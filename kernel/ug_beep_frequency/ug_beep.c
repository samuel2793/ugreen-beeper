// SPDX-License-Identifier: GPL-2.0-only
/*
 * Experimental replacement for UGREEN's ug_beep driver.
 *
 * Target: DH4300 Plus, vendor Linux 6.1.84 only.  Do not install without the
 * validation and rollback procedure in README.md.
 */
#include <linux/delay.h>
#include <linux/kernel.h>
#include <linux/namei.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/proc_fs.h>
#include <linux/pwm.h>
#include <linux/slab.h>
#include <linux/uaccess.h>
#include <linux/workqueue.h>

/* The vendor driver performs the same proc inode lookup for /proc/nas. */
#include "fs/proc/internal.h"

#define UG_BEEP_DEFAULT_HZ 950U
#define UG_BEEP_MIN_HZ 500U
#define UG_BEEP_MAX_HZ 2000U
#define UG_BEEP_MAX_COMMAND 64U
#define UG_BEEP_MAX_COUNT 20U
#define UG_BEEP_MIN_DURATION_MS 10U
#define UG_BEEP_MAX_DURATION_MS 5000U
#define UG_BEEP_MAX_INTERVAL_MS 10000U

struct ug_beep {
	struct device *dev;
	struct pwm_device *pwm;
	struct pwm_state state;
	struct mutex lock;
	struct delayed_work transition_work;
	struct proc_dir_entry *proc_dir;
	struct proc_dir_entry *proc_file;
	bool owns_proc_dir;
	u32 frequency_hz;
	u32 remaining;
	u32 duration_ms;
	u32 interval_ms;
	bool active;
};

static int ug_beep_apply_locked(struct ug_beep *beep, bool enabled)
{
	int ret;

	beep->state.enabled = enabled;
	ret = pwm_apply_state(beep->pwm, &beep->state);
	if (ret)
		dev_err(beep->dev, "unable to %s PWM: %d\n",
			enabled ? "enable" : "disable", ret);
	return ret;
}

/*
 * UGREEN keeps /proc/nas alive for other modules such as ug_sataio.  The
 * vendor module looks up the existing proc_dir_entry rather than recreating
 * it.  PDE() retrieves the proc entry from the proc inode safely.
 */
static struct proc_dir_entry *ug_beep_find_nas_dir(void)
{
	struct path path;
	struct dentry *dentry;
	struct proc_dir_entry *dir = NULL;

	if (kern_path("/proc", LOOKUP_FOLLOW, &path))
		return NULL;
	dentry = lookup_positive_unlocked("nas", path.dentry, 3);
	if (!IS_ERR(dentry)) {
		dir = PDE(dentry->d_inode);
		dput(dentry);
	}
	path_put(&path);
	return dir;
}

static void ug_beep_transition(struct work_struct *work)
{
	struct ug_beep *beep = container_of(to_delayed_work(work),
					   struct ug_beep, transition_work);
	u32 delay_ms;
	int ret;

	mutex_lock(&beep->lock);
	if (!beep->active)
		goto out;

	if (beep->state.enabled) {
		ret = ug_beep_apply_locked(beep, false);
		if (ret)
			goto stop;
		if (--beep->remaining == 0) {
			beep->active = false;
			goto out;
		}
		delay_ms = beep->interval_ms;
	} else {
		ret = ug_beep_apply_locked(beep, true);
		if (ret)
			goto stop;
		delay_ms = beep->duration_ms;
	}

	mod_delayed_work(system_wq, &beep->transition_work,
			 msecs_to_jiffies(delay_ms));
	goto out;

stop:
	beep->active = false;
	out:
	mutex_unlock(&beep->lock);
}

static void ug_beep_stop(struct ug_beep *beep)
{
	cancel_delayed_work_sync(&beep->transition_work);
	mutex_lock(&beep->lock);
	beep->active = false;
	beep->remaining = 0;
	ug_beep_apply_locked(beep, false);
	mutex_unlock(&beep->lock);
}

static int ug_beep_start(struct ug_beep *beep, u32 count, u32 duration_ms,
			 u32 interval_ms)
{
	int ret;

	ug_beep_stop(beep);
	mutex_lock(&beep->lock);
	beep->remaining = count;
	beep->duration_ms = duration_ms;
	beep->interval_ms = interval_ms;
	beep->active = true;
	ret = ug_beep_apply_locked(beep, true);
	if (!ret)
		mod_delayed_work(system_wq, &beep->transition_work,
				 msecs_to_jiffies(duration_ms));
	else
		beep->active = false;
	mutex_unlock(&beep->lock);
	return ret;
}

static ssize_t frequency_hz_show(struct device *dev,
				 struct device_attribute *attr, char *buf)
{
	struct ug_beep *beep = dev_get_drvdata(dev);
	u32 frequency_hz;

	mutex_lock(&beep->lock);
	frequency_hz = beep->frequency_hz;
	mutex_unlock(&beep->lock);
	return sysfs_emit(buf, "%u\n", frequency_hz);
}

static ssize_t frequency_hz_store(struct device *dev,
				  struct device_attribute *attr, const char *buf,
				  size_t count)
{
	struct ug_beep *beep = dev_get_drvdata(dev);
	struct pwm_state state;
	u32 frequency_hz;
	int ret;

	ret = kstrtouint(buf, 10, &frequency_hz);
	if (ret)
		return ret;
	if (frequency_hz < UG_BEEP_MIN_HZ || frequency_hz > UG_BEEP_MAX_HZ)
		return -ERANGE;

	mutex_lock(&beep->lock);
	state = beep->state;
	state.period = DIV_ROUND_CLOSEST_ULL(NSEC_PER_SEC, frequency_hz);
	state.duty_cycle = state.period / 2;
	ret = pwm_apply_state(beep->pwm, &state);
	if (!ret) {
		beep->state = state;
		beep->frequency_hz = frequency_hz;
	}
	mutex_unlock(&beep->lock);
	return ret ? ret : count;
}
static DEVICE_ATTR_RW(frequency_hz);

static ssize_t frequency_min_hz_show(struct device *dev,
				     struct device_attribute *attr, char *buf)
{
	return sysfs_emit(buf, "%u\n", UG_BEEP_MIN_HZ);
}
static DEVICE_ATTR_RO(frequency_min_hz);

static ssize_t frequency_max_hz_show(struct device *dev,
				     struct device_attribute *attr, char *buf)
{
	return sysfs_emit(buf, "%u\n", UG_BEEP_MAX_HZ);
}
static DEVICE_ATTR_RO(frequency_max_hz);

static struct attribute *ug_beep_attrs[] = {
	&dev_attr_frequency_hz.attr,
	&dev_attr_frequency_min_hz.attr,
	&dev_attr_frequency_max_hz.attr,
	NULL,
};
ATTRIBUTE_GROUPS(ug_beep);

static ssize_t ug_beep_proc_write(struct file *file, const char __user *buffer,
				  size_t count, loff_t *offset)
{
	struct ug_beep *beep = pde_data(file_inode(file));
	char command[UG_BEEP_MAX_COMMAND];
	u32 beeps, duration_ms, interval_ms;
	int parsed;

	if (!count || count >= sizeof(command))
		return -EINVAL;
	if (copy_from_user(command, buffer, count))
		return -EFAULT;
	command[count] = '\0';
	strim(command);

	if (!strcmp(command, "off")) {
		ug_beep_stop(beep);
		return count;
	}

	parsed = sscanf(command, "rep %u %u %u", &beeps, &duration_ms,
			&interval_ms);
	if (parsed != 3 || beeps < 1 || beeps > UG_BEEP_MAX_COUNT ||
	    duration_ms < UG_BEEP_MIN_DURATION_MS ||
	    duration_ms > UG_BEEP_MAX_DURATION_MS ||
	    interval_ms > UG_BEEP_MAX_INTERVAL_MS)
		return -EINVAL;
	if (ug_beep_start(beep, beeps, duration_ms, interval_ms))
		return -EIO;
	return count;
}

static const struct proc_ops ug_beep_proc_ops = {
	.proc_write = ug_beep_proc_write,
};

static int ug_beep_probe(struct platform_device *pdev)
{
	struct ug_beep *beep;
	int ret;

	beep = devm_kzalloc(&pdev->dev, sizeof(*beep), GFP_KERNEL);
	if (!beep)
		return -ENOMEM;
	beep->dev = &pdev->dev;
	mutex_init(&beep->lock);
	INIT_DELAYED_WORK(&beep->transition_work, ug_beep_transition);
	beep->pwm = pwm_get(&pdev->dev, NULL);
	if (IS_ERR(beep->pwm))
		return dev_err_probe(&pdev->dev, PTR_ERR(beep->pwm), "cannot get PWM\n");

	pwm_get_state(beep->pwm, &beep->state);
	beep->frequency_hz = UG_BEEP_DEFAULT_HZ;
	beep->state.period = DIV_ROUND_CLOSEST_ULL(NSEC_PER_SEC,
						     beep->frequency_hz);
	beep->state.duty_cycle = beep->state.period / 2;
	ret = ug_beep_apply_locked(beep, false);
	if (ret)
		goto put_pwm;

	platform_set_drvdata(pdev, beep);
	ret = devm_device_add_groups(&pdev->dev, ug_beep_groups);
	if (ret)
		goto disable_pwm;
	beep->proc_dir = ug_beep_find_nas_dir();
	if (!beep->proc_dir) {
		beep->proc_dir = proc_mkdir("nas", NULL);
		beep->owns_proc_dir = true;
	}
	if (!beep->proc_dir) {
		ret = -ENOMEM;
		goto disable_pwm;
	}
	beep->proc_file = proc_create_data("beeper", 0222, beep->proc_dir,
					   &ug_beep_proc_ops, beep);
	if (!beep->proc_file) {
		ret = -ENOMEM;
		goto remove_proc_dir;
	}
	return 0;

remove_proc_dir:
	if (beep->owns_proc_dir)
		proc_remove(beep->proc_dir);
disable_pwm:
	ug_beep_apply_locked(beep, false);
put_pwm:
	pwm_put(beep->pwm);
	return ret;
}

static int ug_beep_remove(struct platform_device *pdev)
{
	struct ug_beep *beep = platform_get_drvdata(pdev);

	ug_beep_stop(beep);
	proc_remove(beep->proc_file);
	if (beep->owns_proc_dir)
		proc_remove(beep->proc_dir);
	pwm_put(beep->pwm);
	return 0;
}

static const struct of_device_id ug_beep_of_match[] = {
	{ .compatible = "ug-pwm-beep" },
	{ }
};
MODULE_DEVICE_TABLE(of, ug_beep_of_match);

static struct platform_driver ug_beep_driver = {
	.probe = ug_beep_probe,
	.remove = ug_beep_remove,
	.driver = {
		.name = "ug-beep",
		.of_match_table = ug_beep_of_match,
	},
};
module_platform_driver(ug_beep_driver);

MODULE_DESCRIPTION("Experimental UGREEN PWM beeper with sysfs frequency control");
MODULE_LICENSE("GPL");
