"""Orquestación: consulta cada empresa, actualiza el registro y decide qué avisar."""
from dataclasses import dataclass, field

from buscador.fechas import estimar_fecha
from buscador.filtros import clasificar, pasa_titulo
from buscador.modelos import ESPANA, INTERNACIONAL, Registro


@dataclass
class ResultadoEjecucion:
    nuevas: list = field(default_factory=list)   # Registros que hay que avisar en esta ejecución
    recuperadas: int = 0                         # de ellas, las que ya se habían visto antes
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


def actualizar_desde_listado(registro, resultado, empresa, hoy):
    """Refresca los datos que da el listado del portal (siempre los más recientes)."""
    registro.empresa = empresa
    registro.titulo = resultado.titulo
    registro.publicada = resultado.publicada
    registro.ultima_vez = hoy
    if not registro.primera_vez:
        registro.primera_vez = hoy
    if registro.ubicacion_verificada != "si":
        registro.ubicacion = resultado.ubicacion
    if not registro.fecha_exacta and not registro.fecha_publicacion:
        registro.fecha_publicacion = estimar_fecha(resultado.publicada, hoy)


def evaluar(registro, resultado, fuente, config):
    """Aplica los filtros al registro. Si pasa el de título y aún no se conoce la
    ubicación completa, abre la ficha (una sola vez por oferta). Devuelve True si pasa."""
    registro.categoria, registro.pasa_filtro = "", False
    if not pasa_titulo(registro.titulo, config.palabras_titulo, config.palabras_excluidas):
        return False
    if registro.ubicacion_verificada != "si":
        detalle = fuente.detalle(resultado)
        fuente.pausa()
        registro.ubicacion_verificada = "si" if detalle.verificada else "no"
        if detalle.verificada:
            registro.ubicacion = detalle.ubicacion
        if detalle.fecha_publicacion:
            registro.fecha_publicacion, registro.fecha_exacta = detalle.fecha_publicacion, True
    registro.categoria, registro.pasa_filtro, _ = clasificar(
        registro.ubicacion, registro.ubicacion_verificada == "si",
        config.ubicaciones_espana, config.ubicaciones_internacionales)
    return registro.pasa_filtro


def ejecutar(config, crear_fuente, registros, hoy, log=print):
    """Recorre las empresas de la config y actualiza `registros` (dict url -> Registro).

    - Las ofertas nuevas se añaden al registro, pasen o no los filtros.
    - Las que siguen publicadas y aún no se han avisado se vuelven a evaluar con los
      filtros actuales: si ahora pasan (p. ej. porque has ampliado un filtro), se avisan.
    - Las ya avisadas nunca se vuelven a avisar.

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
            registro = registros.get(r.url)
            ya_vista = registro is not None
            if not ya_vista:
                registro = registros[r.url] = Registro(url=r.url)
            actualizar_desde_listado(registro, r, fuente.nombre, hoy)
            if registro.avisada_el:
                continue  # ya se avisó en otra ejecución
            if evaluar(registro, r, fuente, config):
                registro.avisada_el = hoy
                resultado.nuevas.append(registro)
                resultado.recuperadas += ya_vista
                cuenta[registro.categoria] += 1
        log(f"✅ {empresa.nombre}: {len(encontrados)} resultados revisados, "
            f"{cuenta[ESPANA]} nuevas en España, {cuenta[INTERNACIONAL]} nuevas en otros países")
    return resultado
