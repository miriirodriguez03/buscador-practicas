"""Fechas de publicación: exactas (ficha de la oferta) o estimadas (texto del listado)."""
import re
from datetime import date, timedelta

_DIAS = [
    (re.compile(r"\btoday\b|\bhoy\b", re.I), 0),
    (re.compile(r"\byesterday\b|\bayer\b", re.I), 1),
]
_HACE_N = re.compile(r"(\d+)\s*\+?\s*(?:days?|d[ií]as?)", re.I)
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def estimar_fecha(texto, referencia):
    """Fecha ISO aproximada a partir de textos como 'Posted 3 Days Ago', 'Posted Today'
    o 'Posted 30+ Days Ago' (en este caso, la fecha más reciente posible).
    `referencia` es la fecha ISO en la que se leyó el texto. Devuelve '' si no se entiende."""
    if not texto or not referencia:
        return ""
    try:
        base = date.fromisoformat(referencia)
    except ValueError:
        return ""
    for patron, dias in _DIAS:
        if patron.search(texto):
            return (base - timedelta(days=dias)).isoformat()
    m = _HACE_N.search(texto)
    if m:
        return (base - timedelta(days=int(m.group(1)))).isoformat()
    return ""


def fecha_iso_valida(texto):
    """Devuelve el texto si es una fecha AAAA-MM-DD válida, o '' si no lo es."""
    texto = (texto or "").strip()[:10]
    if not _ISO.match(texto):
        return ""
    try:
        date.fromisoformat(texto)
    except ValueError:
        return ""
    return texto


def formato_corto(fecha_iso):
    """'2026-10-30' -> '30/10/2026'."""
    a, m, d = fecha_iso.split("-")
    return f"{d}/{m}/{a}"
