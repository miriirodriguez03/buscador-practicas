import pytest

from buscador.filtros import clasificar, contiene_alguna, normalizar, pasa_titulo
from buscador.modelos import ESPANA, INTERNACIONAL

ESPANA_LISTA = ["Spain", "España", "Madrid", "Sant Cugat"]


def test_normalizar_quita_tildes_y_mayusculas():
    assert normalizar("Prácticas en ESPAÑA") == "practicas en espana"
    assert normalizar(None) == ""


@pytest.mark.parametrize("texto, palabras, esperado", [
    ("Summer Intern - R&D", ["intern"], True),
    ("Internal Auditor", ["intern"], False),           # palabra completa, no prefijo
    ("Becario de Prácticas", ["practicas"], True),     # sin tildes en la lista
    ("Werkstudent (m/w/d)", ["werkstudent"], True),
    ("Co-op Engineering", ["co-op"], True),
    ("Anything", [], False),
    ("Anything", None, False),
])
def test_contiene_alguna(texto, palabras, esperado):
    assert contiene_alguna(texto, palabras) is esperado


def test_pasa_titulo_con_excluidas():
    assert pasa_titulo("R&D Intern", ["intern"], ["senior"])
    assert not pasa_titulo("Senior Intern Manager", ["intern"], ["senior"])
    assert not pasa_titulo("Quality Engineer", ["intern"], [])


def test_clasificar_espana_aunque_comparta_con_otros_paises():
    assert clasificar("Madrid, Spain, Paris, France", True, ESPANA_LISTA, ["Germany"]) == \
        (ESPANA, True, "Madrid, Spain, Paris, France")


def test_clasificar_ciudad_de_respaldo():
    assert clasificar("Sant Cugat del Vallès", True, ESPANA_LISTA, [])[0] == ESPANA


def test_clasificar_internacional_filtrado_por_pais():
    assert clasificar("Munich, Germany", True, ESPANA_LISTA, ["Germany"]) == (INTERNACIONAL, True, "Munich, Germany")
    assert clasificar("Shanghai, China", True, ESPANA_LISTA, ["Germany"]) == (INTERNACIONAL, False, "Shanghai, China")


def test_clasificar_internacional_sin_filtro_acepta_todo():
    assert clasificar("Shanghai, China", True, ESPANA_LISTA, []) == (INTERNACIONAL, True, "Shanghai, China")


def test_clasificar_sin_verificar_se_marca_para_revisar():
    assert clasificar("2 Locations", False, ESPANA_LISTA, ["Germany"]) == \
        (INTERNACIONAL, True, "2 Locations (ubicación sin verificar)")
