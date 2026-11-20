"""Fuente para portales Workday (*.myworkdayjobs.com), usando su API JSON pública."""
import re
from urllib.parse import urlparse

from buscador.fuentes.base import Fuente
from buscador.modelos import Resultado

TAM_PAGINA = 20


def datos_workday(url):
    """De 'https://medtronic.wd1.myworkdayjobs.com/en-US/MedtronicCareers' saca host, tenant y portal."""
    partes = urlparse(url.strip())
    host = partes.netloc
    if "myworkdayjobs.com" not in host:
        raise ValueError("la dirección no es de Workday (no contiene myworkdayjobs.com)")
    tenant = host.split(".")[0]
    segmentos = [s for s in partes.path.split("/") if s]
    segmentos = [s for s in segmentos if not re.fullmatch(r"[a-z]{2}-[A-Z]{2}", s)]  # quita 'en-US', etc.
    if not segmentos:
        raise ValueError("falta el nombre del portal al final de la dirección")
    return host, tenant, segmentos[0]


class FuenteWorkday(Fuente):
    def __init__(self, nombre, url, cliente, max_por_termino=100):
        super().__init__(nombre)
        self.host, self.tenant, self.portal = datos_workday(url)
        self.cliente = cliente
        self.max_por_termino = max_por_termino

    def pausa(self):
        self.cliente.pausa()

    @property
    def _api(self):
        return f"https://{self.host}/wday/cxs/{self.tenant}/{self.portal}"

    def _buscar_termino(self, termino):
        """Ofertas que el portal muestra al buscar 'termino', página a página."""
        ofertas, offset = [], 0
        while offset < self.max_por_termino:
            cuerpo = {"appliedFacets": {}, "limit": TAM_PAGINA, "offset": offset, "searchText": termino}
            respuesta = self.cliente.peticion("POST", f"{self._api}/jobs", json=cuerpo)
            pagina = respuesta.json().get("jobPostings", [])
            ofertas.extend(pagina)
            if len(pagina) < TAM_PAGINA:
                break
            offset += TAM_PAGINA
            self.pausa()
        return ofertas

    def buscar(self, terminos):
        encontradas = {}
        for termino in terminos:
            for oferta in self._buscar_termino(termino):
                ruta = oferta.get("externalPath")
                if ruta:  # algunos resultados llegan sin enlace: se ignoran
                    encontradas[ruta] = oferta
            self.pausa()
        return [Resultado(titulo=o.get("title", ""), ubicacion=o.get("locationsText", ""),
                          publicada=o.get("postedOn", ""),
                          url=f"https://{self.host}/{self.portal}{ruta}", ruta=ruta)
                for ruta, o in encontradas.items()]

    def ubicacion_detallada(self, resultado):
        try:
            respuesta = self.cliente.peticion("GET", f"{self._api}{resultado.ruta}")
            info = respuesta.json().get("jobPostingInfo", {})
            trozos = [info.get("location", "")]
            for extra in info.get("additionalLocations", []) or []:
                trozos.append(extra if isinstance(extra, str) else str(extra.get("descriptor", "")))
            trozos.append((info.get("country") or {}).get("descriptor", ""))
            texto = ", ".join(t for t in trozos if t)
            return texto, bool(texto)
        except Exception:
            return "", False
