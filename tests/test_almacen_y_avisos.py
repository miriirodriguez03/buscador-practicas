from buscador.almacen import AlmacenCsv, migrar_fila
from buscador.avisos import escribir_avisos
from buscador.modelos import COLUMNAS, ESPANA, INTERNACIONAL, Registro


def registro(n, categoria=ESPANA, titulo=None, **otros):
    datos = dict(url=f"https://acme/job/{n}", empresa="Acme", titulo=titulo or f"Intern {n}",
                 categoria=categoria, pasa_filtro=True, ubicacion="Madrid, Spain",
                 ubicacion_verificada="si", publicada="Posted Today", fecha_publicacion="2026-11-20",
                 fecha_exacta=False, primera_vez="2026-11-20", ultima_vez="2026-11-20",
                 avisada_el="2026-11-20")
    datos.update(otros)
    return Registro(**datos)


# --- Almacén -------------------------------------------------------------------

def test_almacen_ida_y_vuelta(tmp_path):
    almacen = AlmacenCsv(tmp_path / "vistas.csv")
    assert almacen.cargar() == {}
    registros = {r.url: r for r in (registro(1), registro(2, INTERNACIONAL, fecha_exacta=True, avisada_el=""))}
    almacen.guardar(registros)
    assert almacen.cargar() == registros
    assert almacen.migradas == 0


def test_almacen_escribe_las_columnas_en_orden(tmp_path):
    almacen = AlmacenCsv(tmp_path / "vistas.csv")
    almacen.guardar({"u": registro(1)})
    assert (tmp_path / "vistas.csv").read_text(encoding="utf-8").splitlines()[0] == ",".join(COLUMNAS)


def test_almacen_migra_el_formato_antiguo(tmp_path):
    ruta = tmp_path / "vistas.csv"
    ruta.write_text(
        "empresa,titulo,ubicacion,categoria,publicada,pasa_filtro,detectada_el,url\n"
        "A,Intern,\"Madrid, Spain\",espana,Posted 3 Days Ago,si,2026-11-14,https://a/1\n"
        "A,Sales Rep,Paris,,Posted Today,no,2026-11-14,https://a/2\n",
        encoding="utf-8")
    almacen = AlmacenCsv(ruta)
    registros = almacen.cargar()
    assert almacen.migradas == 2
    assert registros["https://a/1"].avisada_el == "2026-11-14"
    assert registros["https://a/1"].fecha_publicacion == "2026-11-11"
    assert registros["https://a/2"].avisada_el == ""


def test_migrar_fila_ubicacion_sin_verificar():
    r = migrar_fila({"url": "u", "ubicacion": "2 Locations (ubicación sin verificar)",
                     "categoria": "internacional", "pasa_filtro": "si", "detectada_el": "2026-11-14"})
    assert (r.ubicacion, r.ubicacion_verificada, r.avisada_el) == ("2 Locations", "no", "2026-11-14")


def test_migrar_fila_descartada_por_ubicacion_conserva_la_ubicacion_verificada():
    r = migrar_fila({"url": "u", "ubicacion": "Milano, Italy", "categoria": "internacional",
                     "pasa_filtro": "no", "detectada_el": "2026-11-14"})
    assert (r.ubicacion_verificada, r.pasa_filtro, r.avisada_el) == ("si", False, "")


def test_migrar_fila_de_la_version_mas_antigua_sin_categoria():
    r = migrar_fila({"url": "u", "ubicacion": "Madrid", "categoria": "", "pasa_filtro": "si",
                     "detectada_el": "2026-11-14"})
    assert (r.ubicacion_verificada, r.avisada_el) == ("", "2026-11-14")


# --- Avisos --------------------------------------------------------------------

def test_avisos_por_categoria(tmp_path):
    creados = escribir_avisos([registro(1), registro(2, INTERNACIONAL, titulo="Intern | QA")], "@ana",
                              carpeta=tmp_path)
    assert len(creados) == 2
    es = (tmp_path / "nuevas_espana.md").read_text(encoding="utf-8")
    assert es.startswith("@ana\n**1 🇪🇸 ofertas nuevas en España**")
    assert "| Acme | [Intern 1](https://acme/job/1) | Madrid, Spain | Posted Today |" in es
    intl = (tmp_path / "nuevas_internacional.md").read_text(encoding="utf-8")
    assert "[Intern / QA]" in intl  # la barra vertical rompería la tabla


def test_avisos_muestran_la_fecha_exacta_si_se_conoce(tmp_path):
    escribir_avisos([registro(1, fecha_publicacion="2026-10-30", fecha_exacta=True)], "", carpeta=tmp_path)
    assert "| Madrid, Spain | 30/10/2026 |" in (tmp_path / "nuevas_espana.md").read_text(encoding="utf-8")


def test_avisos_marcan_la_ubicacion_sin_verificar(tmp_path):
    escribir_avisos([registro(1, INTERNACIONAL, ubicacion="2 Locations", ubicacion_verificada="no")], "",
                    carpeta=tmp_path)
    texto = (tmp_path / "nuevas_internacional.md").read_text(encoding="utf-8")
    assert "2 Locations (ubicación sin verificar)" in texto


def test_avisos_borra_los_anteriores_y_omite_categorias_vacias(tmp_path):
    (tmp_path / "nuevas_internacional.md").write_text("viejo", encoding="utf-8")
    escribir_avisos([registro(1)], "", carpeta=tmp_path)
    assert (tmp_path / "nuevas_espana.md").exists()
    assert not (tmp_path / "nuevas_internacional.md").exists()


def test_avisos_sin_usuario_de_plantilla(tmp_path):
    escribir_avisos([registro(1)], "tu-usuario", carpeta=tmp_path)
    assert not (tmp_path / "nuevas_espana.md").read_text(encoding="utf-8").startswith("@")


def test_avisos_recorta_listas_largas(tmp_path):
    escribir_avisos([registro(i) for i in range(5)], "", max_en_aviso=3, carpeta=tmp_path)
    texto = (tmp_path / "nuevas_espana.md").read_text(encoding="utf-8")
    assert texto.count("| Acme |") == 3
    assert "…y 2 más" in texto


def test_avisos_en_resumen_de_github(tmp_path):
    resumen = tmp_path / "resumen.md"
    escribir_avisos([registro(1)], "", carpeta=tmp_path, resumen=resumen)
    assert "Intern 1" in resumen.read_text(encoding="utf-8")
