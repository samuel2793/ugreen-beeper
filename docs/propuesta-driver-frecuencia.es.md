# Propuesta: `ug_beep` con frecuencia configurable

Es una propuesta de diseño, no una guía de instalación ni un parche listo para
producción. Parte del módulo documentado en [hardware.md](hardware.md).

La propuesta cuenta además con una implementación experimental limpia en
[`kernel/ug_beep_frequency`](../kernel/ug_beep_frequency). En el DH4300 Plus
se cargó temporalmente desde `/tmp`: mantuvo `sata_sw`, publicó los atributos
sysfs y cambió el PWM desactivado de 950 a 1000 Hz (periodo de 1.000.000 ns).
Un `rep 1 100 0` terminó con el PWM apagado. No es una medición con
osciloscopio ni una validación auditiva independiente, y no debe instalarse de
forma persistente sin el árbol de fuentes UGREEN.

## Objetivo

Añadir al driver propietario del PWM estos atributos sysfs documentados:

```text
/sys/devices/platform/ug-beep/frequency_hz       # lectura/escritura, Hz seleccionados
/sys/devices/platform/ug-beep/frequency_min_hz   # solo lectura
/sys/devices/platform/ug-beep/frequency_max_hz   # solo lectura
```

La escritura de `frequency_hz` debe aplicar `period = NSEC_PER_SEC /
frequency_hz` con un duty cercano al 50 % mediante `pwm_apply_state()`, y
conservar `rep` para la reproducción finita. `SysfsFrequencyProcfsBackend`
implementa este contrato: verifica los límites, escribe la frecuencia y envía
el `rep` actual. Se desactiva si falta algún atributo, por lo que el kernel
UGREEN de serie no recibirá nunca una frecuencia por accidente.

## Condiciones necesarias

1. Datos por dispositivo y un mutex para serializar frecuencia y reproducción.
2. Sintaxis exacta y documentada: no sobrecargar `rep`.
3. Rechazar valores inválidos. El rango se decidirá solo tras validar
   físicamente 500, 1000 y 2000 Hz; no se debe anunciar antes.
4. Definir el caso de cambio durante un pitido: devolver `-EBUSY` o aplicarlo
   en un borde seguro. Comprobar cada error de `pwm_apply_state()` y preservar
   el estado anterior.
5. No acceder jamás a `febe0010.pwm` ni a `febe0020.pwm`.

El módulo actual ya usa la API PWM estándar, de modo que no hacen falta
unbind/rebind, exportación PWM ni escrituras de registros.

## Puerta de compilación y validación física

Solo un administrador que disponga del árbol/configuración exactos de
`6.1.84 #d64bed19bdfd`, copia del módulo original y acceso de recuperación debe
compilar o instalar un módulo. Este proyecto no carga, descarga ni reemplaza
módulos.

Antes de una única prueba finita, guardar la versión, checksum y estado:

```sh
uname -a
sha256sum /lib/modules/"$(uname -r)"/kernel/drivers/ugreen/ug_beep.ko
sudo cat /sys/kernel/debug/pwm
```

Empezar por los 950 Hz actuales y hacer como máximo un `rep 1 100 0` por valor.
Comprobar debugfs y el sonido tras cada prueba. Si el PWM permanece activo,
detenerse y usar la vía documentada de apagado del driver o reiniciar durante
una ventana de mantenimiento; nunca modificar los PWM del ventilador.

## Alternativas descartadas

El driver sobrescribe el periodo del Device Tree al hacer probe: un cambio de
DT no crea una frecuencia dinámica. Un consumidor PWM independiente chocaría
con `ug_beep`. Extender de forma limitada el propietario actual es la opción
menos invasiva y más mantenible.
