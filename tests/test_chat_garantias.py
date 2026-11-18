"""
Preguntas por garantías absolutas (HU-02): el chat responde con un texto fijo y no llama a Gemini.
    python -m unittest tests.test_chat_garantias -v
No usan Gemini ni PostgreSQL.
"""
import os
import sys
import unittest
from unittest import mock

# chat_service importa database.py, que exige la variable (no se conecta en esta prueba).
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:x@localhost:5432/gastro_ia")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import chat_service as ch  # noqa: E402
import diseno as d  # noqa: E402


class Deteccion(unittest.TestCase):
    def test_preguntas_por_garantia(self):
        for texto in (
            "¿Es 100% seguro para celíacos?",
            "¿Este local es 100 % seguro?",
            "¿Me garantizás que no tiene TACC?",
            "Necesito una garantía de que no hay contaminación cruzada.",
            "¿Es totalmente seguro para una persona celíaca?",
            "¿Está garantizado que es sin gluten?",
            "¿Es seguro para celíacos?",
            "¿Quedo completamente seguro si como ahí?",
        ):
            self.assertTrue(d.es_pregunta_garantia(texto), texto)

    def test_consultas_normales_no_se_confunden(self):
        for texto in (
            "¿Qué opciones sin TACC hay en Palermo?",
            "Busco una pizzería vegana en Córdoba",
            "¿Es seguro caminar de noche por la zona?",
            "Mostrame lugares con menú sin gluten",
            "¿Tienen opciones aptas para celíacos?",
            "",
            None,
        ):
            self.assertFalse(d.es_pregunta_garantia(texto), texto)


class RespuestaFija(unittest.TestCase):
    def setUp(self):
        self.servicio = ch.ChatService(db=None, gemini_api_key="")
        self.servicio._enviar = mock.Mock(side_effect=AssertionError("no debe llamar a Gemini"))
        self.servicio._sin_ia = mock.Mock(side_effect=AssertionError("no debe buscar en la base"))
        self.servicio._guardar_turno = mock.Mock()

    def test_responde_sin_gemini(self):
        for texto in ("¿Es 100 % seguro?", "¿Me lo garantizás?", "¿Es totalmente seguro para celíacos?"):
            self.assertEqual(self.servicio.send_message(texto, "prueba-garantia"), d.RESPUESTA_GARANTIA)
        self.servicio._enviar.assert_not_called()
        self.servicio._sin_ia.assert_not_called()
        self.assertEqual(self.servicio._guardar_turno.call_count, 3)
        self.assertEqual(self.servicio.last_restaurants, [])

    def test_el_texto_es_la_advertencia_de_hu02(self):
        self.assertTrue(d.RESPUESTA_GARANTIA.startswith("No puedo asegurar"))
        self.assertIn("contaminación cruzada", d.RESPUESTA_GARANTIA)
        self.assertIn("Contactá directamente al local", d.RESPUESTA_GARANTIA)

    def test_la_respuesta_fija_pasa_la_validacion_del_backend(self):
        # El validador genérico marca «100 % seguro», pero este texto es una negación.
        self.assertEqual(d.validar_respuesta_ia(d.RESPUESTA_GARANTIA, []), (True, []))

    def test_una_garantia_de_la_ia_sigue_bloqueada(self):
        ok, problemas = d.validar_respuesta_ia("Es 100% seguro para celíacos.", [])
        self.assertFalse(ok)
        self.assertTrue(any("garantía" in p for p in problemas))


if __name__ == "__main__":
    unittest.main()
