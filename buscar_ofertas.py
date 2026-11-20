"""
Buscador de ofertas de prácticas en portales Workday.
Detecta ofertas nuevas, las filtra por título, las clasifica en
ESPAÑA / OTROS PAÍSES y prepara un aviso separado para cada categoría.
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
AVISOS = {  # categoría -> (archivo del aviso, título que aparece dentro del aviso)
    "espana": ("nuevas_espana.md", "🇪🇸 ofertas nuevas en España"),
    "internacional": ("nuevas_internacional.md", "🌍 ofertas nuevas en otros países"),
}
COLUMNAS = ["empresa", "titulo", "ubicacion", "categoria", "publicada",
            "pasa_filtro", "detectada_el", "url"]
MAX_POR_TERMINO = 100   # resultados máximos que se revisan por término y empresa
MAX_EN_AVISO = 100      # ofertas máximas que se listan en un mismo aviso
PAUSA = 1.0             # segundos entre peticiones, para no sobrecargar los portales
CABECERAS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (buscador personal de practicas)",
}
ESPANA_POR_DEFECTO = ["Spain", "España"]
# Si un portal responde 429 (demasiadas peticiones) o un error temporal 5xx, se espera y se reintenta
REINTENTOS = (20, 60, 120)       # segundos de espera antes de cada reintento
ESPERA_MAXIMA_REINTENTO = 300    # tope cuando el portal indica cuánto esperar (cabecera Retry-After)
PRESUPUESTO_ESPERAS = 15 * 60    # máximo de segundos de espera por reintentos en toda la ejecución
CODIGOS_REINTENTABLES = {429, 500, 502, 503, 504}
_esperado = 0.0                  # segundos ya esperados por reintentos en esta ejecución
_respuestas = {}                 # código HTTP -> número de respuestas (para el diagnóstico final)


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


def segundos_retry_after(respuesta):
    """Segundos que el portal pide esperar en la cabecera Retry-After (None si no lo indica)."""
    valor = (respuesta.headers.get("Retry-After") or "").strip()
    return float(valor) if valor.isdigit() and int(valor) > 0 else None


def peticion(metodo, url, **opciones):
    """Hace la petición HTTP. Si el portal responde 429 o un error temporal 5xx, espera y
    reintenta (respetando Retry-After y el presupuesto total de esperas). Si no se recupera,
    lanza el error igual que antes."""
    global _esperado
    for intento in range(len(REINTENTOS) + 1):
        respuesta = requests.request(metodo, url, headers=CABECERAS, timeout=30, **opciones)
        _respuestas[respuesta.status_code] = _respuestas.get(respuesta.status_code, 0) + 1
        if respuesta.status_code not in CODIGOS_REINTENTABLES or intento == len(REINTENTOS):
            break
        espera = min(segundos_retry_after(respuesta) or REINTENTOS[intento], ESPERA_MAXIMA_REINTENTO)
        if _esperado + espera > PRESUPUESTO_ESPERAS:
            break  # ya se ha esperado bastante en esta ejecución: no se insiste más
        print(f"   ⏳ {urlparse(url).netloc} respondió {respuesta.status_code}; reintento en {espera:.0f} s")
        time.sleep(espera)
        _esperado += espera
    respuesta.raise_for_status()
    return respuesta


def buscar_en_workday(host, tenant, portal, termino):
    """Devuelve las ofertas que el portal muestra al buscar 'termino'."""
    api = f"https://{host}/wday/cxs/{tenant}/{portal}/jobs"
    ofertas, offset = [], 0
    while offset < MAX_POR_TERMINO:
        cuerpo = {"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": termino}
        respuesta = peticion("POST", api, json=cuerpo)
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
        respuesta = peticion("GET", f"https://{host}/wday/cxs/{tenant}/{portal}{ruta}")
        info = respuesta.json().get("jobPostingInfo", {})
        trozos = [info.get("location", "")]
        for extra in info.get("additionalLocations", []) or []:
            trozos.append(extra if isinstance(extra, str) else str(extra.get("descriptor", "")))
        trozos.append((info.get("country") or {}).get("descriptor", ""))
        texto = ", ".join(t for t in trozos if t)
        return texto, bool(texto)
    except Exception:
        return "", False


def clasificar(ubicacion, verificada, espana, internacionales):
    """Devuelve (categoria, pasa_filtro, ubicacion_mostrada).
    - España: si alguna de sus ubicaciones está en España (también si comparte con otros países).
    - Otros países: el resto, filtrado por 'ubicaciones_internacionales' si la lista no está vacía.
    - Si no se pudo comprobar la ubicación, va a 'Otros países' marcada para que la revises."""
    if contiene_alguna(ubicacion, espana):
        return "espana", True, ubicacion
    if not verificada:
        return "internacional", True, f"{ubicacion} (ubicación sin verificar)"
    if internacionales:
        return "internacional", contiene_alguna(ubicacion, internacionales), ubicacion
    return "internacional", True, ubicacion


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


def escribir_avisos(nuevas, usuario):
    """Crea un archivo de aviso por categoría, solo si esa categoría tiene ofertas nuevas."""
    limpiar = lambda t: (t or "").replace("|", "/")
    resumen = os.environ.get("GITHUB_STEP_SUMMARY")  # resumen visible en la página de la ejecución
    for categoria, (archivo, titulo) in AVISOS.items():
        if os.path.exists(archivo):
            os.remove(archivo)
        ofertas = [o for o in nuevas if o["categoria"] == categoria]
        if not ofertas:
            continue
        lineas = []
        if usuario and usuario != "tu-usuario":
            lineas.append(f"@{usuario.lstrip('@')}")
        lineas += [f"**{len(ofertas)} {titulo}** que encajan con tus filtros:", "",
                   "| Empresa | Puesto | Ubicación | Publicada |", "|---|---|---|---|"]
        for o in ofertas[:MAX_EN_AVISO]:
            lineas.append(f"| {limpiar(o['empresa'])} | [{limpiar(o['titulo'])}]({o['url']}) "
                          f"| {limpiar(o['ubicacion'])} | {limpiar(o['publicada'])} |")
        if len(ofertas) > MAX_EN_AVISO:
            lineas.append(f"\n…y {len(ofertas) - MAX_EN_AVISO} más. Las tienes todas en `{ARCHIVO_VISTAS}`.")
        texto = "\n".join(lineas) + "\n"
        with open(archivo, "w", encoding="utf-8") as f:
            f.write(texto)
        if resumen:
            with open(resumen, "a", encoding="utf-8") as f:
                f.write(texto + "\n")


def main():
    with open(ARCHIVO_CONFIG, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    empresas = config.get("empresas") or []
    terminos = config.get("terminos_busqueda") or ["intern"]
    palabras_titulo = config.get("palabras_titulo") or []
    excluidas = config.get("palabras_excluidas") or []
    espana = config.get("ubicaciones_espana") or ESPANA_POR_DEFECTO
    # 'ubicaciones' es el nombre antiguo de la lista: se sigue aceptando
    internacionales = config.get("ubicaciones_internacionales", config.get("ubicaciones")) or []

    vistas = cargar_vistas()
    nuevas = []
    fallos = 0
    limitadas = 0  # empresas que fallaron porque el portal respondió 429
    hoy = date.today().isoformat()

    for empresa in empresas:
        nombre = empresa.get("nombre", "¿sin nombre?")
        try:
            host, tenant, portal = datos_workday(empresa.get("url", ""))
            encontradas = {}
            for termino in terminos:
                for oferta in buscar_en_workday(host, tenant, portal, termino):
                    if oferta.get("externalPath"):  # algunos resultados llegan sin enlace: se ignoran
                        encontradas[oferta["externalPath"]] = oferta
                time.sleep(PAUSA)
        except Exception as error:
            print(f"⚠️  {nombre}: no se pudo consultar ({error})")
            fallos += 1
            if getattr(getattr(error, "response", None), "status_code", None) == 429:
                limitadas += 1
            continue

        cuenta = {"espana": 0, "internacional": 0}
        for ruta, oferta in encontradas.items():
            url = f"https://{host}/{portal}{ruta}"
            if url in vistas:
                continue  # ya la habíamos visto en otra ejecución
            titulo = oferta.get("title", "")
            ubicacion = oferta.get("locationsText", "")
            categoria = ""
            pasa = contiene_alguna(titulo, palabras_titulo) and not contiene_alguna(titulo, excluidas)
            if pasa:
                detalle, ok = ubicacion_detallada(host, tenant, portal, ruta)
                time.sleep(PAUSA)
                categoria, pasa, ubicacion = clasificar(detalle if ok else ubicacion, ok,
                                                        espana, internacionales)
            fila = {"empresa": nombre, "titulo": titulo, "ubicacion": ubicacion,
                    "categoria": categoria, "publicada": oferta.get("postedOn", ""),
                    "pasa_filtro": "si" if pasa else "no", "detectada_el": hoy, "url": url}
            vistas[url] = fila
            if pasa:
                nuevas.append(fila)
                cuenta[categoria] += 1
        print(f"✅ {nombre}: {len(encontradas)} resultados revisados, "
              f"{cuenta['espana']} nuevas en España, {cuenta['internacional']} nuevas en otros países")

    guardar_vistas(vistas)
    escribir_avisos(nuevas, config.get("usuario_github"))
    total_es = sum(1 for o in nuevas if o["categoria"] == "espana")
    print(f"\nTotal: {total_es} nuevas en España y {len(nuevas) - total_es} nuevas en otros países.")
    codigos = ", ".join(f"{c}: {n}" for c, n in sorted(_respuestas.items()))
    print(f"Peticiones por código HTTP -> {codigos or 'ninguna'} "
          f"(esperado en reintentos: {_esperado:.0f} s; empresas con error: {fallos}/{len(empresas)})")

    if empresas and fallos == len(empresas):
        if limitadas == fallos:
            print("❌ Todos los portales han respondido 429 (demasiadas peticiones) incluso tras reintentar: "
                  "Workday está limitando las peticiones que llegan desde GitHub. No es un problema de "
                  "config.yaml; la próxima ejecución lo volverá a intentar.")
        else:
            print("❌ No se pudo consultar ninguna empresa. Revisa las direcciones de config.yaml.")
        sys.exit(1)


if __name__ == "__main__":
    main()
