"""Ejecuta el programa completo contra 91 respuestas reales de Workday grabadas
(Medtronic, CompuGroup Medical y Almirall) y exige el mismo resultado (contenido
idéntico, sin contar los finales de línea, que dependen del sistema operativo) que
produjo el script original (buscar_ofertas.py de la fase 0) con esas respuestas."""
import shutil

import pytest

from buscador.cli import main
from conftest import FIXTURES, Reproductor, RespuestaFalsa

HOY = "2026-11-20"  # fecha en la que se grabaron las respuestas


@pytest.fixture
def carpeta(tmp_path, monkeypatch):
    shutil.copy(FIXTURES / "config_reducida.yaml", tmp_path / "config.yaml")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    return tmp_path


def _leer(ruta):
    return ruta.read_text(encoding="utf-8")


def test_misma_salida_que_el_script_original(carpeta, reproductor, sin_esperas):
    lineas = []
    codigo = main([], enviar=reproductor, dormir=sin_esperas, hoy=HOY, log=lineas.append)

    assert codigo == 0
    assert reproductor.llamadas == 91
    for nombre in ("ofertas_vistas.csv", "nuevas_espana.md", "nuevas_internacional.md"):
        assert _leer(carpeta / nombre) == _leer(FIXTURES / f"esperado_{nombre}"), nombre
    assert "Total: 5 nuevas en España y 10 nuevas en otros países." in "\n".join(lineas)


def test_segunda_ejecucion_no_repite_avisos(carpeta, sin_esperas):
    main([], enviar=Reproductor(FIXTURES / "workday_grabacion.json"), dormir=sin_esperas, hoy=HOY, log=lambda _: None)
    csv_tras_la_primera = _leer(carpeta / "ofertas_vistas.csv")

    # Misma búsqueda otra vez: todas las ofertas ya están vistas -> no se piden fichas ni hay avisos
    lineas = []
    codigo = main([], enviar=Reproductor(FIXTURES / "workday_grabacion.json"), dormir=sin_esperas,
                  hoy="2026-11-21", log=lineas.append)

    assert codigo == 0
    assert not (carpeta / "nuevas_espana.md").exists()
    assert not (carpeta / "nuevas_internacional.md").exists()
    assert _leer(carpeta / "ofertas_vistas.csv") == csv_tras_la_primera
    assert any("Total: 0 nuevas en España y 0 nuevas en otros países." in l for l in lineas)


def test_dry_run_no_escribe_nada(carpeta, reproductor, sin_esperas):
    lineas = []
    codigo = main(["--dry-run"], enviar=reproductor, dormir=sin_esperas, hoy=HOY, log=lineas.append)

    assert codigo == 0
    assert not (carpeta / "ofertas_vistas.csv").exists()
    assert not (carpeta / "nuevas_espana.md").exists()
    texto = "\n".join(lineas)
    assert "PHARMACOLOGY TRAINEE" in texto
    assert "modo prueba" in texto


def test_filtrar_por_empresa(carpeta, reproductor, sin_esperas):
    lineas = []
    codigo = main(["--empresa", "almirall"], enviar=reproductor, dormir=sin_esperas, hoy=HOY, log=lineas.append)

    assert codigo == 0
    texto = "\n".join(lineas)
    assert "✅ Almirall" in texto and "Medtronic" not in texto
    assert "Total: 4 nuevas en España y 1 nuevas en otros países." in texto


def test_empresa_inexistente(carpeta):
    lineas = []
    assert main(["--empresa", "NoExiste"], log=lineas.append) == 1
    assert "Ninguna empresa" in lineas[-1]


def test_todas_limitadas_por_429_termina_con_error(carpeta, sin_esperas):
    lineas = []
    codigo = main([], enviar=lambda *a, **k: RespuestaFalsa(429), dormir=sin_esperas, hoy=HOY, log=lineas.append)

    assert codigo == 1
    texto = "\n".join(lineas)
    assert "Todos los portales han respondido 429" in texto
    assert "429: 12" in texto  # 3 empresas x (1 intento + 3 reintentos)
    assert (carpeta / "ofertas_vistas.csv").exists()  # el registro se guarda igualmente (vacío)


def test_config_invalida_termina_con_error(carpeta):
    (carpeta / "config.yaml").write_text("empresas: Philips\n", encoding="utf-8")
    lineas = []
    assert main([], log=lineas.append) == 1
    assert "'empresas' debe ser una lista" in lineas[-1]
