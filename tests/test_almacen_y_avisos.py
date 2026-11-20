from buscador.almacen import AlmacenCsv
from buscador.avisos import escribir_avisos
from buscador.modelos import COLUMNAS, ESPANA, INTERNACIONAL, Oferta


def oferta(n, categoria=ESPANA, titulo=None):
    return Oferta(empresa="Acme", titulo=titulo or f"Intern {n}", ubicacion="Madrid, Spain",
                  categoria=categoria, publicada="Posted Today", pasa_filtro=True,
                  detectada_el="2026-11-20", url=f"https://acme/job/{n}")


def test_almacen_ida_y_vuelta(tmp_path):
    almacen = AlmacenCsv(tmp_path / "vistas.csv")
    assert almacen.cargar() == {}
    vistas = {o.url: o.a_fila() for o in (oferta(1), oferta(2, INTERNACIONAL))}
    almacen.guardar(vistas)
    assert almacen.cargar() == vistas


def test_almacen_conserva_filas_antiguas_y_ordena_columnas(tmp_path):
    ruta = tmp_path / "vistas.csv"
    ruta.write_text("url,empresa,titulo\nhttps://x,Vieja,Algo\n", encoding="utf-8")
    almacen = AlmacenCsv(ruta)
    almacen.guardar(almacen.cargar())
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    assert lineas[0] == ",".join(COLUMNAS)
    assert lineas[1] == "Vieja,Algo,,,,,,https://x"


def test_avisos_por_categoria(tmp_path):
    creados = escribir_avisos([oferta(1), oferta(2, INTERNACIONAL, titulo="Intern | QA")], "@ana",
                              carpeta=tmp_path)
    assert len(creados) == 2
    es = (tmp_path / "nuevas_espana.md").read_text(encoding="utf-8")
    assert es.startswith("@ana\n**1 🇪🇸 ofertas nuevas en España**")
    assert "| Acme | [Intern 1](https://acme/job/1) | Madrid, Spain | Posted Today |" in es
    intl = (tmp_path / "nuevas_internacional.md").read_text(encoding="utf-8")
    assert "[Intern / QA]" in intl  # la barra vertical rompería la tabla


def test_avisos_borra_los_anteriores_y_omite_categorias_vacias(tmp_path):
    (tmp_path / "nuevas_internacional.md").write_text("viejo", encoding="utf-8")
    escribir_avisos([oferta(1)], "", carpeta=tmp_path)
    assert (tmp_path / "nuevas_espana.md").exists()
    assert not (tmp_path / "nuevas_internacional.md").exists()


def test_avisos_sin_usuario_de_plantilla(tmp_path):
    escribir_avisos([oferta(1)], "tu-usuario", carpeta=tmp_path)
    assert not (tmp_path / "nuevas_espana.md").read_text(encoding="utf-8").startswith("@")


def test_avisos_recorta_listas_largas(tmp_path):
    escribir_avisos([oferta(i) for i in range(5)], "", max_en_aviso=3, carpeta=tmp_path)
    texto = (tmp_path / "nuevas_espana.md").read_text(encoding="utf-8")
    assert texto.count("| Acme |") == 3
    assert "…y 2 más" in texto


def test_avisos_en_resumen_de_github(tmp_path):
    resumen = tmp_path / "resumen.md"
    escribir_avisos([oferta(1)], "", carpeta=tmp_path, resumen=resumen)
    assert "Intern 1" in resumen.read_text(encoding="utf-8")
