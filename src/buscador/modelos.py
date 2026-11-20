"""Estructuras de datos que se pasan entre módulos."""
from dataclasses import dataclass

# Columnas de ofertas_vistas.csv, en este orden
COLUMNAS = ["empresa", "titulo", "ubicacion", "categoria", "publicada",
            "pasa_filtro", "detectada_el", "url"]

ESPANA = "espana"
INTERNACIONAL = "internacional"


@dataclass(frozen=True)
class Resultado:
    """Una oferta tal y como la devuelve el buscador de un portal, antes de filtrar."""
    titulo: str
    ubicacion: str      # texto corto del listado (p. ej. "Madrid, Spain" o "2 Locations")
    publicada: str      # texto del portal (p. ej. "Posted 3 Days Ago")
    url: str            # enlace público a la oferta; identifica la oferta
    ruta: str           # identificador interno de la fuente para pedir la ficha


@dataclass
class Oferta:
    """Una oferta ya evaluada, lista para guardarse y, si pasa los filtros, avisarse."""
    empresa: str
    titulo: str
    ubicacion: str
    categoria: str      # ESPANA, INTERNACIONAL o "" si no pasó el filtro de título
    publicada: str
    pasa_filtro: bool
    detectada_el: str   # fecha ISO (AAAA-MM-DD)
    url: str

    def a_fila(self):
        """Convierte la oferta en una fila de ofertas_vistas.csv."""
        return {"empresa": self.empresa, "titulo": self.titulo, "ubicacion": self.ubicacion,
                "categoria": self.categoria, "publicada": self.publicada,
                "pasa_filtro": "si" if self.pasa_filtro else "no",
                "detectada_el": self.detectada_el, "url": self.url}
