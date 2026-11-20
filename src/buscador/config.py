"""Carga y validación de config.yaml."""
from dataclasses import dataclass, field

import yaml

ESPANA_POR_DEFECTO = ["Spain", "España"]
CLAVES_CONOCIDAS = {"usuario_github", "terminos_busqueda", "palabras_titulo", "palabras_excluidas",
                    "ubicaciones_espana", "ubicaciones_internacionales", "ubicaciones",
                    "empresas", "ajustes"}


class ErrorConfig(Exception):
    """config.yaml no se puede usar. El mensaje explica qué corregir."""


@dataclass
class Empresa:
    nombre: str
    url: str


@dataclass
class Ajustes:
    """Valores avanzados; todos son opcionales en config.yaml (sección 'ajustes')."""
    pausa: float = 1.0              # segundos entre peticiones
    max_por_termino: int = 100      # resultados máximos que se revisan por término y empresa
    max_en_aviso: int = 100         # ofertas máximas que se listan en un mismo aviso


@dataclass
class Config:
    usuario_github: str = ""
    terminos: list = field(default_factory=lambda: ["intern"])
    palabras_titulo: list = field(default_factory=list)
    palabras_excluidas: list = field(default_factory=list)
    ubicaciones_espana: list = field(default_factory=lambda: list(ESPANA_POR_DEFECTO))
    ubicaciones_internacionales: list = field(default_factory=list)
    empresas: list = field(default_factory=list)
    ajustes: Ajustes = field(default_factory=Ajustes)
    avisos: list = field(default_factory=list)   # advertencias no graves detectadas al cargar


def _lista_de_textos(datos, clave, errores):
    valor = datos.get(clave)
    if valor is None:
        return None
    if not isinstance(valor, list) or not all(isinstance(v, (str, int, float)) for v in valor):
        errores.append(f"'{clave}' debe ser una lista de textos (cada uno en una línea que empiece por '- ')")
        return None
    return [str(v) for v in valor]


def _numero(datos, clave, por_defecto, tipo, errores):
    valor = datos.get(clave, por_defecto)
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or valor < 0:
        errores.append(f"'ajustes.{clave}' debe ser un número positivo")
        return por_defecto
    return tipo(valor)


def interpretar(datos):
    """Convierte el contenido ya leído de config.yaml en un `Config` validado."""
    if datos is None:
        datos = {}
    if not isinstance(datos, dict):
        raise ErrorConfig("config.yaml debe contener claves del tipo 'nombre: valor'")

    errores, avisos = [], []
    for clave in sorted(set(datos) - CLAVES_CONOCIDAS):
        avisos.append(f"clave desconocida '{clave}' en config.yaml (se ignora; ¿está bien escrita?)")

    config = Config()
    usuario = datos.get("usuario_github")
    if usuario is not None:
        config.usuario_github = str(usuario)

    # Las listas vacías o ausentes conservan el valor por defecto, como hasta ahora
    config.terminos = _lista_de_textos(datos, "terminos_busqueda", errores) or config.terminos
    config.palabras_titulo = _lista_de_textos(datos, "palabras_titulo", errores) or []
    config.palabras_excluidas = _lista_de_textos(datos, "palabras_excluidas", errores) or []
    config.ubicaciones_espana = _lista_de_textos(datos, "ubicaciones_espana", errores) or config.ubicaciones_espana
    # 'ubicaciones' es el nombre antiguo de la lista internacional: se sigue aceptando
    clave_intl = "ubicaciones_internacionales" if "ubicaciones_internacionales" in datos else "ubicaciones"
    config.ubicaciones_internacionales = _lista_de_textos(datos, clave_intl, errores) or []

    empresas = datos.get("empresas") or []
    if not isinstance(empresas, list):
        errores.append("'empresas' debe ser una lista de bloques con 'nombre' y 'url'")
        empresas = []
    for i, e in enumerate(empresas, start=1):
        if not isinstance(e, dict):
            errores.append(f"la empresa nº {i} debe tener 'nombre:' y 'url:' (revisa la sangría)")
            continue
        config.empresas.append(Empresa(nombre=str(e.get("nombre") or "¿sin nombre?"),
                                       url=str(e.get("url") or "")))
    if not config.empresas:
        avisos.append("no hay ninguna empresa en 'empresas'")
    if not config.palabras_titulo:
        avisos.append("'palabras_titulo' está vacía: no pasará ninguna oferta")

    ajustes = datos.get("ajustes") or {}
    if not isinstance(ajustes, dict):
        errores.append("'ajustes' debe contener claves del tipo 'nombre: valor'")
        ajustes = {}
    base = Ajustes()
    config.ajustes = Ajustes(pausa=_numero(ajustes, "pausa", base.pausa, float, errores),
                             max_por_termino=_numero(ajustes, "max_por_termino", base.max_por_termino, int, errores),
                             max_en_aviso=_numero(ajustes, "max_en_aviso", base.max_en_aviso, int, errores))

    if errores:
        raise ErrorConfig("Hay que corregir config.yaml:\n  - " + "\n  - ".join(errores))
    config.avisos = avisos
    return config


def cargar_config(ruta):
    """Lee y valida config.yaml. Lanza ErrorConfig con un mensaje claro si algo falla."""
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = yaml.safe_load(f)
    except FileNotFoundError:
        raise ErrorConfig(f"no se encuentra el archivo de configuración '{ruta}'") from None
    except yaml.YAMLError as error:
        raise ErrorConfig(f"config.yaml no es YAML válido (¿tabuladores o sangría incorrecta?):\n{error}") from None
    return interpretar(datos)
