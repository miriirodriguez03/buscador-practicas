import json
from pathlib import Path

import pytest
import requests

FIXTURES = Path(__file__).parent / "fixtures"


class RespuestaFalsa:
    """Imita lo que el programa usa de requests.Response."""

    def __init__(self, estado=200, datos=None, cabeceras=None, url="https://falso"):
        self.status_code = estado
        self._datos = datos if datos is not None else {}
        self.headers = cabeceras or {}
        self.url = url

    @property
    def ok(self):
        return self.status_code < 400

    def json(self):
        return self._datos

    def raise_for_status(self):
        if not self.ok:
            raise requests.HTTPError(f"{self.status_code} Client Error for url: {self.url}", response=self)


class Reproductor:
    """Sustituye a requests.request devolviendo respuestas grabadas de Workday."""

    def __init__(self, ruta):
        self.pendientes = {}
        for r in json.loads(Path(ruta).read_text(encoding="utf-8")):
            self.pendientes.setdefault(self._clave(r["metodo"], r["url"], r["cuerpo"]), []).append(r)
        self.llamadas = 0

    @staticmethod
    def _clave(metodo, url, cuerpo):
        return metodo, url, json.dumps(cuerpo, sort_keys=True)

    def __call__(self, metodo, url, json=None, **_):
        self.llamadas += 1
        cola = self.pendientes.get(self._clave(metodo, url, json))
        if not cola:
            raise AssertionError(f"petición no grabada: {metodo} {url} {json}")
        r = cola.pop(0)
        return RespuestaFalsa(r["estado"], r["json"], url=url)


@pytest.fixture
def reproductor():
    return Reproductor(FIXTURES / "workday_grabacion.json")


@pytest.fixture
def sin_esperas():
    esperas = []
    return esperas.append  # registra las esperas sin dormir de verdad
