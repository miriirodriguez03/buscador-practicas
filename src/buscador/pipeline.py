"""Orquestación: consulta cada empresa, filtra, clasifica y decide qué ofertas son nuevas."""
from dataclasses import dataclass, field

from buscador.filtros import clasificar, pasa_titulo
from buscador.modelos import ESPANA, INTERNACIONAL, Oferta


@dataclass
class ResultadoEjecucion:
    nuevas: list = field(default_factory=list)   # Ofertas que pasan los filtros y no se habían visto
    revisadas: int = 0                           # empresas consultadas con éxito
    fallos: int = 0                              # empresas que no se pudieron consultar
    limitadas: int = 0                           # de ellas, las que fallaron por un 429

    @property
    def total_espana(self):
        return sum(1 for o in self.nuevas if o.categoria == ESPANA)

    @property
    def total_internacional(self):
        return len(self.nuevas) - self.total_espana


def _codigo_http(error):
    return getattr(getattr(error, "response", None), "status_code", None)


def evaluar(resultado, fuente, config, hoy):
    """Convierte un Resultado en Oferta aplicando el filtro de título y, si lo pasa,
    pidiendo la ficha para clasificar por ubicación."""
    ubicacion, categoria = resultado.ubicacion, ""
    pasa = pasa_titulo(resultado.titulo, config.palabras_titulo, config.palabras_excluidas)
    if pasa:
        detalle, ok = fuente.ubicacion_detallada(resultado)
        fuente.pausa()
        categoria, pasa, ubicacion = clasificar(detalle if ok else ubicacion, ok,
                                                config.ubicaciones_espana,
                                                config.ubicaciones_internacionales)
    return Oferta(empresa=fuente.nombre, titulo=resultado.titulo, ubicacion=ubicacion,
                  categoria=categoria, publicada=resultado.publicada, pasa_filtro=pasa,
                  detectada_el=hoy, url=resultado.url)


def ejecutar(config, crear_fuente, vistas, hoy, log=print):
    """Recorre las empresas de la config. Añade a `vistas` (dict url -> fila) todas las
    ofertas nuevas revisadas, pasen o no los filtros, y devuelve un ResultadoEjecucion.

    `crear_fuente(empresa)` devuelve la Fuente de esa empresa (o lanza ValueError)."""
    resultado = ResultadoEjecucion()
    for empresa in config.empresas:
        try:
            fuente = crear_fuente(empresa)
            encontrados = fuente.buscar(config.terminos)
        except Exception as error:
            log(f"⚠️  {empresa.nombre}: no se pudo consultar ({error})")
            resultado.fallos += 1
            if _codigo_http(error) == 429:
                resultado.limitadas += 1
            continue

        resultado.revisadas += 1
        cuenta = {ESPANA: 0, INTERNACIONAL: 0}
        for r in encontrados:
            if r.url in vistas:
                continue  # ya la habíamos visto en otra ejecución
            oferta = evaluar(r, fuente, config, hoy)
            vistas[r.url] = oferta.a_fila()
            if oferta.pasa_filtro:
                resultado.nuevas.append(oferta)
                cuenta[oferta.categoria] += 1
        log(f"✅ {empresa.nombre}: {len(encontrados)} resultados revisados, "
            f"{cuenta[ESPANA]} nuevas en España, {cuenta[INTERNACIONAL]} nuevas en otros países")
    return resultado
