"""Motor de inferencia con encadenamiento hacia adelante.

Ciclo reconocer-actuar (como en OPS5 / CLIPS):

1. EMPAREJAR: reglas no disparadas cuyos antecedentes están todos en la
   memoria de trabajo -> conjunto de conflictos.
2. RESOLVER: la estrategia ordena el conjunto de conflictos y elige una regla.
3. ACTUAR: se dispara la regla y sus consecuentes pasan a la memoria de trabajo.

El ciclo termina cuando el conjunto de conflictos queda vacío.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

# Criterios de resolución de conflictos disponibles y su descripción.
CRITERIOS = {
    "prioridad": "mayor prioridad explícita (salience)",
    "especificidad": "mayor especificidad (más antecedentes)",
    "recencia": "mayor recencia (usa los hechos agregados más recientemente)",
    "orden": "primera en el orden de la base de conocimiento",
    "azar": "elección al azar (semilla reproducible)",
}

# La refracción (no disparar dos veces la misma regla) siempre está activa.
ESTRATEGIA_POR_DEFECTO = ("prioridad", "especificidad", "recencia", "orden")

ESTRATEGIAS_PREDEFINIDAS = {
    "Completa: prioridad > especificidad > recencia > orden": ESTRATEGIA_POR_DEFECTO,
    "Original del taller: especificidad > orden": ("especificidad", "orden"),
    "Estilo LEX: recencia > especificidad > prioridad > orden": (
        "recencia", "especificidad", "prioridad", "orden"),
    "Con azar: prioridad > especificidad > recencia > azar": (
        "prioridad", "especificidad", "recencia", "azar"),
}


class EstrategiaConflictos:
    """Ordena el conjunto de conflictos aplicando los criterios en cascada."""

    def __init__(self, criterios=ESTRATEGIA_POR_DEFECTO, semilla=None):
        criterios = tuple(criterios)
        invalidos = [c for c in criterios if c not in CRITERIOS]
        if invalidos or not criterios:
            raise ValueError(
                f"Criterios inválidos {invalidos}. Válidos: {', '.join(CRITERIOS)}"
            )
        self.criterios = criterios
        self.rng = random.Random(semilla)

    def _valor(self, criterio, regla, memoria):
        if criterio == "prioridad":
            return regla.prioridad
        if criterio == "especificidad":
            return len(regla.si)
        if criterio == "recencia":
            # Ciclos de los antecedentes de mayor a menor; se comparan
            # lexicográficamente (idea de la estrategia LEX de OPS5).
            return tuple(sorted((memoria[a]["ciclo"] for a in regla.si), reverse=True))
        if criterio == "orden":
            return -regla.orden
        return self.rng.random()  # azar

    def ordenar(self, conflicto, memoria):
        """Devuelve [(regla, claves)] de la mejor a la peor candidata."""
        evaluadas = [
            (r, tuple(self._valor(c, r, memoria) for c in self.criterios))
            for r in conflicto
        ]
        evaluadas.sort(key=lambda t: t[1], reverse=True)  # orden estable
        return evaluadas

    def describir(self, claves) -> str:
        partes = []
        for c, v in zip(self.criterios, claves):
            if c == "prioridad":
                partes.append(f"prioridad={v}")
            elif c == "especificidad":
                partes.append(f"antecedentes={v}")
            elif c == "recencia":
                partes.append("recencia=(" + ",".join(map(str, v)) + ")")
            elif c == "orden":
                partes.append(f"orden={-v + 1}")
            else:
                partes.append(f"azar={v:.2f}")
        return ", ".join(partes)

    def explicar_eleccion(self, ordenadas) -> str:
        if len(ordenadas) == 1:
            return "única regla aplicable: no hay conflicto que resolver."
        (r1, k1), (r2, k2) = ordenadas[0], ordenadas[1]
        for c, a, b in zip(self.criterios, k1, k2):
            if a != b:
                return f"{r1.id} se impone a {r2.id} por {CRITERIOS[c]}."
        return f"empate en todos los criterios; se elige {r1.id} (primera de la lista)."


@dataclass
class Paso:
    ciclo: int
    conflicto: list          # [(Regla, descripción de claves)] de mejor a peor
    seleccionada: object     # Regla disparada
    motivo: str
    hechos_nuevos: list
    hechos_repetidos: list
    memoria: list            # hechos en memoria de trabajo tras el paso


class SesionInferencia:
    """Una ejecución del motor, avanzable ciclo a ciclo (paso a paso)."""

    def __init__(self, kb, hechos_iniciales, estrategia):
        self.kb = kb
        self.estrategia = estrategia
        # Memoria de trabajo: hecho -> {ciclo en que se agregó, origen, regla}
        self.memoria = {
            h: {"ciclo": 0, "origen": "inicial", "regla": None}
            for h in hechos_iniciales
        }
        self.disparadas: set[str] = set()   # refracción
        self.pasos: list[Paso] = []
        self.ciclo = 0
        self.terminada = False

    def conjunto_conflictos(self):
        hechos = set(self.memoria)
        return [
            r for r in self.kb.reglas
            if r.id not in self.disparadas and set(r.si) <= hechos
        ]

    def siguiente_paso(self):
        """Ejecuta un ciclo. Devuelve el Paso o None si ya no hay reglas aplicables."""
        if self.terminada:
            return None
        conflicto = self.conjunto_conflictos()
        if not conflicto:
            self.terminada = True
            return None

        self.ciclo += 1
        ordenadas = self.estrategia.ordenar(conflicto, self.memoria)
        elegida = ordenadas[0][0]
        motivo = self.estrategia.explicar_eleccion(ordenadas)
        self.disparadas.add(elegida.id)

        nuevos, repetidos = [], []
        for c in elegida.entonces:
            if c in self.memoria:
                repetidos.append(c)
            else:
                self.memoria[c] = {"ciclo": self.ciclo, "origen": "inferido",
                                   "regla": elegida.id}
                nuevos.append(c)

        paso = Paso(
            ciclo=self.ciclo,
            conflicto=[(r, self.estrategia.describir(k)) for r, k in ordenadas],
            seleccionada=elegida,
            motivo=motivo,
            hechos_nuevos=nuevos,
            hechos_repetidos=repetidos,
            memoria=list(self.memoria),
        )
        self.pasos.append(paso)
        return paso

    # ------------------------------------------------------------- resultados
    def _ordenados(self, tipo):
        hs = [h for h in self.memoria if self.kb.tipo(h) == tipo]

        def clave(h):
            m = self.memoria[h]
            r = self.kb.regla(m["regla"]) if m["regla"] else None
            return (-(r.prioridad if r else 0), m["ciclo"])

        return sorted(hs, key=clave)

    def diagnosticos(self):
        return self._ordenados("diagnostico")

    def recomendaciones(self):
        return self._ordenados("recomendacion")

    def explicar(self, hecho, nivel=0):
        """Cadena de razonamiento (árbol de derivación) de un hecho."""
        sangria = "    " * nivel
        info = self.memoria[hecho]
        if info["origen"] == "inicial":
            return [f"{sangria}- {self.kb.texto(hecho)} (dato inicial)"]
        r = self.kb.regla(info["regla"])
        lineas = [f"{sangria}- {self.kb.texto(hecho)}  <= {r.id} «{r.nombre}»"]
        for a in r.si:
            lineas += self.explicar(a, nivel + 1)
        return lineas


class MotorInferencia:
    def __init__(self, kb, estrategia=None):
        self.kb = kb
        self.estrategia = estrategia or EstrategiaConflictos()

    def nueva_sesion(self, hechos_iniciales):
        return SesionInferencia(self.kb, hechos_iniciales, self.estrategia)

    def ejecutar(self, hechos_iniciales):
        sesion = self.nueva_sesion(hechos_iniciales)
        while sesion.siguiente_paso() is not None:
            pass
        return sesion
