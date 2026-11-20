"""Filtros por título y clasificación por ubicación."""
import re
import unicodedata

from buscador.modelos import ESPANA, INTERNACIONAL


def normalizar(texto):
    """Pasa a minúsculas y quita tildes: 'Prácticas' -> 'practicas'."""
    texto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in texto if not unicodedata.combining(c)).lower()


def contiene_alguna(texto, palabras):
    """True si el texto contiene alguna de las palabras como palabra completa."""
    texto = normalizar(texto)
    return any(re.search(r"\b" + re.escape(normalizar(p)) + r"\b", texto) for p in palabras or [])


def pasa_titulo(titulo, incluidas, excluidas):
    """El título debe contener alguna palabra incluida y ninguna excluida."""
    return contiene_alguna(titulo, incluidas) and not contiene_alguna(titulo, excluidas)


def clasificar(ubicacion, verificada, espana, internacionales):
    """Devuelve (categoria, pasa_filtro, ubicacion_mostrada).
    - España: si alguna de sus ubicaciones está en España (también si comparte con otros países).
    - Otros países: el resto, filtrado por 'internacionales' si la lista no está vacía.
    - Si no se pudo comprobar la ubicación, va a 'Otros países' marcada para que la revises."""
    if contiene_alguna(ubicacion, espana):
        return ESPANA, True, ubicacion
    if not verificada:
        return INTERNACIONAL, True, f"{ubicacion} (ubicación sin verificar)"
    if internacionales:
        return INTERNACIONAL, contiene_alguna(ubicacion, internacionales), ubicacion
    return INTERNACIONAL, True, ubicacion
