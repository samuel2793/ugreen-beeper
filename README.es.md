# ugreen-beeper — documentación en español

Herramienta para emitir pitidos desde aplicaciones, scripts y servicios Linux
en NAS UGREEN compatibles.

**Verificado:** UGREEN DH4300 Plus, Debian 12, kernel 6.1.84, interfaz
`/proc/nas/beeper` y controlador `ug-beep`. No se ha verificado en otros modelos.

## Prueba sin instalar

```sh
./ugreen-beep status
./ugreen-beep beep --dry-run -t 2 -l 400 -i 500
./ugreen-beep beep -t 2 -l 400 -i 500
```

## Instalar para otros procesos sin pip

```sh
sudo mkdir -p /opt/ugreen-beeper
sudo cp -r src /opt/ugreen-beeper/
sudo cp ugreen-beep /opt/ugreen-beeper/
sudo chmod +x /opt/ugreen-beeper/ugreen-beep
sudo ln -s /opt/ugreen-beeper/ugreen-beep /usr/local/bin/ugreen-beep
ugreen-beep status
```

El comando `ln -s` fallará si ya existe un archivo con ese nombre, para evitar
sobrescribirlo sin comprobarlo.

## Alternativa: instalación en entorno virtual

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/ugreen-beep beep -t 2 -l 400 -i 500
```

Si falla la creación del entorno virtual, instala `python3-venv`.

## Eventos reutilizables

```sh
.venv/bin/ugreen-beep event backup-failed --config examples/events.json
```

El fichero `examples/events.json` relaciona cada nombre de evento con cantidad,
duración e intervalo de pitidos. Un sistema de copia de seguridad puede llamar
al comando tras finalizar, sin conocer los parámetros físicos.

## Desde Python

```python
from ugreen_beeper import Beeper

Beeper().beep(count=3, duration_ms=150, interval_ms=200)
```

La frecuencia `-f` del script original `ugbeep` **no funciona** en el driver
verificado: el módulo fija el PWM en ~950 Hz. La CLI 0.2.0 acepta
`--frequency` para mantener una API evolutiva, pero `ProcfsBackend` lo rechaza
explícitamente —también con `--dry-run`— y nunca lo ignora. No se debe tocar
directamente el PWM: el controlador del kernel ya es propietario del
dispositivo. Tampoco hay cola de reproducción para múltiples procesos en esta
versión. El uso simultáneo podría interferir.

`SysfsFrequencyProcfsBackend` ya implementa el contrato del driver ampliado:
descubre los límites sysfs, escribe `frequency_hz` y después envía `rep`. El
driver de serie no publica esos atributos, por lo que la CLI seguirá rechazando
la frecuencia hasta instalar y validar dicho driver.

Existe un reemplazo experimental del driver en
[`kernel/ug_beep_frequency`](kernel/ug_beep_frequency), probado temporalmente
en el DH4300 Plus. No se instala automáticamente, no persiste tras reiniciar y
no debe utilizarse en un NAS con cargas críticas sin revisar su procedimiento
de recuperación.

La API de Python admite `frequency_hz`, pero solo un backend que declare
`supports_frequency` puede recibirlo; de lo contrario se lanza
`UnsupportedFrequencyError`. Consulta [README.md](README.md) para todos los
parámetros, pruebas y límites, y [docs/hardware.md](docs/hardware.md) para la
investigación. La propuesta experimental y el procedimiento seguro están en
[docs/propuesta-driver-frecuencia.es.md](docs/propuesta-driver-frecuencia.es.md).
