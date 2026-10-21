"""Representación y carga de la Base de Conocimiento (BC).

La BC se almacena en un archivo JSON con tres secciones:

* ``metadatos``: nombre, dominio y versión de la base.
* ``hechos``: catálogo de hechos con su tipo (sintoma, intermedio,
  diagnostico, recomendacion) y un texto legible.
* ``reglas``: lista de reglas SI <antecedentes> ENTONCES <consecuentes>.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

TIPOS_HECHO = ("sintoma", "intermedio", "diagnostico", "recomendacion")

RUTA_KB_DEFECTO = (
    Path(__file__).resolve().parent.parent
    / "conocimiento"
    / "base_conocimiento_informatica.json"
)


class ErrorBaseConocimiento(ValueError):
    """El archivo de conocimiento no existe o tiene un formato inválido."""


@dataclass(frozen=True)
class Regla:
    id: str
    nombre: str
    si: tuple          # antecedentes (todos deben estar en la memoria de trabajo)
    entonces: tuple    # consecuentes (hechos que se agregan al dispararse)
    prioridad: int = 5  # "salience": mayor valor = más urgente
    explicacion: str = ""
    orden: int = 0     # posición en el archivo (se usa como último desempate)


class BaseConocimiento:
    def __init__(self, reglas, hechos=None, metadatos=None):
        self.reglas = list(reglas)
        self.hechos = dict(hechos or {})
        self.metadatos = dict(metadatos or {})
        self.advertencias: list[str] = []
        self._por_id: dict[str, Regla] = {}
        self._validar()

    # ------------------------------------------------------------------ carga
    @classmethod
    def desde_archivo(cls, ruta) -> "BaseConocimiento":
        ruta = Path(ruta)
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise ErrorBaseConocimiento(f"No existe el archivo: {ruta}") from None
        except json.JSONDecodeError as e:
            raise ErrorBaseConocimiento(f"JSON inválido en {ruta}: {e}") from None

        reglas = []
        for i, r in enumerate(datos.get("reglas", [])):
            try:
                reglas.append(
                    Regla(
                        id=str(r["id"]),
                        nombre=r["nombre"],
                        si=tuple(r["si"]),
                        entonces=tuple(r["entonces"]),
                        prioridad=int(r.get("prioridad", 5)),
                        explicacion=r.get("explicacion", ""),
                        orden=i,
                    )
                )
            except KeyError as e:
                raise ErrorBaseConocimiento(
                    f"La regla #{i + 1} no tiene el campo obligatorio {e}"
                ) from None
        return cls(reglas, datos.get("hechos", {}), datos.get("metadatos", {}))

    # ------------------------------------------------------------- validación
    def _validar(self):
        if not self.reglas:
            raise ErrorBaseConocimiento("La base de conocimiento no contiene reglas.")
        for r in self.reglas:
            if r.id in self._por_id:
                raise ErrorBaseConocimiento(f"Id de regla duplicado: {r.id}")
            if not r.si or not r.entonces:
                raise ErrorBaseConocimiento(
                    f"La regla {r.id} debe tener antecedentes y consecuentes."
                )
            self._por_id[r.id] = r
        for h, d in self.hechos.items():
            if d.get("tipo") not in TIPOS_HECHO:
                raise ErrorBaseConocimiento(
                    f"Tipo inválido para el hecho '{h}': {d.get('tipo')!r}"
                )

        consecuentes = {c for r in self.reglas for c in r.entonces}
        antecedentes = {a for r in self.reglas for a in r.si}
        sintomas = set(self.sintomas())
        for a in sorted(antecedentes - consecuentes - sintomas):
            self.advertencias.append(
                f"'{a}' es antecedente pero no es síntoma ni consecuente de ninguna "
                "regla: solo se activará si se ingresa como hecho inicial."
            )
        for s in sorted(sintomas - antecedentes):
            self.advertencias.append(f"El síntoma '{s}' no se usa en ninguna regla.")

    # ---------------------------------------------------------------- consulta
    def regla(self, id_regla: str) -> Regla:
        return self._por_id[id_regla]

    def tipo(self, hecho: str) -> str:
        return self.hechos.get(hecho, {}).get("tipo", "intermedio")

    def texto(self, hecho: str) -> str:
        t = self.hechos.get(hecho, {}).get("texto")
        return t or hecho.replace("_", " ").capitalize()

    def sintomas(self) -> list[str]:
        return [h for h, d in self.hechos.items() if d.get("tipo") == "sintoma"]

    def hechos_conocidos(self) -> set[str]:
        conocidos = set(self.hechos)
        for r in self.reglas:
            conocidos.update(r.si)
            conocidos.update(r.entonces)
        return conocidos

    # ------------------------------------------------- métricas de encadenamiento
    def encadenamientos(self) -> list[tuple[str, str]]:
        """Pares (productora, consumidora): un consecuente de una regla es
        antecedente de otra."""
        pares = []
        for p in self.reglas:
            for c in self.reglas:
                if p.id != c.id and set(p.entonces) & set(c.si):
                    pares.append((p.id, c.id))
        return pares

    def profundidad_maxima(self) -> int:
        """Longitud (en reglas) de la cadena de inferencia más larga."""
        productoras: dict[str, list[Regla]] = {}
        for r in self.reglas:
            for c in r.entonces:
                productoras.setdefault(c, []).append(r)
        memo: dict[str, int] = {}

        def prof(r: Regla, visitando=()):
            if r.id in memo:
                return memo[r.id]
            if r.id in visitando:
                return 0
            mejor = 0
            for a in r.si:
                for p in productoras.get(a, []):
                    mejor = max(mejor, prof(p, visitando + (r.id,)))
            memo[r.id] = 1 + mejor
            return memo[r.id]

        return max(prof(r) for r in self.reglas)
