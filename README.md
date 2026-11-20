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

Para añadir una empresa, copia un bloque de dos líneas (`nombre` y `url`) con la
dirección de su portal `*.myworkdayjobs.com`.

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
