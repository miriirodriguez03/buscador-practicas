"""Fuentes de ofertas. Cada portal (Workday, SuccessFactors, ...) es una clase `Fuente`."""
from buscador.fuentes.base import Fuente
from buscador.fuentes.workday import FuenteWorkday


def crear_fuente(empresa, cliente, ajustes):
    """Elige la fuente adecuada según la dirección de la empresa.
    Lanza ValueError si ninguna fuente sabe leer esa dirección."""
    url = empresa.url or ""
    if "myworkdayjobs.com" in url:
        return FuenteWorkday(empresa.nombre, url, cliente, max_por_termino=ajustes.max_por_termino)
    raise ValueError("la dirección no es de Workday (no contiene myworkdayjobs.com)")


__all__ = ["Fuente", "FuenteWorkday", "crear_fuente"]
