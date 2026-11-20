"""Punto de entrada de línea de comandos.

Ejemplos:
  python buscar_ofertas.py                      ejecución normal
  python buscar_ofertas.py --dry-run            busca y muestra, sin guardar ni crear avisos
  python buscar_ofertas.py --empresa Almirall   solo esa empresa (se puede repetir)
"""
import argparse
import os
import sys
from datetime import date

from buscador import __version__
from buscador.almacen import AlmacenCsv
from buscador.avisos import AVISOS, escribir_avisos, texto_aviso
from buscador.config import ErrorConfig, cargar_config
from buscador.fuentes import crear_fuente
from buscador.http import ClienteHttp
from buscador.pipeline import ejecutar


def _argumentos(argv):
    p = argparse.ArgumentParser(prog="buscar_ofertas",
                                description="Busca ofertas de prácticas nuevas en los portales de config.yaml.")
    p.add_argument("--config", default="config.yaml", help="archivo de configuración (por defecto: config.yaml)")
    p.add_argument("--vistas", default="ofertas_vistas.csv",
                   help="registro de ofertas ya revisadas (por defecto: ofertas_vistas.csv)")
    p.add_argument("--dry-run", action="store_true",
                   help="busca y muestra las ofertas nuevas sin guardar el registro ni crear avisos")
    p.add_argument("--empresa", action="append", metavar="NOMBRE",
                   help="consulta solo esta empresa (sin distinguir mayúsculas); se puede repetir")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p.parse_args(argv)


def main(argv=None, enviar=None, dormir=None, hoy=None, log=print):
    """Ejecuta el buscador y devuelve el código de salida (0 = bien, 1 = error).
    `enviar`, `dormir` y `hoy` solo se usan en los tests."""
    args = _argumentos(argv)
    try:
        config = cargar_config(args.config)
    except ErrorConfig as error:
        log(f"❌ {error}")
        return 1
    for aviso in config.avisos:
        log(f"⚠️  {aviso}")

    if args.empresa:
        pedidas = {n.lower() for n in args.empresa}
        config.empresas = [e for e in config.empresas if e.nombre.lower() in pedidas]
        if not config.empresas:
            log(f"❌ Ninguna empresa de config.yaml se llama {', '.join(args.empresa)}")
            return 1

    cliente = ClienteHttp(pausa=config.ajustes.pausa, enviar=enviar, dormir=dormir, log=log)
    almacen = AlmacenCsv(args.vistas)
    vistas = almacen.cargar()
    hoy = hoy or date.today().isoformat()

    resultado = ejecutar(config, lambda e: crear_fuente(e, cliente, config.ajustes), vistas, hoy, log=log)

    if args.dry_run:
        for categoria, (_, titulo) in AVISOS.items():
            ofertas = [o for o in resultado.nuevas if o.categoria == categoria]
            if ofertas:
                log("\n" + texto_aviso(ofertas, titulo, "", config.ajustes.max_en_aviso, args.vistas))
        log("(modo prueba: no se ha guardado el registro ni se han creado avisos)")
    else:
        almacen.guardar(vistas)
        escribir_avisos(resultado.nuevas, config.usuario_github, config.ajustes.max_en_aviso,
                        archivo_vistas=args.vistas, resumen=os.environ.get("GITHUB_STEP_SUMMARY"))

    log(f"\nTotal: {resultado.total_espana} nuevas en España y "
        f"{resultado.total_internacional} nuevas en otros países.")
    log(f"Peticiones por código HTTP -> {cliente.resumen() or 'ninguna'} "
        f"(esperado en reintentos: {cliente.esperado:.0f} s; "
        f"empresas con error: {resultado.fallos}/{len(config.empresas)})")

    if config.empresas and resultado.fallos == len(config.empresas):
        if resultado.limitadas == resultado.fallos:
            log("❌ Todos los portales han respondido 429 (demasiadas peticiones) incluso tras reintentar: "
                "Workday está limitando las peticiones que llegan desde GitHub. No es un problema de "
                "config.yaml; la próxima ejecución lo volverá a intentar.")
        else:
            log("❌ No se pudo consultar ninguna empresa. Revisa las direcciones de config.yaml.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
