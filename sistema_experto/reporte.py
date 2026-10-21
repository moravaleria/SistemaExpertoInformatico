"""Formateo de la traza y de la conclusión (usado por la CLI y la GUI)."""
from __future__ import annotations


def formatear_memoria_inicial(kb, hechos) -> str:
    lineas = [f"MEMORIA DE TRABAJO INICIAL ({len(hechos)} hechos):"]
    lineas += [f"  - {kb.texto(h)}  [{h}]" for h in hechos]
    return "\n".join(lineas)


def formatear_sin_conflicto() -> str:
    return ("Conjunto de conflictos: (vacío)\n"
            "No quedan reglas aplicables: fin de la inferencia.")


def formatear_paso(paso, kb) -> str:
    r = paso.seleccionada
    l = [
        "-" * 70,
        f"CICLO {paso.ciclo}",
        f"Conjunto de conflictos ({len(paso.conflicto)} regla(s) aplicable(s)):",
    ]
    for i, (rc, desc) in enumerate(paso.conflicto, 1):
        marca = ">>" if rc.id == r.id else "  "
        l.append(f" {marca} {i}. {rc.id} {rc.nombre}  [{desc}]")
    l.append(f"Regla seleccionada: {r.id} - {r.nombre}")
    l.append(f"Motivo: {paso.motivo}")
    l.append(f"   SI {' Y '.join(r.si)}")
    l.append(f"   ENTONCES {', '.join(r.entonces)}")
    if r.explicacion:
        l.append(f"Justificación: {r.explicacion}")
    if paso.hechos_nuevos:
        l.append("Hechos nuevos en memoria: " + ", ".join(paso.hechos_nuevos))
    else:
        l.append("Hechos nuevos en memoria: ninguno (ya estaban presentes)")
    return "\n".join(l)


def formatear_conclusion(sesion) -> str:
    kb = sesion.kb
    l = ["=" * 70, "RESULTADO DE LA INFERENCIA", "=" * 70,
         f"Reglas disparadas: {len(sesion.pasos)}"]
    if sesion.pasos:
        l.append("Orden de disparo: " + " -> ".join(p.seleccionada.id for p in sesion.pasos))
    inter = [h for h, m in sesion.memoria.items()
             if kb.tipo(h) == "intermedio" and m["origen"] == "inferido"]
    if inter:
        l.append("Hechos intermedios inferidos: " + ", ".join(inter))

    l += ["", "DIAGNÓSTICO(S):"]
    diag = sesion.diagnosticos()
    l += [f"  * {kb.texto(d)}" for d in diag] or ["  (ninguno)"]

    l += ["", "RECOMENDACIÓN DEL SISTEMA EXPERTO:"]
    recs = sesion.recomendaciones()
    if recs:
        for i, rec in enumerate(recs, 1):
            l.append(f"  {i}. {kb.texto(rec)}")
            l.append("     Cadena de razonamiento:")
            l += ["     " + x for x in sesion.explicar(rec)]
    else:
        l.append("  El sistema no pudo emitir una recomendación con los hechos "
                 "ingresados. Ingrese más síntomas u observaciones.")
    return "\n".join(l)
