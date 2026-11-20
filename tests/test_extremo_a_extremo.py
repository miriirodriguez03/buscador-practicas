"""Ejecuta el programa completo contra 91 respuestas reales de Workday grabadas
(Medtronic, CompuGroup Medical y Almirall).

La salida esperada se generó con el código de la fase 2 y se verificó contra la de la
fase 1 sobre la misma grabación: mismas ofertas, misma clasificación y mismos avisos,
salvo la columna 'Publicada', que ahora muestra la fecha exacta cuando se conoce."""
import csv
import shutil

import pytest
import yaml

from buscador.cli import main
from conftest import FIXTURES, Reproductor, RespuestaFalsa

HOY = "2026-11-20"   # fecha en la que se grabaron las respuestas
PETICIONES_BUSQUEDA = 33   # de las 91 grabadas; el resto son fichas de ofertas


@pytest.fixture
def carpeta(tmp_path, monkeypatch):
    shutil.copy(FIXTURES / "config_reducida.yaml", tmp_path / "config.yaml")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    return tmp_path


def _leer(ruta):
    return ruta.read_text(encoding="utf-8")


def _registros(ruta):
    with open(ruta, encoding="utf-8", newline="") as f:
        return {fila["url"]: fila for fila in csv.DictReader(f)}


def ejecutar(hoy=HOY, argumentos=()):
    lineas, rep = [], Reproductor(FIXTURES / "workday_grabacion.json")
    codigo = main(list(argumentos), enviar=rep, dormir=lambda _: None, hoy=hoy, log=lineas.append)
    return codigo, "\n".join(lineas), rep.llamadas


def test_salida_esperada(carpeta):
    codigo, texto, llamadas = ejecutar()

    assert codigo == 0
    assert llamadas == 91
    for nombre in ("ofertas_vistas.csv", "nuevas_espana.md", "nuevas_internacional.md"):
        assert _leer(carpeta / nombre) == _leer(FIXTURES / f"esperado_{nombre}"), nombre
    assert "Total: 5 nuevas en España y 10 nuevas en otros países." in texto
    assert "17/11/2026" in _leer(carpeta / "nuevas_espana.md")   # fecha exacta de la ficha


def test_segunda_ejecucion_no_repite_avisos_ni_abre_fichas(carpeta):
    ejecutar()
    codigo, texto, llamadas = ejecutar(hoy="2026-11-21")

    assert codigo == 0
    assert llamadas == PETICIONES_BUSQUEDA     # ninguna ficha: todo estaba ya evaluado
    assert not (carpeta / "nuevas_espana.md").exists()
    assert not (carpeta / "nuevas_internacional.md").exists()
    assert "Total: 0 nuevas en España y 0 nuevas en otros países." in texto
    registros = _registros(carpeta / "ofertas_vistas.csv")
    assert all(r["primera_vez"] == HOY and r["ultima_vez"] == "2026-11-21" for r in registros.values())


def test_ampliar_un_filtro_recupera_ofertas_descartadas(carpeta):
    ejecutar()   # con ubicaciones_internacionales: Germany, Netherlands, Switzerland
    descartadas = {u for u, r in _registros(carpeta / "ofertas_vistas.csv").items()
                   if r["categoria"] == "internacional" and r["pasa_filtro"] == "no"}
    assert descartadas

    config = yaml.safe_load(_leer(carpeta / "config.yaml"))
    config["ubicaciones_internacionales"] = []   # ahora, cualquier país
    (carpeta / "config.yaml").write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    codigo, texto, llamadas = ejecutar(hoy="2026-11-21")

    assert codigo == 0
    assert llamadas == PETICIONES_BUSQUEDA     # la ubicación ya se conocía: no se reabren fichas
    assert f"Total: 0 nuevas en España y {len(descartadas)} nuevas en otros países." in texto
    assert f"{len(descartadas)} de ellas ya se habían visto antes" in texto
    registros = _registros(carpeta / "ofertas_vistas.csv")
    assert all(registros[u]["avisada_el"] == "2026-11-21" for u in descartadas)
    # las avisadas el primer día no se repiten
    aviso = _leer(carpeta / "nuevas_internacional.md")
    assert all(u in aviso for u in descartadas)
    assert sum(1 for r in registros.values() if r["avisada_el"] == HOY) == 15


def test_migra_el_formato_antiguo_sin_repetir_avisos(carpeta):
    # Registro en el formato de las fases 0 y 1, tras haber avisado de esas mismas 15 ofertas
    shutil.copy(FIXTURES / "formato_antiguo_ofertas_vistas.csv", carpeta / "ofertas_vistas.csv")
    codigo, texto, llamadas = ejecutar(hoy="2026-11-21")

    assert codigo == 0
    assert "formato antiguo: se convierte al nuevo (370 ofertas" in texto
    assert "Total: 0 nuevas en España y 0 nuevas en otros países." in texto
    assert llamadas == PETICIONES_BUSQUEDA
    registros = _registros(carpeta / "ofertas_vistas.csv")
    assert list(next(iter(registros.values())))[-1] == "avisada_el"   # columnas nuevas
    assert sum(1 for r in registros.values() if r["avisada_el"] == HOY) == 15

    # Y la siguiente ejecución ya lee el formato nuevo sin volver a migrar
    _, texto, _ = ejecutar(hoy="2026-11-22")
    assert "formato antiguo" not in texto


def test_dry_run_no_escribe_nada(carpeta):
    codigo, texto, _ = ejecutar(argumentos=["--dry-run"])

    assert codigo == 0
    assert not (carpeta / "ofertas_vistas.csv").exists()
    assert not (carpeta / "nuevas_espana.md").exists()
    assert "PHARMACOLOGY TRAINEE" in texto
    assert "modo prueba" in texto


def test_filtrar_por_empresa(carpeta):
    codigo, texto, _ = ejecutar(argumentos=["--empresa", "almirall"])

    assert codigo == 0
    assert "✅ Almirall" in texto and "Medtronic" not in texto
    assert "Total: 4 nuevas en España y 1 nuevas en otros países." in texto


def test_empresa_inexistente(carpeta):
    lineas = []
    assert main(["--empresa", "NoExiste"], log=lineas.append) == 1
    assert "Ninguna empresa" in lineas[-1]


def test_todas_limitadas_por_429_termina_con_error(carpeta):
    lineas = []
    codigo = main([], enviar=lambda *a, **k: RespuestaFalsa(429), dormir=lambda _: None, hoy=HOY,
                  log=lineas.append)

    assert codigo == 1
    texto = "\n".join(lineas)
    assert "Todos los portales han respondido 429" in texto
    assert "429: 12" in texto  # 3 empresas x (1 intento + 3 reintentos)


def test_config_invalida_termina_con_error(carpeta):
    (carpeta / "config.yaml").write_text("empresas: Philips\n", encoding="utf-8")
    lineas = []
    assert main([], log=lineas.append) == 1
    assert "'empresas' debe ser una lista" in lineas[-1]
