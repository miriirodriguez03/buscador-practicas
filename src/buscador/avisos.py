"""Avisos en Markdown: un archivo por categoría, que luego se publica como issue."""
import os

from buscador.fechas import formato_corto
from buscador.modelos import ESPANA, INTERNACIONAL

AVISOS = {  # categoría -> (archivo del aviso, título que aparece dentro del aviso)
    ESPANA: ("nuevas_espana.md", "🇪🇸 ofertas nuevas en España"),
    INTERNACIONAL: ("nuevas_internacional.md", "🌍 ofertas nuevas en otros países"),
}


def _limpiar(texto):
    return (texto or "").replace("|", "/")


def _ubicacion(o):
    return o.ubicacion + (" (ubicación sin verificar)" if o.ubicacion_verificada == "no" else "")


def _publicada(o):
    """Fecha exacta si se conoce (p. ej. '30/10/2026'); si no, el texto del portal."""
    return formato_corto(o.fecha_publicacion) if o.fecha_exacta and o.fecha_publicacion else o.publicada


def texto_aviso(ofertas, titulo, usuario, max_en_aviso, archivo_vistas):
    """Markdown con la tabla de ofertas (objetos Registro) de una categoría."""
    lineas = []
    if usuario and usuario != "tu-usuario":
        lineas.append(f"@{usuario.lstrip('@')}")
    lineas += [f"**{len(ofertas)} {titulo}** que encajan con tus filtros:", "",
               "| Empresa | Puesto | Ubicación | Publicada |", "|---|---|---|---|"]
    for o in ofertas[:max_en_aviso]:
        lineas.append(f"| {_limpiar(o.empresa)} | [{_limpiar(o.titulo)}]({o.url}) "
                      f"| {_limpiar(_ubicacion(o))} | {_limpiar(_publicada(o))} |")
    if len(ofertas) > max_en_aviso:
        lineas.append(f"\n…y {len(ofertas) - max_en_aviso} más. Las tienes todas en `{archivo_vistas}`.")
    return "\n".join(lineas) + "\n"


def escribir_avisos(nuevas, usuario, max_en_aviso=100, archivo_vistas="ofertas_vistas.csv",
                    carpeta=".", resumen=None):
    """Crea un archivo de aviso por categoría, solo si esa categoría tiene ofertas nuevas.
    Borra los avisos de ejecuciones anteriores. Si `resumen` es una ruta (GitHub Actions),
    añade también el texto ahí. Devuelve la lista de archivos creados."""
    creados = []
    for categoria, (archivo, titulo) in AVISOS.items():
        ruta = os.path.join(carpeta, archivo)
        if os.path.exists(ruta):
            os.remove(ruta)
        ofertas = [o for o in nuevas if o.categoria == categoria]
        if not ofertas:
            continue
        texto = texto_aviso(ofertas, titulo, usuario, max_en_aviso, archivo_vistas)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(texto)
        creados.append(ruta)
        if resumen:
            with open(resumen, "a", encoding="utf-8") as f:
                f.write(texto + "\n")
    return creados
