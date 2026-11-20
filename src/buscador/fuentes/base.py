"""Interfaz común de todas las fuentes de ofertas."""
from abc import ABC, abstractmethod


class Fuente(ABC):
    """Un portal de empleo de una empresa.

    Para añadir un tipo de portal nuevo basta con crear una subclase que implemente
    `buscar` y `detalle`, y registrarla en `fuentes.crear_fuente`.
    """

    def __init__(self, nombre):
        self.nombre = nombre

    @abstractmethod
    def buscar(self, terminos):
        """Devuelve la lista de `Resultado` encontrados para todos los términos, sin
        duplicados. Lanza una excepción si no se puede consultar el portal."""

    @abstractmethod
    def detalle(self, resultado):
        """Abre la ficha de la oferta y devuelve un `Detalle` con la ubicación completa
        (país incluido) y, si el portal la da, la fecha exacta de publicación.
        Si no se puede abrir, devuelve Detalle("", False). Nunca lanza excepciones."""

    def pausa(self):
        """Pausa de cortesía entre peticiones al portal (por defecto, ninguna)."""
