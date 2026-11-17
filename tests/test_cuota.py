"""
Pruebas del problema "a las 4 consultas Gemini se queda sin respuestas" (cuota del plan gratis).
    python -m unittest tests.test_cuota -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import cuota  # noqa: E402


class Reloj:
    """Reloj falso: dormir() adelanta la hora sin esperar de verdad."""
    def __init__(self):
        self.t = 0.0
        self.dormidos = []

    def ahora(self):
        return self.t

    def dormir(self, s):
        self.dormidos.append(s)
        self.t += s


def control(rpm=4, max_espera=20.0):
    r = Reloj()
    return cuota.ControlCuota(rpm=rpm, max_espera=max_espera, reloj=r.ahora, dormir=r.dormir), r


class VentanaPorMinuto(unittest.TestCase):
    def test_hasta_rpm_pedidos_sin_esperar(self):
        c, r = control(rpm=4)
        for _ in range(4):
            self.assertEqual(c.reservar(), 0)
        self.assertEqual(r.dormidos, [])

    def test_tc027_el_quinto_pedido_en_el_mismo_minuto_no_se_manda(self):
        """Con 4 pedidos/min y espera máxima de 20 s, el 5.º se rechaza (se responderá sin IA)."""
        c, _ = control(rpm=4, max_espera=20)
        for _ in range(4):
            c.reservar()
        with self.assertRaises(cuota.CuotaAgotada) as cm:
            c.reservar()
        self.assertGreater(cm.exception.segundos, 20)

    def test_espera_corta_se_espera_en_vez_de_fallar(self):
        c, r = control(rpm=2, max_espera=30)
        c.reservar()
        r.t = 40.0            # pasaron 40 s: el primero vence a los 60 s
        c.reservar()
        esperado = c.reservar()   # hay que esperar ~20 s (< 30)
        self.assertAlmostEqual(esperado, 20.0, delta=0.5)
        self.assertTrue(r.dormidos)

    def test_la_ventana_se_libera_pasado_el_minuto(self):
        c, r = control(rpm=2)
        c.reservar(); c.reservar()
        r.t = 61.0
        self.assertEqual(c.reservar(), 0)


class UnaConsultaCuestaVariosPedidos(unittest.TestCase):
    """Reproduce el síntoma: cada mensaje del chat = 2 pedidos (pregunta + resultado de la búsqueda)."""

    def test_con_5_por_minuto_solo_2_consultas_usan_la_IA(self):
        c, _ = control(rpm=5, max_espera=20)
        con_ia = 0
        for _consulta in range(6):
            try:
                c.reservar(); c.reservar()          # pregunta + resultado de la herramienta
                con_ia += 1
            except cuota.CuotaAgotada:
                pass
        self.assertEqual(con_ia, 2)   # la 3.ª falla a mitad: el chat "se moría" a las 3-4 consultas


class ClasificarError429(unittest.TestCase):
    def test_por_minuto_con_espera(self):
        msg = "429 You exceeded your current quota. ... Please retry in 49.003386475s."
        self.assertEqual(cuota.clasificar_error(msg)[0], "rpm")
        self.assertAlmostEqual(cuota.clasificar_error(msg)[1], 49.0, delta=0.1)

    def test_retry_delay_en_segundos(self):
        tipo, espera = cuota.clasificar_error("ResourceExhausted 429 ... retry_delay {\n seconds: 12\n}")
        self.assertEqual((tipo, espera), ("rpm", 12.0))

    def test_limite_diario(self):
        msg = ("429 Quota exceeded for metric generate_content_free_tier_requests, "
               "GenerateRequestsPerDayPerProjectPerModel-FreeTier, limit: 20")
        self.assertEqual(cuota.clasificar_error(msg)[0], "diaria")

    def test_espera_de_horas_es_diaria(self):
        tipo, espera = cuota.clasificar_error("429 RESOURCE_EXHAUSTED Please retry in 10h17m5.72s.")
        self.assertEqual(tipo, "diaria")
        self.assertAlmostEqual(espera, 10 * 3600 + 17 * 60 + 5.72, delta=0.1)

    def test_otros_errores_no_son_de_cuota(self):
        self.assertEqual(cuota.clasificar_error("500 Internal error")[0], "otro")
        self.assertEqual(cuota.clasificar_error("")[0], "otro")


class EnviarConCuota(unittest.TestCase):
    def test_ok_directo(self):
        c, _ = control()
        self.assertEqual(cuota.enviar_con_cuota(c, lambda: "respuesta"), "respuesta")

    def test_tc025_429_por_minuto_espera_y_reintenta_una_vez(self):
        c, r = control(rpm=10, max_espera=20)
        llamadas = []

        def enviar():
            llamadas.append(1)
            if len(llamadas) == 1:
                raise RuntimeError("429 Resource exhausted. Please retry in 7s.")
            return "ok"
        self.assertEqual(cuota.enviar_con_cuota(c, enviar), "ok")
        self.assertEqual(len(llamadas), 2)
        self.assertTrue(any(s >= 7 for s in r.dormidos))

    def test_429_persistente_lanza_cuota_agotada(self):
        c, _ = control(rpm=10, max_espera=20)

        def enviar():
            raise RuntimeError("429 Resource exhausted. Please retry in 5s.")
        with self.assertRaises(cuota.CuotaAgotada):
            cuota.enviar_con_cuota(c, enviar)

    def test_tc026_429_diario_no_espera(self):
        c, r = control()

        def enviar():
            raise RuntimeError("429 GenerateRequestsPerDayPerProjectPerModel-FreeTier exceeded")
        with self.assertRaises(cuota.CuotaAgotada) as cm:
            cuota.enviar_con_cuota(c, enviar)
        self.assertTrue(cm.exception.diaria)
        self.assertEqual(r.dormidos, [])
        with self.assertRaises(cuota.CuotaAgotada):       # y los siguientes pedidos ni se intentan
            cuota.enviar_con_cuota(c, lambda: "no debería llamarse")

    def test_error_que_no_es_de_cuota_se_propaga(self):
        c, _ = control()

        def enviar():
            raise ValueError("falla distinta")
        with self.assertRaises(ValueError):
            cuota.enviar_con_cuota(c, enviar)


if __name__ == "__main__":
    unittest.main()
