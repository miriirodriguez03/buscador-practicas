"""
Buscador de ofertas de prácticas en portales Workday.
Paso 2 del sistema de candidaturas: detecta ofertas nuevas, las filtra
por título y ubicación, las guarda en ofertas_vistas.csv y prepara un aviso.
No hace falta tocar este archivo: todo se configura en config.yaml.
"""
import csv
import os
import re
import sys
import time
import unicodedata
from datetime import date
from urllib.parse import urlparse

import requests
import yaml

ARCHIVO_CONFIG = "config.yaml"
ARCHIVO_VISTAS = "ofertas_vistas.csv"
ARCHIVO_AVISO = "nuevas_ofertas.md"
COLUMNAS = ["empresa", "titulo", "ubicacion", "publicada", "pasa_filtro", "detectada_el", "url"]
MAX_POR_TERMINO = 100   # resultados máximos que se revisan por término y empresa
MAX_EN_AVISO = 100      # ofertas máximas que se listan en un mismo aviso
PAUSA = 1.0             # segundos entre peticiones, para no sobrecargar los portales
CABECERAS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (buscador personal de practicas)",
}


def normalizar(texto):
    """Pasa a minúsculas y quita tildes: 'Prácticas' -> 'practicas'."""
    texto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in texto if not unicodedata.combining(c)).lower()


def contiene_alguna(texto, palabras):
    """True si el texto contiene alguna de las palabras como palabra completa."""
    texto = normalizar(texto)
    return any(re.search(r"\b" + re.escape(normalizar(p)) + r"\b", texto) for p in palabras or [])


def datos_workday(url):
    """De 'https://medtronic.wd1.myworkdayjobs.com/en-US/MedtronicCareers' saca host, tenant y portal."""
    partes = urlparse(url.strip())
    host = partes.netloc
    if "myworkdayjobs.com" not in host:
        raise ValueError("la dirección no es de Workday (no contiene myworkdayjobs.com)")
    tenant = host.split(".")[0]
    segmentos = [s for s in partes.path.split("/") if s]
    segmentos = [s for s in segmentos if not re.fullmatch(r"[a-z]{2}-[A-Z]{2}", s)]  # quita 'en-US', etc.
    if not segmentos:
        raise ValueError("falta el nombre del portal al final de la dirección")
    return host, tenant, segmentos[0]


def buscar_en_workday(host, tenant, portal, termino):
    """Devuelve las ofertas que el portal muestra al buscar 'termino'."""
    api = f"https://{host}/wday/cxs/{tenant}/{portal}/jobs"
    ofertas, offset = [], 0
    while offset < MAX_POR_TERMINO:
        cuerpo = {"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": termino}
        respuesta = requests.post(api, json=cuerpo, headers=CABECERAS, timeout=30)
        respuesta.raise_for_status()
        pagina = respuesta.json().get("jobPostings", [])
        ofertas.extend(pagina)
        if len(pagina) < 20:
            break
        offset += 20
        time.sleep(PAUSA)
    return ofertas


def ubicacion_detallada(host, tenant, portal, ruta):
    """Abre la ficha de la oferta para conocer su ubicación completa (país incluido).
    Devuelve (texto, True) si lo consigue o ("", False) si no."""
    try:
        respuesta = requests.get(f"https://{host}/wday/cxs/{tenant}/{portal}{ruta}",
                                 headers=CABECERAS, timeout=30)
        respuesta.raise_for_status()
        info = respuesta.json().get("jobPostingInfo", {})
        trozos = [info.get("location", "")]
        for extra in info.get("additionalLocations", []) or []:
            trozos.append(extra if isinstance(extra, str) else str(extra.get("descriptor", "")))
        trozos.append((info.get("country") or {}).get("descriptor", ""))
        texto = ", ".join(t for t in trozos if t)
        return texto, bool(texto)
    except Exception:
        return "", False


def cargar_vistas():
    if not os.path.exists(ARCHIVO_VISTAS):
        return {}
    with open(ARCHIVO_VISTAS, encoding="utf-8", newline="") as f:
        return {fila["url"]: fila for fila in csv.DictReader(f)}


def guardar_vistas(vistas):
    with open(ARCHIVO_VISTAS, "w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUMNAS)
        escritor.writeheader()
        for fila in vistas.values():
            escritor.writerow({c: fila.get(c, "") for c in COLUMNAS})


def escribir_aviso(nuevas, usuario):
    """Crea nuevas_ofertas.md solo si hay ofertas nuevas (GitHub lo convierte en un aviso)."""
    if os.path.exists(ARCHIVO_AVISO):
        os.remove(ARCHIVO_AVISO)
    if not nuevas:
        return
    limpiar = lambda t: (t or "").replace("|", "/")
    lineas = []
    if usuario and usuario != "tu-usuario":
        lineas.append(f"@{usuario.lstrip('@')}")
    lineas += [f"**{len(nuevas)} ofertas nuevas** que encajan con tus filtros:", "",
               "| Empresa | Puesto | Ubicación | Publicada |", "|---|---|---|---|"]
    for o in nuevas[:MAX_EN_AVISO]:
        lineas.append(f"| {limpiar(o['empresa'])} | [{limpiar(o['titulo'])}]({o['url']}) "
                      f"| {limpiar(o['ubicacion'])} | {limpiar(o['publicada'])} |")
    if len(nuevas) > MAX_EN_AVISO:
        lineas.append(f"\n…y {len(nuevas) - MAX_EN_AVISO} más. Las tienes todas en `{ARCHIVO_VISTAS}`.")
    texto = "\n".join(lineas) + "\n"
    with open(ARCHIVO_AVISO, "w", encoding="utf-8") as f:
        f.write(texto)
    resumen = os.environ.get("GITHUB_STEP_SUMMARY")  # resumen visible en la página de la ejecución
    if resumen:
        with open(resumen, "a", encoding="utf-8") as f:
            f.write(texto)


def main():
    with open(ARCHIVO_CONFIG, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    empresas = config.get("empresas") or []
    terminos = config.get("terminos_busqueda") or ["intern"]
    palabras_titulo = config.get("palabras_titulo") or []
    excluidas = config.get("palabras_excluidas") or []
    ubicaciones = config.get("ubicaciones") or []

    vistas = cargar_vistas()
    nuevas = []
    fallos = 0
    hoy = date.today().isoformat()

    for empresa in empresas:
        nombre = empresa.get("nombre", "¿sin nombre?")
        try:
            host, tenant, portal = datos_workday(empresa.get("url", ""))
            encontradas = {}
            for termino in terminos:
                for oferta in buscar_en_workday(host, tenant, portal, termino):
                    encontradas[oferta["externalPath"]] = oferta
                time.sleep(PAUSA)
        except Exception as error:
            print(f"⚠️  {nombre}: no se pudo consultar ({error})")
            fallos += 1
            continue

        nuevas_empresa = 0
        for ruta, oferta in encontradas.items():
            url = f"https://{host}/{portal}{ruta}"
            if url in vistas:
                continue  # ya la habíamos visto en otra ejecución
            titulo = oferta.get("title", "")
            ubicacion = oferta.get("locationsText", "")
            pasa = contiene_alguna(titulo, palabras_titulo) and not contiene_alguna(titulo, excluidas)
            if pasa and ubicaciones:
                detalle, ok = ubicacion_detallada(host, tenant, portal, ruta)
                time.sleep(PAUSA)
                if ok:
                    ubicacion = detalle
                    pasa = contiene_alguna(ubicacion, ubicaciones)
                else:
                    ubicacion += " (ubicación sin verificar)"  # mejor avisar que perderla
            fila = {"empresa": nombre, "titulo": titulo, "ubicacion": ubicacion,
                    "publicada": oferta.get("postedOn", ""), "pasa_filtro": "si" if pasa else "no",
                    "detectada_el": hoy, "url": url}
            vistas[url] = fila
            if pasa:
                nuevas.append(fila)
                nuevas_empresa += 1
        print(f"✅ {nombre}: {len(encontradas)} resultados revisados, {nuevas_empresa} nuevas que encajan")

    guardar_vistas(vistas)
    escribir_aviso(nuevas, config.get("usuario_github"))
    print(f"\nTotal: {len(nuevas)} ofertas nuevas que encajan con tus filtros.")

    if empresas and fallos == len(empresas):
        print("❌ No se pudo consultar ninguna empresa. Revisa las direcciones de config.yaml.")
        sys.exit(1)


if __name__ == "__main__":
    main()
