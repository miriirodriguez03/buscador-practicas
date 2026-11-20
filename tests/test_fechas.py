import pytest

from buscador.fechas import estimar_fecha, fecha_iso_valida, formato_corto


@pytest.mark.parametrize("texto, esperado", [
    ("Posted Today", "2026-11-20"),
    ("Posted Yesterday", "2026-11-19"),
    ("Posted 3 Days Ago", "2026-11-17"),
    ("Posted 1 Day Ago", "2026-11-19"),
    ("Posted 30+ Days Ago", "2026-10-21"),   # la fecha más reciente posible
    ("Publicado hace 2 días", "2026-11-18"),
    ("", ""),
    ("Posted recently", ""),
])
def test_estimar_fecha(texto, esperado):
    assert estimar_fecha(texto, "2026-11-20") == esperado


def test_estimar_fecha_sin_referencia_valida():
    assert estimar_fecha("Posted Today", "") == ""
    assert estimar_fecha("Posted Today", "ayer") == ""


@pytest.mark.parametrize("texto, esperado", [
    ("2026-10-30", "2026-10-30"),
    ("2026-10-30T08:00:00.000Z", "2026-10-30"),
    ("2026-13-40", ""),
    ("30/10/2026", ""),
    (None, ""),
])
def test_fecha_iso_valida(texto, esperado):
    assert fecha_iso_valida(texto) == esperado


def test_formato_corto():
    assert formato_corto("2026-10-30") == "30/10/2026"
