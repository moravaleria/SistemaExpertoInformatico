"""Interfaz de línea de comandos."""
from __future__ import annotations

import argparse

from . import reporte
from .base_conocimiento import RUTA_KB_DEFECTO, BaseConocimiento, ErrorBaseConocimiento
from .hechos import ErrorHechos, cargar_hechos, preguntar_hechos, separar_desconocidos
from .motor import ESTRATEGIA_POR_DEFECTO, EstrategiaConflictos, MotorInferencia


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="main.py",
        description="Sistema experto de diagnóstico de fallas informáticas "
                    "(sin argumentos se abre la interfaz gráfica).",
    )
    p.add_argument("--kb", default=str(RUTA_KB_DEFECTO),
                   help="archivo JSON con la base de conocimiento")
    p.add_argument("--hechos", help="archivo .txt o .json con los hechos iniciales")
    p.add_argument("--interactivo", action="store_true",
                   help="preguntar los síntomas por consola")
    p.add_argument("--paso-a-paso", action="store_true",
                   help="pausar después de cada ciclo de inferencia")
    p.add_argument("--criterios", default=",".join(ESTRATEGIA_POR_DEFECTO),
                   help="criterios de resolución de conflictos separados por coma "
                        "(prioridad, especificidad, recencia, orden, azar)")
    p.add_argument("--semilla", type=int, help="semilla para el criterio 'azar'")
    p.add_argument("--gui", action="store_true", help="abrir la interfaz gráfica")
    return p


def main_cli(argv=None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)
    if not args.hechos and not args.interactivo:
        parser.print_help()
        return 2

    try:
        kb = BaseConocimiento.desde_archivo(args.kb)
        estrategia = EstrategiaConflictos(
            [c.strip() for c in args.criterios.split(",") if c.strip()], args.semilla)
        hechos: list[str] = []
        if args.hechos:
            hechos += cargar_hechos(args.hechos)
        if args.interactivo:
            hechos += [h for h in preguntar_hechos(kb) if h not in hechos]
    except (ErrorBaseConocimiento, ErrorHechos, ValueError) as e:
        print(f"Error: {e}")
        return 1

    for adv in kb.advertencias:
        print(f"[aviso BC] {adv}")
    hechos, desconocidos = separar_desconocidos(kb, hechos)
    if desconocidos:
        print("[aviso] Hechos ignorados (no aparecen en la BC): " + ", ".join(desconocidos))
    if not hechos:
        print("No hay hechos iniciales válidos para ejecutar la inferencia.")
        return 1

    print(f"\nBase de conocimiento: {kb.metadatos.get('nombre', args.kb)} "
          f"({len(kb.reglas)} reglas)")
    print("Estrategia de conflictos: " + " > ".join(estrategia.criterios))
    print("\n" + reporte.formatear_memoria_inicial(kb, hechos) + "\n")

    sesion = MotorInferencia(kb, estrategia).nueva_sesion(hechos)
    while True:
        paso = sesion.siguiente_paso()
        if paso is None:
            print("-" * 70)
            print(reporte.formatear_sin_conflicto() + "\n")
            break
        print(reporte.formatear_paso(paso, kb))
        if args.paso_a_paso:
            input("\n[Enter] para el siguiente ciclo... ")
    print(reporte.formatear_conclusion(sesion))
    return 0
