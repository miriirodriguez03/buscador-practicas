# buscador-practicas

Buscador automático de ofertas de prácticas en empresas de tecnología médica y
farmacéuticas, para el Máster en Ingeniería Biomecánica y Dispositivos Médicos.

Revisa los portales de empleo Workday de las empresas de `config.yaml`, se queda
con las ofertas cuyo título indica prácticas o beca, las clasifica en **España** u
**otros países** y abre un *issue* en este repositorio con las ofertas nuevas.
Como GitHub te notifica los issues, te llega el aviso al correo o al móvil.

## Cómo funciona

1. **GitHub Actions** (`.github/workflows/buscar.yml`) ejecuta `buscar_ofertas.py`
   dos veces al día (07:17 y 16:17 UTC). También se puede lanzar a mano desde la
   pestaña *Actions* → *Buscar ofertas de prácticas* → *Run workflow*.
2. El script consulta cada portal, filtra por título y abre la ficha de cada oferta
   para conocer su ubicación real.
3. Las ofertas nuevas se escriben en `nuevas_espana.md` y `nuevas_internacional.md`,
   y el workflow abre un issue por cada archivo.
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

## Ejecutarlo en tu ordenador

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe buscar_ofertas.py
```

Ojo: al ejecutarlo en local se actualiza `ofertas_vistas.csv`. Si subes ese
archivo sin haber creado los avisos, esas ofertas no se volverán a notificar.

## Problemas conocidos

- **Workday limita las peticiones desde los servidores de GitHub.** Si todas las
  empresas fallan con código 429, la ejecución termina en error; el resumen final
  del log indica cuántas respuestas hubo de cada código HTTP.
- Las ofertas descartadas por los filtros también se guardan como vistas, así que
  si amplías los filtros no se vuelven a evaluar. Se corregirá en la fase 2.
- Lilly, Takeda y Sanofi (programas de estudiantes) están desactivadas en
  `config.yaml` porque sus direcciones ya no funcionan.
