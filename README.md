# buscador-practicas

Buscador automático de ofertas de prácticas en empresas de tecnología médica y
farmacéuticas, para el Máster en Ingeniería Biomecánica y Dispositivos Médicos.

Revisa los portales de empleo Workday de las empresas de `config.yaml`, se queda
con las ofertas cuyo título indica prácticas o beca, las clasifica en **España** u
**otros países** y abre un *issue* en este repositorio con las ofertas nuevas.
Como GitHub te notifica los issues, te llega el aviso al correo o al móvil.

## Cómo funciona

1. **Tu PC** ejecuta `ejecutar_local.ps1` todos los días (por defecto a las 09:00 y
   18:00) mediante el Programador de tareas de Windows. Si el PC está apagado a
   esa hora, se ejecuta al encenderlo. No se usa GitHub Actions porque Workday
   bloquea las peticiones que salen de GitHub (ver *Problemas conocidos*).
2. El script consulta cada portal, filtra por título y abre la ficha de cada oferta
   para conocer su ubicación real.
3. Las ofertas nuevas se escriben en `nuevas_espana.md` y `nuevas_internacional.md`,
   y se abre un issue por cada archivo con la CLI de GitHub (`gh`).
4. Solo después de crear los avisos se guarda `ofertas_vistas.csv`, el registro de
   todas las ofertas ya revisadas, para no avisar dos veces de la misma.

## Configuración

Todo se ajusta en [`config.yaml`](config.yaml), sin tocar el código:

| Clave | Para qué sirve |
|---|---|
| `usuario_github` | Usuario al que se menciona en los avisos |
| `terminos_busqueda` | Lo que se escribe en el buscador de cada portal |
| `palabras_titulo` | El título debe contener al menos una |
| `palabras_excluidas` | Si el título contiene alguna, se descarta |
| `ubicaciones_espana` | Palabras que identifican una oferta en España |
| `ubicaciones_internacionales` | Países aceptados fuera de España (`[]` = todos) |
| `empresas` | Nombre y dirección Workday de cada empresa |

| `ajustes` *(opcional)* | `pausa` entre peticiones (s), `max_por_termino`, `max_en_aviso` |

Para añadir una empresa, copia un bloque de dos líneas (`nombre` y `url`) con la
dirección de su portal `*.myworkdayjobs.com`.

Al arrancar se valida `config.yaml`: si hay un error de estructura (sangría,
tabuladores, una lista mal escrita…) el programa se detiene explicando qué
corregir, y avisa de claves desconocidas por si hay una errata.

## Probar cambios sin consecuencias

```powershell
# Busca y muestra las ofertas nuevas sin guardar el registro ni crear avisos
.\.venv\Scripts\python.exe buscar_ofertas.py --dry-run

# Solo algunas empresas (útil al añadir una nueva a config.yaml)
.\.venv\Scripts\python.exe buscar_ofertas.py --dry-run --empresa Almirall --empresa Philips

# Todas las opciones
.\.venv\Scripts\python.exe buscar_ofertas.py --help
```

## Instalación en el PC (una sola vez)

Requisitos: Git, Python 3.12 y la CLI de GitHub (`winget install GitHub.cli`), con
sesión iniciada (`gh auth login`).

```powershell
# Registrar la tarea diaria (09:00 y 18:00 por defecto)
powershell -ExecutionPolicy Bypass -File .\instalar_tarea.ps1

# Otras horas
powershell -ExecutionPolicy Bypass -File .\instalar_tarea.ps1 -Horas "08:30","20:00"

# Lanzarlo a mano en cualquier momento
powershell -ExecutionPolicy Bypass -File .\ejecutar_local.ps1

# Quitar la tarea
Unregister-ScheduledTask -TaskName "Buscador de practicas" -Confirm:$false
```

`ejecutar_local.ps1` actualiza el repositorio, crea el entorno de Python si no
existe, busca, crea los issues y sube `ofertas_vistas.csv`. Si algo falla, deja el
CSV como estaba, de modo que la siguiente ejecución vuelve a avisar de esas
ofertas. Cada ejecución queda registrada en `logs/` (que no se sube al repositorio).

## Estructura del código

```
buscar_ofertas.py          punto de entrada (lo usan ejecutar_local.ps1 y el workflow)
src/buscador/
  cli.py                   opciones de línea de comandos y resumen final
  config.py                lectura y validación de config.yaml
  pipeline.py              recorre empresas, filtra y decide qué ofertas son nuevas
  filtros.py               filtro por título y clasificación España / otros países
  fuentes/base.py          interfaz común de los portales de empleo
  fuentes/workday.py       portales Workday (*.myworkdayjobs.com)
  http.py                  peticiones con pausas y reintentos (429, 5xx, cortes de red)
  almacen.py               ofertas_vistas.csv
  avisos.py                textos Markdown de los avisos
  modelos.py               estructuras de datos compartidas
tests/                     tests (pytest) con respuestas reales de Workday grabadas
```

Para añadir otro tipo de portal (SuccessFactors, Greenhouse…) se crea una clase en
`src/buscador/fuentes/` que herede de `Fuente` y se registra en `crear_fuente`.

### Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

`tests/test_extremo_a_extremo.py` reproduce 91 respuestas reales de Workday y
comprueba que el CSV y los avisos generados son idénticos a los del programa
original. Los tests también se ejecutan en GitHub Actions en cada cambio
(`.github/workflows/tests.yml`); no consultan Workday, así que no les afecta el
bloqueo.

## Problemas conocidos

- **Workday bloquea las peticiones desde los servidores de GitHub**: todas
  responden 429 incluso tras reintentar, mientras que desde una conexión
  doméstica funcionan. Por eso la búsqueda programada se hace desde el PC y el
  workflow de GitHub Actions solo se lanza a mano.
- Solo se busca cuando el PC está encendido.
- Las ofertas descartadas por los filtros también se guardan como vistas, así que
  si amplías los filtros no se vuelven a evaluar. Se corregirá en la fase 2.
- Lilly, Takeda y Sanofi (programas de estudiantes) están desactivadas en
  `config.yaml` porque sus direcciones ya no funcionan.
