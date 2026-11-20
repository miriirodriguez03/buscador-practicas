import pytest
import requests

from buscador.http import SIN_CONEXION, ClienteHttp
from conftest import RespuestaFalsa


def secuencia(*respuestas):
    """Función 'enviar' que devuelve (o lanza) cada elemento por orden."""
    pendientes = list(respuestas)

    def enviar(*_, **__):
        r = pendientes.pop(0)
        if isinstance(r, Exception):
            raise r
        return r
    return enviar


def cliente(enviar, esperas, **opciones):
    return ClienteHttp(enviar=enviar, dormir=esperas.append, log=lambda _: None, **opciones)


def test_reintenta_429_y_se_recupera():
    esperas = []
    c = cliente(secuencia(RespuestaFalsa(429), RespuestaFalsa(503), RespuestaFalsa(200, {"ok": 1})), esperas)
    assert c.peticion("GET", "https://x").json() == {"ok": 1}
    assert esperas == [20, 60]
    assert c.esperado == 80
    assert c.respuestas == {429: 1, 503: 1, 200: 1}


def test_respeta_retry_after_con_tope():
    esperas = []
    c = cliente(secuencia(RespuestaFalsa(429, cabeceras={"Retry-After": "5"}),
                          RespuestaFalsa(429, cabeceras={"Retry-After": "9999"}),
                          RespuestaFalsa(200)), esperas)
    c.peticion("GET", "https://x")
    assert esperas == [5, 300]


def test_se_rinde_tras_los_reintentos():
    esperas = []
    c = cliente(secuencia(*[RespuestaFalsa(429)] * 4), esperas)
    with pytest.raises(requests.HTTPError) as error:
        c.peticion("GET", "https://x")
    assert error.value.response.status_code == 429
    assert esperas == [20, 60, 120]


def test_respeta_el_presupuesto_total_de_esperas():
    esperas = []
    c = cliente(secuencia(RespuestaFalsa(429), RespuestaFalsa(429)), esperas, presupuesto=50)
    with pytest.raises(requests.HTTPError):
        c.peticion("GET", "https://x")
    assert esperas == [20]  # la siguiente espera (60 s) superaría el presupuesto


def test_no_reintenta_errores_definitivos():
    esperas = []
    c = cliente(secuencia(RespuestaFalsa(404)), esperas)
    with pytest.raises(requests.HTTPError):
        c.peticion("GET", "https://x")
    assert esperas == []


def test_reintenta_cortes_de_conexion():
    esperas = []
    c = cliente(secuencia(requests.ConnectionError("dns"), requests.Timeout("lento"), RespuestaFalsa(200)), esperas)
    assert c.peticion("GET", "https://x").status_code == 200
    assert esperas == [20, 60]
    assert c.respuestas == {SIN_CONEXION: 2, 200: 1}


def test_corte_de_conexion_persistente_se_relanza():
    esperas = []
    c = cliente(secuencia(*[requests.ConnectionError("dns")] * 4), esperas)
    with pytest.raises(requests.ConnectionError):
        c.peticion("GET", "https://x")
    assert esperas == [20, 60, 120]


def test_resumen_ordena_codigos_y_textos():
    c = cliente(secuencia(), [])
    c.respuestas = {429: 2, 200: 5, SIN_CONEXION: 1}
    assert c.resumen() == "200: 5, 429: 2, sin conexión: 1"
