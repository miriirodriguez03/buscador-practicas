"""Interfaz común de todas las fuentes de ofertas."""
from abc import ABC, abstractmethod


class Fuente(ABC):
    """Un portal de empleo de una empresa.

    Para añadir un tipo de portal nuevo basta con crear una subclase que implemente
    `buscar` y `ubicacion_detallada`, y registrarla en `fuentes.crear_fuente`.
    """

    def __init__(self, nombre):
        self.nombre = nombre

    @abstractmethod
    def buscar(self, terminos):
        """Devuelve la lista de `Resultado` encontrados para todos los términos, sin
        duplicados. Lanza una excepción si no se puede consultar el portal."""

    @abstractmethod
    def ubicacion_detallada(self, resultado):
        """Devuelve (texto, True) con la ubicación completa de la oferta (país incluido),
        o ("", False) si no se pudo obtener."""

    def pausa(self):
        """Pausa de cortesía entre peticiones al portal (por defecto, ninguna)."""
