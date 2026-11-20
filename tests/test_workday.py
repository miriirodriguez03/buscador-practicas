import pytest

from buscador.config import Ajustes, Empresa
from buscador.fuentes import FuenteWorkday, crear_fuente
from buscador.fuentes.workday import datos_workday
from buscador.http import ClienteHttp
from buscador.modelos import Detalle, Resultado
from conftest import RespuestaFalsa


@pytest.mark.parametrize("url, esperado", [
    ("https://medtronic.wd1.myworkdayjobs.com/MedtronicCareers",
     ("medtronic.wd1.myworkdayjobs.com", "medtronic", "MedtronicCareers")),
    ("https://medtronic.wd1.myworkdayjobs.com/en-US/MedtronicCareers/",
     ("medtronic.wd1.myworkdayjobs.com", "medtronic", "MedtronicCareers")),
    ("  https://cgm.wd3.myworkdayjobs.com/cgm  ", ("cgm.wd3.myworkdayjobs.com", "cgm", "cgm")),
])
def test_datos_workday(url, esperado):
    assert datos_workday(url) == esperado


@pytest.mark.parametrize("url, mensaje", [
    ("https://careers.example.com/jobs", "no es de Workday"),
    ("https://medtronic.wd1.myworkdayjobs.com/", "falta el nombre del portal"),
])
def test_datos_workday_errores(url, mensaje):
    with pytest.raises(ValueError, match=mensaje):
        datos_workday(url)


def test_crear_fuente_rechaza_direcciones_desconocidas():
    with pytest.raises(ValueError, match="no es de Workday"):
        crear_fuente(Empresa("X", "https://x.com"), None, Ajustes())


def oferta(n, ruta=True):
    datos = {"title": f"Intern {n}", "locationsText": "Madrid, Spain", "postedOn": "Posted Today"}
    if ruta:
        datos["externalPath"] = f"/job/Madrid/Intern-{n}_R{n}"
    return datos


class PortalFalso:
    """Simula la API de búsqueda de Workday: `por_termino` = nº de ofertas por término."""

    def __init__(self, por_termino, fichas=None):
        self.por_termino = por_termino
        self.fichas = fichas or {}
        self.peticiones = []

    def __call__(self, metodo, url, json=None, **_):
        self.peticiones.append((metodo, url, json))
        if metodo == "GET":
            ficha = self.fichas.get(url)
            return RespuestaFalsa(200, ficha) if ficha is not None else RespuestaFalsa(404, url=url)
        todas = self.por_termino[json["searchText"]]
        return RespuestaFalsa(200, {"jobPostings": todas[json["offset"]:json["offset"] + json["limit"]]})


def fuente(portal, max_por_termino=100):
    c = ClienteHttp(enviar=portal, dormir=lambda _: None, log=lambda _: None)
    return FuenteWorkday("Medtronic", "https://medtronic.wd1.myworkdayjobs.com/MedtronicCareers", c,
                         max_por_termino=max_por_termino)


def test_buscar_pagina_y_quita_duplicados_entre_terminos():
    portal = PortalFalso({"intern": [oferta(i) for i in range(45)],
                          "trainee": [oferta(i) for i in range(40, 50)]})
    resultados = fuente(portal).buscar(["intern", "trainee"])

    assert len(resultados) == 50
    offsets = [p[2]["offset"] for p in portal.peticiones if p[2]["searchText"] == "intern"]
    assert offsets == [0, 20, 40]
    assert resultados[0] == Resultado(
        titulo="Intern 0", ubicacion="Madrid, Spain", publicada="Posted Today",
        url="https://medtronic.wd1.myworkdayjobs.com/MedtronicCareers/job/Madrid/Intern-0_R0",
        ruta="/job/Madrid/Intern-0_R0")


def test_buscar_respeta_el_maximo_por_termino():
    portal = PortalFalso({"intern": [oferta(i) for i in range(200)]})
    assert len(fuente(portal, max_por_termino=40).buscar(["intern"])) == 40


def test_buscar_ignora_resultados_sin_enlace():
    portal = PortalFalso({"intern": [oferta(1), oferta(2, ruta=False)]})
    assert [r.titulo for r in fuente(portal).buscar(["intern"])] == ["Intern 1"]


def test_detalle_une_ubicaciones_y_pais_y_lee_la_fecha():
    api = "https://medtronic.wd1.myworkdayjobs.com/wday/cxs/medtronic/MedtronicCareers/job/X"
    portal = PortalFalso({}, {api: {"jobPostingInfo": {
        "location": "Madrid", "additionalLocations": ["Barcelona", {"descriptor": "Lisboa"}],
        "country": {"descriptor": "Spain"}, "startDate": "2026-10-30"}}})
    r = Resultado("Intern", "2 Locations", "", "u", "/job/X")
    assert fuente(portal).detalle(r) == Detalle("Madrid, Barcelona, Lisboa, Spain", True, "2026-10-30")


def test_detalle_sin_fecha_o_con_fecha_rara():
    api = "https://medtronic.wd1.myworkdayjobs.com/wday/cxs/medtronic/MedtronicCareers/job/X"
    portal = PortalFalso({}, {api: {"jobPostingInfo": {"location": "Madrid", "startDate": "pronto"}}})
    r = Resultado("Intern", "Madrid", "", "u", "/job/X")
    assert fuente(portal).detalle(r) == Detalle("Madrid", True, "")


def test_detalle_si_falla_devuelve_sin_verificar():
    r = Resultado("Intern", "2 Locations", "", "u", "/job/NoExiste")
    assert fuente(PortalFalso({})).detalle(r) == Detalle("", False)
