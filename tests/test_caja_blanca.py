"""
PRUEBAS DE CAJA BLANCA (camino básico) - ver docs/pruebas/caja_blanca.md
Para cada función: grafo de flujo -> complejidad ciclomática V(G) -> caminos independientes -> un caso por camino.
    python -m unittest tests.test_caja_blanca -v
No usan Gemini ni PostgreSQL.
"""
import ast
import inspect
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import diseno as d  # noqa: E402


def complejidad_ciclomatica(funcion) -> int:
    """V(G) = nodos de decisión + 1. Cuenta if, if-else en línea, for, while, except y cada condición
    de un and/or. Una condición dentro de any(...) (generador) se cuenta como una sola."""
    arbol = ast.parse(textwrap.dedent(inspect.getsource(funcion)))
    total = 1

    def visitar(nodo):
        nonlocal total
        if isinstance(nodo, ast.GeneratorExp):
            return
        if isinstance(nodo, (ast.If, ast.IfExp, ast.For, ast.While, ast.ExceptHandler)):
            total += 1
        if isinstance(nodo, ast.BoolOp):
            total += len(nodo.values) - 1
        for hijo in ast.iter_child_nodes(nodo):
            visitar(hijo)

    visitar(arbol)
    return total


class ComplejidadCiclomatica(unittest.TestCase):
    """La documentación (docs/pruebas/caja_blanca.md) dice estos números: si cambiás la función, actualizala."""

    def test_v_de_g_coincide_con_lo_documentado(self):
        self.assertEqual(complejidad_ciclomatica(d.normalizar_limite), 2)
        self.assertEqual(complejidad_ciclomatica(d.validar_parametros), 6)
        self.assertEqual(complejidad_ciclomatica(d.resolver_descarga), 5)


class NormalizarLimite(unittest.TestCase):
    """V(G) = 2: camino 1 (conversión correcta) y camino 2 (falla la conversión)."""

    def test_tc048_camino_1_conversion_correcta(self):
        self.assertEqual(d.normalizar_limite("7"), 7)

    def test_tc048_camino_2_falla_la_conversion(self):
        self.assertEqual(d.normalizar_limite("abc"), 10)
        self.assertEqual(d.normalizar_limite(None, por_defecto=6), 6)


class ValidarParametros(unittest.TestCase):
    """V(G) = 6: seis caminos independientes (nodos de decisión: 5)."""

    def test_tc049_camino_1_sin_parametros(self):
        self.assertEqual(d.validar_parametros(None), (True, None))

    def test_tc049_camino_2_provincia_fuera_del_pais(self):
        ok, motivo = d.validar_parametros({"provincia": "Uruguay"})
        self.assertFalse(ok)
        self.assertEqual(motivo, d.MENSAJE_FUERA_COBERTURA)

    def test_tc049_camino_3_provincia_cubierta_sin_ciudad(self):
        self.assertEqual(d.validar_parametros({"provincia": "Buenos Aires"}), (True, None))
        self.assertEqual(d.validar_parametros({"provincia": "Córdoba"}), (True, None))
        self.assertEqual(d.validar_parametros({"provincia": "Mendoza"}), (True, None))

    def test_tc049_camino_4_ciudad_fuera_del_pais(self):
        ok, motivo = d.validar_parametros({"ciudad": "Montevideo"})
        self.assertFalse(ok)
        self.assertEqual(motivo, d.MENSAJE_FUERA_COBERTURA)

    def test_tc049_camino_5_ciudad_cubierta(self):
        self.assertEqual(d.validar_parametros({"ciudad": "Palermo"}), (True, None))
        self.assertEqual(d.validar_parametros({"ciudad": "Rosario"}), (True, None))
        self.assertEqual(d.validar_parametros({"ciudad": "Mar del Plata"}), (True, None))

    def test_tc049_camino_6_provincia_cubierta_pero_ciudad_fuera(self):
        ok, _ = d.validar_parametros({"provincia": "Buenos Aires", "ciudad": "Montevideo"})
        self.assertFalse(ok)


class ResolverDescarga(unittest.TestCase):
    """V(G) = 5: cinco caminos independientes (cuatro terminan en None y uno devuelve el archivo)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        raiz = Path(self._tmp.name)
        self.base = raiz / "analytics"
        self.base.mkdir()
        (self.base / "datos.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        (self.base / "programa.exe").write_text("x", encoding="utf-8")
        (raiz / "secreto.csv").write_text("clave", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_tc050_camino_1_error_al_resolver_la_ruta(self):
        with mock.patch.object(Path, "resolve", side_effect=OSError("ruta inválida")):
            self.assertIsNone(d.resolver_descarga(self.base, "datos.csv"))

    def test_tc050_camino_2_fuera_de_la_carpeta_permitida(self):
        self.assertIsNone(d.resolver_descarga(self.base, "../secreto.csv"))

    def test_tc050_camino_3_extension_no_permitida(self):
        self.assertIsNone(d.resolver_descarga(self.base, "programa.exe"))

    def test_tc050_camino_4_archivo_que_no_existe(self):
        self.assertIsNone(d.resolver_descarga(self.base, "no_existe.csv"))

    def test_tc050_camino_5_archivo_valido(self):
        self.assertEqual(d.resolver_descarga(self.base, "datos.csv"), (self.base / "datos.csv").resolve())


if __name__ == "__main__":
    unittest.main()
