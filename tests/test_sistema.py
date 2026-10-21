import json
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from sistema_experto.base_conocimiento import (  # noqa: E402
    RUTA_KB_DEFECTO, BaseConocimiento, ErrorBaseConocimiento, Regla)
from sistema_experto.hechos import cargar_hechos  # noqa: E402
from sistema_experto.motor import EstrategiaConflictos, MotorInferencia  # noqa: E402


def ejecutar(caso, criterios=None):
    kb = BaseConocimiento.desde_archivo(RUTA_KB_DEFECTO)
    hechos = cargar_hechos(RAIZ / "casos" / caso)
    estrategia = EstrategiaConflictos(criterios) if criterios else EstrategiaConflictos()
    return MotorInferencia(kb, estrategia).ejecutar(hechos)


class TestBaseConocimiento(unittest.TestCase):
    def setUp(self):
        self.kb = BaseConocimiento.desde_archivo(RUTA_KB_DEFECTO)

    def test_al_menos_15_reglas(self):
        self.assertGreaterEqual(len(self.kb.reglas), 15)

    def test_hay_encadenamiento(self):
        self.assertGreater(len(self.kb.encadenamientos()), 0)
        self.assertGreaterEqual(self.kb.profundidad_maxima(), 3)

    def test_base_sin_advertencias(self):
        self.assertEqual(self.kb.advertencias, [])

    def test_archivo_inexistente(self):
        with self.assertRaises(ErrorBaseConocimiento):
            BaseConocimiento.desde_archivo("no_existe.json")

    def test_ids_duplicados(self):
        r = Regla("R1", "a", ("x",), ("y",))
        with self.assertRaises(ErrorBaseConocimiento):
            BaseConocimiento([r, r])


class TestInferencia(unittest.TestCase):
    def test_caso1_fuente(self):
        s = ejecutar("caso_01_no_enciende.txt")
        self.assertIn("falla_fuente_poder", s.diagnosticos())
        self.assertIn("rec_reemplazar_fuente", s.recomendaciones())

    def test_caso2_malware_y_ram(self):
        s = ejecutar("caso_02_lento_malware_y_ram.txt")
        self.assertIn("infeccion_malware", s.diagnosticos())
        self.assertIn("memoria_insuficiente", s.diagnosticos())
        # La recomendación de mayor prioridad (malware) va primero.
        self.assertEqual(s.recomendaciones()[0], "rec_aislar_y_escanear")

    def test_caso3_dns(self):
        s = ejecutar("caso_03_sin_internet_dns.txt")
        self.assertEqual(s.recomendaciones(), ["rec_configurar_dns"])

    def test_caso4_cadena_de_tres_niveles(self):
        s = ejecutar("caso_04_disco_fallando.txt")
        ids = [p.seleccionada.id for p in s.pasos]
        self.assertLess(ids.index("R17"), ids.index("R18"))
        self.assertLess(ids.index("R18"), ids.index("R19"))
        self.assertEqual(s.recomendaciones()[0], "rec_respaldar_y_reemplazar_disco")
        self.assertIn("rec_migrar_a_ssd", s.recomendaciones())

    def test_caso6_sin_recomendacion(self):
        s = ejecutar("caso_06_datos_insuficientes.txt")
        self.assertEqual(s.recomendaciones(), [])

    def test_json_ignora_hechos_falsos(self):
        hechos = cargar_hechos(RAIZ / "casos" / "caso_07_arranque.json")
        self.assertNotIn("disco_no_detectado_bios", hechos)
        s = ejecutar("caso_07_arranque.json")
        self.assertEqual(s.recomendaciones(), ["rec_reparar_arranque"])

    def test_refraccion(self):
        for caso in sorted((RAIZ / "casos").iterdir()):
            s = ejecutar(caso.name)
            ids = [p.seleccionada.id for p in s.pasos]
            self.assertEqual(len(ids), len(set(ids)), caso.name)

    def test_determinismo(self):
        a = [p.seleccionada.id for p in ejecutar("caso_02_lento_malware_y_ram.txt").pasos]
        b = [p.seleccionada.id for p in ejecutar("caso_02_lento_malware_y_ram.txt").pasos]
        self.assertEqual(a, b)


class TestResolucionConflictos(unittest.TestCase):
    def _kb(self):
        return BaseConocimiento([
            Regla("R1", "a->c", ("a",), ("c",), orden=0),
            Regla("R2", "b->d", ("b",), ("d",), orden=1),
            Regla("R3", "c->e", ("c",), ("e",), orden=2),
        ])

    def _orden(self, criterios):
        s = MotorInferencia(self._kb(), EstrategiaConflictos(criterios)).ejecutar(["a", "b"])
        return [p.seleccionada.id for p in s.pasos]

    def test_recencia_prefiere_hechos_nuevos(self):
        self.assertEqual(self._orden(["recencia", "orden"]), ["R1", "R3", "R2"])

    def test_orden_sin_recencia(self):
        self.assertEqual(self._orden(["orden"]), ["R1", "R2", "R3"])

    def test_prioridad_gana(self):
        kb = BaseConocimiento([
            Regla("R1", "baja", ("a",), ("x",), prioridad=1, orden=0),
            Regla("R2", "alta", ("a",), ("y",), prioridad=9, orden=1),
        ])
        s = MotorInferencia(kb).ejecutar(["a"])
        self.assertEqual(s.pasos[0].seleccionada.id, "R2")

    def test_especificidad_gana(self):
        kb = BaseConocimiento([
            Regla("R1", "general", ("a",), ("x",), orden=0),
            Regla("R2", "especifica", ("a", "b"), ("y",), orden=1),
        ])
        s = MotorInferencia(kb, EstrategiaConflictos(["especificidad", "orden"])).ejecutar(["a", "b"])
        self.assertEqual(s.pasos[0].seleccionada.id, "R2")

    def test_azar_reproducible(self):
        def corrida():
            kb = self._kb()
            e = EstrategiaConflictos(["azar"], semilla=7)
            return [p.seleccionada.id for p in MotorInferencia(kb, e).ejecutar(["a", "b"]).pasos]
        self.assertEqual(corrida(), corrida())

    def test_criterio_invalido(self):
        with self.assertRaises(ValueError):
            EstrategiaConflictos(["inexistente"])


if __name__ == "__main__":
    unittest.main()
