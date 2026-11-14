#!/bin/sh
# Build the experimental ARM64 ug_beep replacement without deploying it.
set -eu

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "usage: $0 <prepared-linux-6.1.84-tree> [output-directory]" >&2
    exit 2
fi

kernel_dir=$1
output_dir=${2:-"$PWD/dist"}
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
module_dir="$project_dir/kernel/ug_beep_frequency"
cross_compile=${CROSS_COMPILE:-aarch64-linux-gnu-}
# Some workstation images configure ccache in a read-only shared location.
# Kernel builds remain deterministic without it.
export CCACHE_DISABLE=1

if [ ! -f "$kernel_dir/Makefile" ] || [ ! -f "$kernel_dir/include/config/kernel.release" ]; then
    echo "error: $kernel_dir is not a prepared Linux kernel build tree" >&2
    exit 1
fi

kernel_release=$(cat "$kernel_dir/include/config/kernel.release")
if [ "$kernel_release" != "6.1.84" ]; then
    echo "error: expected kernel release 6.1.84, got $kernel_release" >&2
    exit 1
fi

make -C "$kernel_dir" ARCH=arm64 CROSS_COMPILE="$cross_compile" \
    M="$module_dir" modules

module="$module_dir/ug_beep.ko"
if [ ! -f "$module" ]; then
    echo "error: build completed without $module" >&2
    exit 1
fi

vermagic=$(modinfo -F vermagic "$module")
case "$vermagic" in
    "6.1.84 "*" aarch64") ;;
    *)
        echo "error: unexpected module vermagic: $vermagic" >&2
        exit 1
        ;;
esac

mkdir -p "$output_dir"
cp "$module" "$output_dir/ug_beep.ko"
printf 'built: %s\nvermagic: %s\n' "$output_dir/ug_beep.ko" "$vermagic"
