"""
RENDIMIENTO Y RESISTENCIA (locales, sin red ni base de datos) - ver docs/pruebas/plan_de_pruebas.md
Miden la parte que no depende de Gemini ni de PostgreSQL: el modo sin IA, la validación de respuestas y el
limitador de mensajes. NO reemplazan una prueba de carga del sitio publicado (eso necesita una herramienta
externa y queda documentado como pendiente). Los máximos son generosos para no fallar en computadoras lentas.
    python -m unittest tests.test_rendimiento -v
"""
import os
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import diseno as d  # noqa: E402


def local(i):
    return {"restaurant_id": i, "name": "Local %d" % i, "neighborhood": "Palermo", "city": "Palermo",
            "cuisine_type": ["pizzeria"], "address": "Av. Santa Fe %d" % (1000 + i), "source_name": "OpenStreetMap",
            "features": {"has_gluten_free_options": True}}


class Rendimiento(unittest.TestCase):
    def test_tc055_el_modo_sin_ia_responde_rapido(self):
        locales = [local(i) for i in range(6)]
        buscar = lambda p: {"restaurants": locales}     # noqa: E731
        inicio = time.perf_counter()
        for _ in range(2000):
            texto, lista = d.armar_respuesta_sin_ia("pizzería sin TACC en Palermo", buscar)
        total = time.perf_counter() - inicio
        self.assertEqual(len(lista), 6)
        self.assertLess(total, 5.0, "2.000 respuestas tardaron %.2f s" % total)

    def test_tc055_validar_una_respuesta_larga_con_muchos_locales(self):
        locales = [local(i) for i in range(50)]
        texto = " ".join("Local %d en Palermo, Av. Santa Fe %d." % (i, 1000 + i) for i in range(50)) * 20
        inicio = time.perf_counter()
        d.validar_respuesta_ia(texto, locales)
        self.assertLess(time.perf_counter() - inicio, 1.0)


class Resistencia(unittest.TestCase):
    def test_tc056_limitador_con_muchos_hilos_a_la_vez_no_deja_pasar_de_mas(self):
        lim = d.LimitadorTasa(100, 3600)
        permitidos, errores = [], []

        def trabajar():
            try:
                permitidos.append(sum(lim.permitir("misma_ip") for _ in range(300)))
            except Exception as e:  # noqa: BLE001
                errores.append(e)

        hilos = [threading.Thread(target=trabajar) for _ in range(16)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        self.assertEqual(errores, [])
        self.assertEqual(sum(permitidos), 100)           # exactamente el máximo, aunque compitan 16 hilos

    def test_tc056_muchos_clientes_distintos_no_rompen_el_limitador(self):
        lim = d.LimitadorTasa(5, 60, max_claves=1000)
        for i in range(20000):
            lim.permitir("ip-%d" % i, ahora=float(i))   # cada IP aparece una vez; las viejas vencen y se limpian
        self.assertTrue(lim.permitir("ip-nueva", ahora=20000.0))


if __name__ == "__main__":
    unittest.main()
