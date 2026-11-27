"""
Pruebas de la red neuronal propia de Foody (backend/modelo_foody.py) - ver docs/pruebas/modelo_propio.md

    python -m unittest tests.test_modelo_propio -v
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import diseno as d  # noqa: E402
import modelo_foody as m  # noqa: E402


def etiquetas(texto):
    e = m.predecir(texto)
    return set(e["restricciones"] + e["cocinas"] + e["precio"])


class RedNeuronal(unittest.TestCase):
    def test_los_pesos_estan_y_son_livianos(self):
        self.assertTrue(m.RUTA_PESOS.exists())
        self.assertLess(m.RUTA_PESOS.stat().st_size, 1024 * 1024)
        self.assertTrue(m.disponible())

    def test_entiende_errores_de_tipeo(self):
        casos = {"pizeria": {"pizzeria"}, "sin tak": {"sin_tacc"}, "hamburgesas veganas": {"hamburguesa", "vegano"},
                 "susi": {"japonesa"}, "heladria": {"heladeria"}, "algo begano": {"vegano"}}
        for texto, esperado in casos.items():
            self.assertEqual(etiquetas(texto), esperado, texto)

    def test_entiende_palabras_que_las_reglas_no_conocen(self):
        for texto, esperado in {"pastas": {"italiana"}, "ceviche": {"peruana"}, "libre de gluten": {"sin_tacc"},
                                "tacos": {"mexicana"}, "medialunas": {"panaderia"}}.items():
            self.assertEqual(etiquetas(texto), esperado, texto)

    def test_no_inventa_etiquetas(self):
        for texto in ("tengo hambre", "asdf qwerty", "", "milanesas", "algo sin azucar",
                      "cerca de mi casa", "gracias", "restaurantes"):
            self.assertEqual(etiquetas(texto), set(), texto)

    def test_probabilidades_entre_0_y_1(self):
        for p in m.probabilidades("pizza vegana sin tacc").values():
            self.assertTrue(0.0 <= p <= 1.0)


class IntegracionConElInterprete(unittest.TestCase):
    def test_corrige_tipeo_en_comida_restriccion_y_zona(self):
        p = d.interpretar_consulta_local("algo begano en villa urqiza")
        self.assertEqual(p.get("ciudad"), "Villa Urquiza")
        self.assertTrue(p.get("requiere_vegano"))
        p = d.interpretar_consulta_local("pastas en palrmo")
        self.assertEqual((p.get("ciudad"), p.get("tipo_cocina")), ("Palermo", ["italiana"]))

    def test_el_nombre_de_la_zona_no_confunde_a_la_red(self):
        p = d.interpretar_consulta_local("restaurante en Cafayate")
        self.assertNotIn("tipo_cocina", p)

    def test_apagada_sigue_funcionando_con_reglas(self):
        with mock.patch.dict(os.environ, {"FOODY_MODELO": "off"}):
            self.assertEqual(m.predecir("pizeria"), {"restricciones": [], "cocinas": [], "precio": [], "intenciones": []})
            p = d.interpretar_consulta_local("pizzería sin TACC en Palermo")
        self.assertEqual((p["ciudad"], p["tipo_cocina"], p["requiere_sin_tacc"]), ("Palermo", ["pizzeria"], True))

    def test_nunca_quita_una_restriccion_de_las_reglas(self):
        # Aunque la red no la detecte, la restricción que encontraron las reglas se mantiene.
        with mock.patch.object(m, "predecir", return_value={"restricciones": [], "cocinas": []}):
            p = d.interpretar_consulta_local("algo sin gluten y vegano")
        self.assertTrue(p["requiere_sin_tacc"] and p["requiere_vegano"])

    def test_pesos_danados_no_rompen_foody(self):
        with mock.patch.object(m, "RUTA_PESOS", m.RUTA_PESOS.with_name("no_existe.json")), \
                mock.patch.object(m, "_cargada", False), mock.patch.object(m, "_red", None):
            self.assertEqual(m.probabilidades("pizza"), {})
            self.assertEqual(d.interpretar_consulta_local("pizzería en Palermo")["tipo_cocina"], ["pizzeria"])


def _buscar_falso(params):
    _buscar_falso.ultimo = params
    return {"restaurants": [{"id": 1, "name": "Lo de Ana", "city": params.get("ciudad") or "Palermo",
                             "address": "Calle 123", "source": "OpenStreetMap", "cuisine": "pizza"}]}


def responder(texto, historial=None):
    _buscar_falso.ultimo = None
    t, _ = d.armar_respuesta_sin_ia(texto, _buscar_falso, historial=historial)
    return t


class IntencionesYPrecio(unittest.TestCase):
    def test_reconoce_intenciones(self):
        casos = {"que es sin tacc?": "pregunta_que_es", "soy intolerante a la lactosa": "otra_restriccion",
                 "fui a ese lugar y estaba horrible": "opinion", "cual es la capital de francia?": "fuera_de_tema",
                 "chau foody": "despedida", "que podes hacer?": "ayuda"}
        for texto, intencion in casos.items():
            self.assertIn(intencion, m.predecir(texto)["intenciones"], texto)

    def test_precio_barato_filtra(self):
        p = d.interpretar_consulta_local("pizzeria barata en palermo")
        self.assertEqual((p["ciudad"], p["tipo_cocina"], p["precio_maximo"]), ("Palermo", ["pizzeria"], 2))
        self.assertEqual(d.interpretar_consulta_local("sushi que no sea muy caro en belgrano").get("precio_maximo"), 2)
        self.assertNotIn("precio_maximo", d.interpretar_consulta_local("sushi en belgrano"))


class RespuestasAmables(unittest.TestCase):
    def test_explica_que_es_sin_tacc_con_advertencia(self):
        t = responder("¿qué es sin TACC?")
        self.assertIn("trigo, avena, cebada", t)
        self.assertIn("confirmar", t)
        self.assertIsNone(_buscar_falso.ultimo)                # explicar no consulta la base

    def test_explica_la_diferencia_vegano_vegetariano(self):
        self.assertIn("La diferencia es", responder("que diferencia hay entre vegano y vegetariano?"))

    def test_otra_restriccion_sin_zona_pide_zona_y_no_promete(self):
        t = responder("los lacteos me caen mal, donde puedo comer?")
        self.assertIn("sin lactosa", t)
        self.assertIn("consultes con el local", t)
        self.assertIsNone(_buscar_falso.ultimo)

    def test_otra_restriccion_con_zona_busca_y_avisa(self):
        t = responder("algo sin lactosa en palermo")
        self.assertEqual(_buscar_falso.ultimo.get("ciudad"), "Palermo")
        self.assertIn("confirmalo con el local", t)

    def test_fuera_de_tema_redirige_con_amabilidad(self):
        t = responder("¿Cuál es la capital de Francia?")
        self.assertTrue(t.startswith("Perdón"))
        self.assertIn("comida", t)

    def test_opinion_agradece(self):
        self.assertIn("Gracias por contarme", responder("fui a la esquina y estaba re caro"))

    def test_saludo_con_busqueda_saluda_y_busca(self):
        t = responder("Hola, busco sushi en Palermo")
        self.assertTrue(t.startswith("¡Hola!"))
        self.assertEqual(_buscar_falso.ultimo.get("tipo_cocina"), ["japonesa"])

    def test_mas_barato_retoma_la_busqueda_anterior(self):
        responder("¿Cuál es el más barato?", historial=["pizzería en Palermo"])
        self.assertEqual((_buscar_falso.ultimo["ciudad"], _buscar_falso.ultimo["tipo_cocina"],
                          _buscar_falso.ultimo["precio_maximo"]), ("Palermo", ["pizzeria"], 2))

    def test_las_busquedas_normales_no_cambian(self):
        responder("pizzería sin TACC en Palermo")
        self.assertEqual(_buscar_falso.ultimo["requiere_sin_tacc"], True)


if __name__ == "__main__":
    unittest.main()
