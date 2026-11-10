"""Corre las pruebas AppTest del front en modo local y api, cada una sobre una copia temporal.

Uso (desde «Overol Front»):
    python tests/correr_pruebas.py                     # todas, en local y api
    python tests/correr_pruebas.py busqueda tickets    # solo esas (prueba_<nombre>.py)
    python tests/correr_pruebas.py --modo local        # un solo modo
    python tests/correr_pruebas.py --base-nueva        # sin copiar overol.db (base demo desde cero)
    python tests/correr_pruebas.py -v                  # muestra cada verificación

Nunca usa el overol.db real (trabaja sobre una copia) ni la clave real de los documentos
(cada copia tiene su propia clave de prueba). Las copias se borran al terminar.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TESTS = Path(__file__).resolve().parent
FRONT = TESTS.parent
NO_COPIAR = shutil.ignore_patterns(
    "tests", "__pycache__", "documentos_verificacion", "*.key", ".env", ".env.*", "*.bak"
)


def correr(suite, mode, base_nueva, verbose):
    tmp = Path(tempfile.mkdtemp(prefix="overol_pruebas_"))
    copy = tmp / "front"

    try:
        shutil.copytree(FRONT, copy, ignore=NO_COPIAR)
        if base_nueva:
            for db_file in copy.glob("overol.db*"):
                db_file.unlink()

        env = dict(os.environ)
        env.pop("OVEROL_CLAVE_DOCUMENTOS", None)
        env.update(
            OVEROL_BACKEND=mode,
            OVEROL_STREAMLIT_STARTED="1",
            OVEROL_CLAVE_DOCUMENTOS_ARCHIVO=str(tmp / "clave_pruebas.key"),
            PYTHONIOENCODING="utf-8",
            PYTHONDONTWRITEBYTECODE="1",
        )
        result = subprocess.run(
            [sys.executable, str(suite), str(copy)],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    lines = result.stdout.splitlines()
    oks = sum(1 for line in lines if line.startswith("OK"))
    fails = [line for line in lines if line.startswith("FAIL")]

    if verbose:
        print("\n".join(lines))

    if fails or result.returncode:
        for line in fails:
            print("   " + line)
        if not fails:
            print("\n".join("   " + line for line in result.stderr.strip().splitlines()[-15:]))

    return result.returncode == 0, oks, len(fails)


def main():
    sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pruebas", nargs="*", help="nombres sin «prueba_» ni «.py» (por defecto, todas)")
    parser.add_argument("--modo", choices=["local", "api", "ambos"], default="ambos")
    parser.add_argument("--base-nueva", action="store_true", help="no copia overol.db: parte de la base demo")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    suites = (
        [TESTS / f"prueba_{name}.py" for name in args.pruebas]
        if args.pruebas
        else sorted(TESTS.glob("prueba_*.py"))
    )
    missing = [s.name for s in suites if not s.exists()]
    if missing:
        sys.exit(f"No existen: {', '.join(missing)}")

    modes = ["local", "api"] if args.modo == "ambos" else [args.modo]
    origin = "base demo nueva" if args.base_nueva or not (FRONT / "overol.db").exists() else "copia de overol.db"
    print(f"Pruebas sobre una {origin} - modos: {', '.join(modes)}\n")

    all_ok = True
    for mode in modes:
        for suite in suites:
            ok, oks, fails = correr(suite, mode, args.base_nueva, args.verbose)
            all_ok = all_ok and ok
            mark = "[OK]" if ok else "[X] "
            detail = f"{oks} OK" + (f", {fails} FALLO(S)" if fails else "") + ("" if ok or fails else " - se cayó")
            print(f"{mark} {suite.stem.removeprefix('prueba_'):<22} {mode:<6} {detail}")

    print("\nTODO OK" if all_ok else "\nHAY FALLOS")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
