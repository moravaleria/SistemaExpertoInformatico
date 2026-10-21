"""Carga y validación de los hechos iniciales (Memoria de Trabajo).

Formatos admitidos:

* ``.txt``: un hecho por línea; ``#`` inicia un comentario.
* ``.json``: lista de hechos (``["tos", "fiebre"]``) o diccionario
  ``{"tos": true, "fiebre": false}``. Solo se cargan los valores verdaderos
  (a diferencia del código original, que trataba cualquier clave como hecho).
"""
from __future__ import annotations

import json
from pathlib import Path


class ErrorHechos(ValueError):
    """El archivo de hechos no existe o tiene un formato inválido."""


def normalizar(hecho) -> str:
    return "_".join(str(hecho).strip().lower().split())


def cargar_hechos(ruta) -> list[str]:
    ruta = Path(ruta)
    try:
        texto = ruta.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ErrorHechos(f"No existe el archivo de hechos: {ruta}") from None

    if ruta.suffix.lower() == ".json":
        try:
            datos = json.loads(texto)
        except json.JSONDecodeError as e:
            raise ErrorHechos(f"JSON inválido en {ruta}: {e}") from None
        if isinstance(datos, dict) and isinstance(datos.get("hechos"), (dict, list)):
            datos = datos["hechos"]
        if isinstance(datos, dict):
            crudos = [h for h, v in datos.items() if v is True]
        elif isinstance(datos, list):
            crudos = datos
        else:
            raise ErrorHechos("El JSON debe ser una lista o un diccionario de hechos.")
    else:
        crudos = []
        for linea in texto.splitlines():
            linea = linea.split("#", 1)[0].strip()
            if linea:
                crudos.append(linea)

    hechos: list[str] = []
    for h in map(normalizar, crudos):
        if h and h not in hechos:
            hechos.append(h)
    return hechos


def separar_desconocidos(kb, hechos):
    """Devuelve (hechos que la BC conoce, hechos que no aparecen en la BC)."""
    conocidos = kb.hechos_conocidos()
    validos = [h for h in hechos if h in conocidos]
    desconocidos = [h for h in hechos if h not in conocidos]
    return validos, desconocidos


def preguntar_hechos(kb, entrada=input, salida=print) -> list[str]:
    """Ingreso interactivo: pregunta por cada síntoma de la BC."""
    salida("Responda s (sí) o n (no, por defecto). Escriba f para terminar.\n")
    hechos = []
    for s in kb.sintomas():
        resp = entrada(f"¿{kb.texto(s)}? [s/N/f] ").strip().lower()
        if resp == "f":
            break
        if resp in ("s", "si", "sí", "y", "yes"):
            hechos.append(s)
    return hechos
