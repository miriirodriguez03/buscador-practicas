from pathlib import Path

import pytest

from buscador.config import ESPANA_POR_DEFECTO, ErrorConfig, cargar_config, interpretar

RAIZ = Path(__file__).parent.parent


def test_carga_el_config_real_del_repositorio():
    config = cargar_config(RAIZ / "config.yaml")
    assert config.empresas, "config.yaml debería tener empresas"
    assert all(e.url.startswith("https://") for e in config.empresas)
    assert "intern" in config.palabras_titulo
    assert config.avisos == []


def test_valores_por_defecto():
    config = interpretar({"palabras_titulo": ["intern"], "empresas": [{"nombre": "A", "url": "u"}]})
    assert config.terminos == ["intern"]
    assert config.ubicaciones_espana == ESPANA_POR_DEFECTO
    assert config.ubicaciones_internacionales == []
    assert config.ajustes.pausa == 1.0 and config.ajustes.max_por_termino == 100


def test_acepta_el_nombre_antiguo_ubicaciones():
    assert interpretar({"ubicaciones": ["Germany"]}).ubicaciones_internacionales == ["Germany"]
    # si existen las dos, manda la nueva
    datos = {"ubicaciones": ["Germany"], "ubicaciones_internacionales": []}
    assert interpretar(datos).ubicaciones_internacionales == []


def test_empresa_sin_nombre_o_url_no_rompe_la_carga():
    config = interpretar({"empresas": [{"url": "https://a.wd1.myworkdayjobs.com/x"}, {"nombre": "B"}]})
    assert [(e.nombre, e.url) for e in config.empresas] == [
        ("¿sin nombre?", "https://a.wd1.myworkdayjobs.com/x"), ("B", "")]


def test_ajustes_personalizados():
    config = interpretar({"ajustes": {"pausa": 0.5, "max_por_termino": 60, "max_en_aviso": 30}})
    assert (config.ajustes.pausa, config.ajustes.max_por_termino, config.ajustes.max_en_aviso) == (0.5, 60, 30)


@pytest.mark.parametrize("datos, mensaje", [
    ({"empresas": "Philips"}, "'empresas' debe ser una lista"),
    ({"empresas": ["Philips"]}, "la empresa nº 1"),
    ({"palabras_titulo": "intern"}, "'palabras_titulo' debe ser una lista"),
    ({"ajustes": {"pausa": "rápido"}}, "'ajustes.pausa' debe ser un número"),
    (["no", "es", "un", "diccionario"], "claves del tipo"),
])
def test_errores_de_estructura(datos, mensaje):
    with pytest.raises(ErrorConfig, match=mensaje):
        interpretar(datos)


def test_avisos_no_graves():
    config = interpretar({"palabras_titulo": ["intern"], "empresa": []})
    assert any("clave desconocida 'empresa'" in a for a in config.avisos)
    assert any("no hay ninguna empresa" in a for a in config.avisos)


def test_yaml_mal_escrito(tmp_path):
    ruta = tmp_path / "config.yaml"
    ruta.write_text("empresas:\n\t- nombre: A\n", encoding="utf-8")
    with pytest.raises(ErrorConfig, match="no es YAML válido"):
        cargar_config(ruta)


def test_archivo_inexistente(tmp_path):
    with pytest.raises(ErrorConfig, match="no se encuentra"):
        cargar_config(tmp_path / "no.yaml")
