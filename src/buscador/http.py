"""Cliente HTTP común a todas las fuentes: pausas, reintentos y estadísticas."""
import time
from urllib.parse import urlparse

import requests

CABECERAS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (buscador personal de practicas)",
}
CODIGOS_REINTENTABLES = {429, 500, 502, 503, 504}
SIN_CONEXION = "sin conexión"


def segundos_retry_after(respuesta):
    """Segundos que el portal pide esperar en la cabecera Retry-After (None si no lo indica)."""
    valor = (respuesta.headers.get("Retry-After") or "").strip()
    return float(valor) if valor.isdigit() and int(valor) > 0 else None


class ClienteHttp:
    """Hace peticiones HTTP con reintentos ante 429, errores 5xx y cortes de conexión.

    - reintentos: segundos de espera antes de cada reintento (su longitud = nº de reintentos)
    - espera_maxima: tope cuando el portal indica cuánto esperar (cabecera Retry-After)
    - presupuesto: máximo de segundos de espera por reintentos en toda la ejecución
    - pausa: segundos entre peticiones normales, para no sobrecargar los portales

    `enviar` y `dormir` se pueden sustituir en los tests para no usar la red ni esperar.
    """

    def __init__(self, pausa=1.0, reintentos=(20, 60, 120), espera_maxima=300,
                 presupuesto=15 * 60, timeout=30, enviar=None, dormir=None, log=print):
        self.pausa_segundos = pausa
        self.reintentos = tuple(reintentos)
        self.espera_maxima = espera_maxima
        self.presupuesto = presupuesto
        self.timeout = timeout
        self._enviar = enviar or requests.request
        self._dormir = dormir or time.sleep
        self._log = log
        self.esperado = 0.0      # segundos ya esperados por reintentos
        self.respuestas = {}     # código HTTP (o SIN_CONEXION) -> número de respuestas

    def _contar(self, clave):
        self.respuestas[clave] = self.respuestas.get(clave, 0) + 1

    def pausa(self):
        """Pausa de cortesía entre peticiones."""
        self._dormir(self.pausa_segundos)

    def peticion(self, metodo, url, **opciones):
        """Hace la petición. Si el portal responde 429 o un error temporal 5xx, o si la
        conexión falla (corte de red, DNS, timeout), espera y reintenta (respetando
        Retry-After y el presupuesto total). Si no se recupera, lanza el error."""
        for intento in range(len(self.reintentos) + 1):
            ultimo = intento == len(self.reintentos)
            try:
                respuesta = self._enviar(metodo, url, headers=CABECERAS, timeout=self.timeout, **opciones)
            except (requests.ConnectionError, requests.Timeout) as error:
                self._contar(SIN_CONEXION)
                if ultimo or self.esperado + self.reintentos[intento] > self.presupuesto:
                    raise
                motivo, espera = f"sin conexión ({type(error).__name__})", self.reintentos[intento]
            else:
                self._contar(respuesta.status_code)
                if respuesta.status_code not in CODIGOS_REINTENTABLES or ultimo:
                    break
                espera = min(segundos_retry_after(respuesta) or self.reintentos[intento], self.espera_maxima)
                if self.esperado + espera > self.presupuesto:
                    break  # ya se ha esperado bastante en esta ejecución: no se insiste más
                motivo = f"respondió {respuesta.status_code}"
            self._log(f"   ⏳ {urlparse(url).netloc} {motivo}; reintento en {espera:.0f} s")
            self._dormir(espera)
            self.esperado += espera
        respuesta.raise_for_status()
        return respuesta

    def resumen(self):
        """Texto con el número de respuestas por código, p. ej. '200: 91, 429: 3'."""
        return ", ".join(f"{c}: {n}" for c, n in sorted(self.respuestas.items(), key=lambda par: str(par[0])))
