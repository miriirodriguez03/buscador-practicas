"""Registro de ofertas ya revisadas (ofertas_vistas.csv)."""
import csv
import os

from buscador.modelos import COLUMNAS


class AlmacenCsv:
    """Guarda todas las ofertas revisadas en un CSV, indexadas por URL."""

    def __init__(self, ruta):
        self.ruta = ruta

    def cargar(self):
        """Devuelve {url: fila}. Si el archivo no existe, devuelve un diccionario vacío."""
        if not os.path.exists(self.ruta):
            return {}
        with open(self.ruta, encoding="utf-8", newline="") as f:
            return {fila["url"]: fila for fila in csv.DictReader(f)}

    def guardar(self, vistas):
        """Escribe todas las filas, con las columnas en el orden de COLUMNAS."""
        with open(self.ruta, "w", encoding="utf-8", newline="") as f:
            escritor = csv.DictWriter(f, fieldnames=COLUMNAS)
            escritor.writeheader()
            for fila in vistas.values():
                escritor.writerow({c: fila.get(c, "") for c in COLUMNAS})
