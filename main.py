"""Punto de entrada: sin argumentos abre la GUI; con argumentos usa la CLI."""
import sys

from sistema_experto.cli import main_cli


def main() -> int:
    if len(sys.argv) == 1 or "--gui" in sys.argv:
        try:
            from sistema_experto.gui import iniciar_gui
        except ImportError:
            print("Tkinter no está disponible en esta instalación de Python.\n"
                  "Use la consola, por ejemplo:\n"
                  "  python main.py --hechos casos/caso_01_no_enciende.txt")
            return 1
        iniciar_gui()
        return 0
    return main_cli()


if __name__ == "__main__":
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass
    sys.exit(main())
