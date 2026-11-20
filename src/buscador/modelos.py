"""Estructuras de datos que se pasan entre módulos."""
from dataclasses import dataclass, fields

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


@dataclass(frozen=True)
class Detalle:
    """Lo que se obtiene al abrir la ficha de una oferta."""
    ubicacion: str              # ubicación completa (país incluido); "" si no se pudo obtener
    verificada: bool            # False si no se pudo abrir la ficha
    fecha_publicacion: str = "" # fecha exacta AAAA-MM-DD, si el portal la da


@dataclass
class Registro:
    """Una oferta del registro (una fila de ofertas_vistas.csv).

    Se guardan todas las ofertas vistas, pasen o no los filtros. Las que aún no se
    han avisado se vuelven a evaluar en cada ejecución mientras sigan publicadas,
    así que si amplías los filtros aparecen las que antes se descartaron."""
    url: str
    empresa: str = ""
    titulo: str = ""
    categoria: str = ""                 # ESPANA, INTERNACIONAL o "" si no pasa el filtro de título
    pasa_filtro: bool = False           # resultado de la última evaluación
    ubicacion: str = ""                 # completa si está verificada; si no, la del listado
    ubicacion_verificada: str = ""      # "si" (ficha leída), "no" (falló) o "" (no hizo falta)
    publicada: str = ""                 # texto del portal en la última ejecución
    fecha_publicacion: str = ""         # AAAA-MM-DD
    fecha_exacta: bool = False          # True si viene de la ficha; False si es estimada
    primera_vez: str = ""               # fecha en que se vio por primera vez
    ultima_vez: str = ""                # última fecha en que seguía publicada
    avisada_el: str = ""                # fecha del aviso; "" si nunca se ha avisado

    def a_fila(self):
        fila = {}
        for campo in fields(self):
            valor = getattr(self, campo.name)
            fila[campo.name] = ("si" if valor else "no") if isinstance(valor, bool) else valor
        return fila

    @classmethod
    def de_fila(cls, fila):
        datos = {}
        for campo in fields(cls):
            valor = fila.get(campo.name) or ""
            datos[campo.name] = (valor == "si") if campo.type is bool else valor
        return cls(**datos)


# Columnas de ofertas_vistas.csv, en este orden
COLUMNAS = [f.name for f in fields(Registro)]
