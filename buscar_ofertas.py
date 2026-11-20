"""
Buscador de ofertas de prácticas.

Este archivo solo arranca el programa; el código está en src/buscador/.
Se conserva para que ejecutar_local.ps1 y el workflow sigan funcionando igual.
Todo se configura en config.yaml. Opciones: python buscar_ofertas.py --help
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from buscador.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
