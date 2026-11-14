# Propuesta: `ug_beep` con frecuencia configurable

Es una propuesta de diseño, no una guía de instalación ni un parche listo para
producción. Parte del módulo documentado en [hardware.md](hardware.md).

## Objetivo

Añadir al driver propietario del PWM un comando documentado `freq <hz>` (o un
atributo sysfs específico). Debe aplicar `period = NSEC_PER_SEC / frequency_hz`
con un duty cercano al 50 % mediante `pwm_apply_state()`, y conservar `rep`
para la reproducción finita.

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
