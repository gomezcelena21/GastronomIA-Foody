"""Pruebas de la lógica pura del diseño. Se ejecutan sin base de datos ni internet:
    python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import diseno as d  # noqa: E402

REALES = [
    {"restaurant_id": 1, "name": "Restaurante Verde", "phone": "11 1234-5678",
     "website": "https://www.restauranteverde.com", "neighborhood": "Palermo", "city": "CABA",
     "cuisine_type": ["vegana"], "address": "Av. Santa Fe 4789",
     "features": {"has_vegan_options": True}, "source_name": "Portal de Datos Abiertos CABA"},
    {"restaurant_id": 2, "name": "Raíces", "phone": None, "website": None, "features": {}},
]


class Cobertura(unittest.TestCase):
    def test_todo_el_pais_esta_cubierto(self):
        for prov in ("CABA", "Buenos Aires", "Ciudad Autónoma de Buenos Aires", "Provincia de Buenos Aires",
                     "GBA", "Córdoba", "Santa Fe", "Mendoza", "Tucumán", "Tierra del Fuego"):
            self.assertTrue(d.validar_parametros({"provincia": prov})[0], prov)
        for ciudad in ("Palermo", "Rosario", "Mar del Plata", "Córdoba", "Mendoza"):
            self.assertTrue(d.validar_parametros({"ciudad": ciudad})[0], ciudad)

    def test_fuera_de_cobertura(self):
        for parametros in ({"provincia": "Uruguay"}, {"ciudad": "Montevideo"},
                           {"ciudad": "Madrid"}, {"ciudad": "Santiago de Chile"}):
            ok, motivo = d.validar_parametros(parametros)
            self.assertFalse(ok, parametros)
            self.assertIn("Argentina", motivo)

    def test_sin_provincia_ok(self):
        self.assertTrue(d.validar_parametros({})[0])
        self.assertTrue(d.validar_parametros(None)[0])


class EntradasSeguras(unittest.TestCase):
    def test_limite(self):
        self.assertEqual(d.normalizar_limite(5), 5)
        self.assertEqual(d.normalizar_limite("7"), 7)
        self.assertEqual(d.normalizar_limite(10000), 25)
        self.assertEqual(d.normalizar_limite(-3), 1)
        self.assertEqual(d.normalizar_limite("1; DROP TABLE restaurants"), 10)
        self.assertEqual(d.normalizar_limite(None), 10)

    def test_parametros_limpios(self):
        p = d.normalizar_parametros_busqueda({
            "provincia": "  CABA ", "tipo_cocina": ["Pizza", 5, "x" * 500], "limite": "1; DROP TABLE x",
            "requiere_vegano": True, "otro": "ignorado"})
        self.assertEqual(p["provincia"], "CABA")
        self.assertEqual(p["limite"], 8)   # por defecto 8 (menos tokens por consulta)
        self.assertTrue(p["requiere_vegano"])
        self.assertNotIn("otro", p)
        self.assertEqual(len(p["tipo_cocina"]), 2)
        self.assertLessEqual(len(p["tipo_cocina"][1]), 40)

    def test_precio_maximo_acotado_de_1_a_4(self):
        for entrada, esperado in ((2, 2), ("3", 3), (0, None), (5, None), ("caro", None), (None, None)):
            p = d.normalizar_parametros_busqueda({"precio_maximo": entrada})
            self.assertEqual(p.get("precio_maximo"), esperado, repr(entrada))

    def test_mensaje(self):
        self.assertEqual(d.sanitizar_mensaje("hola\x00 mundo"), "hola mundo")
        self.assertEqual(len(d.sanitizar_mensaje("a" * 5000)), d.MAX_MENSAJE)
        self.assertEqual(d.sanitizar_mensaje(None), "")
        self.assertEqual(d.sanitizar_mensaje("   "), "")

    def test_sesion(self):
        self.assertTrue(d.sesion_valida("abc-123_X"))
        self.assertFalse(d.sesion_valida("../../etc"))
        self.assertFalse(d.sesion_valida("a" * 65))
        self.assertFalse(d.sesion_valida(None))


class ValidarRespuestaIA(unittest.TestCase):
    def test_respuesta_correcta(self):
        txt = ("Te recomiendo Restaurante Verde en Palermo. Teléfono 11 1234 5678. "
               "Más info en https://www.restauranteverde.com. La información no garantiza la "
               "ausencia de contaminación cruzada, confirmá con el local.")
        ok, prob = d.validar_respuesta_ia(txt, REALES)
        self.assertTrue(ok, prob)

    def test_garantia_absoluta(self):
        ok, prob = d.validar_respuesta_ia("Es 100% seguro para celíacos, te lo garantizo.", REALES)
        self.assertFalse(ok)
        self.assertTrue(any("garant" in p for p in prob))

    def test_telefono_inventado(self):
        ok, prob = d.validar_respuesta_ia("Llamá al 11 9999-0000 para reservar.", REALES)
        self.assertFalse(ok)
        self.assertTrue(any("teléfono" in p for p in prob))

    def test_link_inventado_y_permitido(self):
        self.assertFalse(d.validar_respuesta_ia("Mirá www.inventado.com.ar", REALES)[0])
        self.assertTrue(d.validar_respuesta_ia("Mapa: https://www.google.com/maps/search/?api=1&query=1,2", REALES)[0])

    def test_local_inventado(self):
        ok, prob = d.validar_respuesta_ia('Probá **La Cantina Fantasma** en Palermo.', REALES)
        self.assertFalse(ok)
        self.assertTrue(any("Fantasma" in p for p in prob))
        self.assertTrue(d.validar_respuesta_ia('Probá **Restaurante Verde** en Palermo.', REALES)[0])

    def test_local_inventado_entre_comillas_angulares(self):
        self.assertFalse(d.validar_respuesta_ia("Probá «La Cantina Fantasma» en Palermo.", REALES)[0])
        self.assertTrue(d.validar_respuesta_ia("Probá «Restaurante Verde» en Palermo.", REALES)[0])

    def test_no_confunde_fechas_precios_ni_coordenadas_con_telefonos(self):
        txt = ("Fuente: BA Data, actualizado 2026-03-15 (15/03/2026). Abre 10:30. Está en -34.603722, -58.381592. "
               "El menú sale $ 12.500 y $15000.")
        ok, prob = d.validar_respuesta_ia(txt, REALES)
        self.assertTrue(ok, prob)

    def test_frase_entre_comillas_comunes_no_es_un_local(self):
        self.assertTrue(d.validar_respuesta_ia('Dice "No contamos con información suficiente" sobre eso.', REALES)[0])

    def test_sin_resultados_no_puede_traer_datos(self):
        self.assertFalse(d.validar_respuesta_ia("Llamá al 11 5555-6666", [])[0])
        self.assertTrue(d.validar_respuesta_ia("No encontré opciones, probá otra zona.", [])[0])

    def test_vacia(self):
        self.assertFalse(d.validar_respuesta_ia("", REALES)[0])
        self.assertFalse(d.validar_respuesta_ia(None, REALES)[0])


class RespuestaSegura(unittest.TestCase):
    def test_sin_resultados(self):
        self.assertIn("flexibilizar", d.construir_respuesta_segura([]))

    def test_con_resultados_solo_datos_reales(self):
        t = d.construir_respuesta_segura(REALES)
        self.assertIn("Restaurante Verde", t)
        self.assertIn("11 1234-5678", t)
        self.assertIn("Fuente: Portal de Datos Abiertos CABA", t)
        self.assertIn("no garantiza", t)
        self.assertTrue(d.validar_respuesta_ia(t, REALES)[0])


class Advertencia(unittest.TestCase):
    def test_tc011_advertencia(self):
        self.assertIsNone(d.advertencia_alimentaria({}))
        self.assertIsNone(d.advertencia_alimentaria({"has_vegan_options": False}))
        self.assertIn("Información inferida. Confirmar con el local", d.advertencia_alimentaria({"has_vegan_options": True}))
        self.assertIn("no garantiza", d.advertencia_alimentaria({"has_vegan_options": True}))
        w = d.advertencia_alimentaria({"celiac_certified": True})
        self.assertIn("certificado", w)
        self.assertIn("Confirmar con el local", w)


class Limitador(unittest.TestCase):
    def test_ventana(self):
        lim = d.LimitadorTasa(3, 10)
        self.assertTrue(all(lim.permitir("ip", ahora=t) for t in (0, 1, 2)))
        self.assertFalse(lim.permitir("ip", ahora=3))
        self.assertTrue(lim.permitir("otra", ahora=3))
        self.assertTrue(lim.permitir("ip", ahora=11))


class Valoraciones(unittest.TestCase):
    def test_tc036_basico(self):
        v = d.extraer_valoraciones_basico(
            "La comida estaba rica. El servicio fue lento y la atención mala. Muy caro para lo que es.")
        por = {x["aspecto"]: x["sentimiento"] for x in v}
        self.assertEqual(por["comida"], "positivo")
        self.assertEqual(por["servicio"], "negativo")
        self.assertEqual(por["precio"], "negativo")

    def test_filtro_de_ia(self):
        ok = d.validar_valoraciones([
            {"aspecto": "comida", "sentimiento": "positivo", "detalle": "rica"},
            {"aspecto": "hackeo", "sentimiento": "positivo"},
            {"aspecto": "precio", "sentimiento": "<script>"},
            "basura",
        ])
        self.assertEqual(len(ok), 1)
        self.assertEqual(ok[0]["aspecto"], "comida")
        self.assertEqual(d.validar_valoraciones("no es lista"), [])


if __name__ == "__main__":
    unittest.main()
