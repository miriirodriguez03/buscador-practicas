"""Registro de ofertas (ofertas_vistas.csv), con migración automática del formato antiguo."""
import csv
import os

from buscador.fechas import estimar_fecha
from buscador.modelos import COLUMNAS, Registro

SUFIJO_SIN_VERIFICAR = " (ubicación sin verificar)"


def migrar_fila(fila):
    """Convierte una fila del formato antiguo (fases 0 y 1) en un Registro.

    Formato antiguo: empresa, titulo, ubicacion, categoria, publicada, pasa_filtro,
    detectada_el, url. Entonces una oferta solo se avisaba si pasaba los filtros la
    primera vez que se veía, así que pasa_filtro = 'si' equivale a 'avisada'."""
    ubicacion = fila.get("ubicacion") or ""
    categoria = fila.get("categoria") or ""
    if ubicacion.endswith(SUFIJO_SIN_VERIFICAR):
        ubicacion, verificada = ubicacion[:-len(SUFIJO_SIN_VERIFICAR)], "no"
    elif categoria:
        verificada = "si"   # solo se clasificaba tras abrir la ficha con éxito
    else:
        verificada = ""     # no pasó el filtro de título: la ubicación es la del listado
    detectada = fila.get("detectada_el") or ""
    pasa = fila.get("pasa_filtro") == "si"
    publicada = fila.get("publicada") or ""
    return Registro(url=fila["url"], empresa=fila.get("empresa") or "", titulo=fila.get("titulo") or "",
                    categoria=categoria, pasa_filtro=pasa, ubicacion=ubicacion,
                    ubicacion_verificada=verificada, publicada=publicada,
                    fecha_publicacion=estimar_fecha(publicada, detectada), fecha_exacta=False,
                    primera_vez=detectada, ultima_vez=detectada,
                    avisada_el=detectada if pasa else "")


class AlmacenCsv:
    """Guarda todas las ofertas vistas en un CSV, indexadas por URL."""

    def __init__(self, ruta):
        self.ruta = ruta
        self.migradas = 0   # filas convertidas desde el formato antiguo en la última carga

    def cargar(self):
        """Devuelve {url: Registro}. Si el archivo no existe, devuelve un diccionario vacío.
        Si está en el formato antiguo, lo convierte (se guardará en el nuevo)."""
        self.migradas = 0
        if not os.path.exists(self.ruta):
            return {}
        with open(self.ruta, encoding="utf-8", newline="") as f:
            lector = csv.DictReader(f)
            antiguo = "avisada_el" not in (lector.fieldnames or [])
            registros = {}
            for fila in lector:
                if not fila.get("url"):
                    continue
                registros[fila["url"]] = migrar_fila(fila) if antiguo else Registro.de_fila(fila)
        if antiguo:
            self.migradas = len(registros)
        return registros

    def guardar(self, registros):
        """Escribe todos los registros, con las columnas en el orden de COLUMNAS."""
        with open(self.ruta, "w", encoding="utf-8", newline="") as f:
            escritor = csv.DictWriter(f, fieldnames=COLUMNAS)
            escritor.writeheader()
            for registro in registros.values():
                escritor.writerow(registro.a_fila())
