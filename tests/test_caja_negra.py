"""
PRUEBAS DE CAJA NEGRA: particiones de equivalencia y valores límite - ver docs/pruebas/caja_negra.md
Los resultados esperados salen del REQUISITO (límites de mensaje, de resultados, cobertura de toda la Argentina, 20
mensajes por minuto), no de leer el código.
    python -m unittest tests.test_caja_negra -v
No usan Gemini ni PostgreSQL.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import diseno as d  # noqa: E402


class LongitudDelMensaje(unittest.TestCase):
    """Requisito: el mensaje tiene entre 1 y 1.500 caracteres; lo demás se descarta o se recorta."""

    def test_tc052_particiones_invalidas_y_vacias(self):
        for entrada in (None, 123, [], "", "   ", "\t\n"):
            self.assertEqual(d.sanitizar_mensaje(entrada), "", repr(entrada))

    def test_tc052_valores_limite(self):
        casos = ((1, 1), (2, 2), (1499, 1499), (1500, 1500), (1501, 1500), (5000, 1500))
        for largo, esperado in casos:
            self.assertEqual(len(d.sanitizar_mensaje("a" * largo)), esperado, "largo %d" % largo)

    def test_tc052_quita_caracteres_de_control(self):
        self.assertEqual(d.sanitizar_mensaje("ho\x00la\x07"), "hola")


class CantidadDeResultados(unittest.TestCase):
    """Requisito: se piden entre 1 y 25 resultados; si el dato no sirve, se usa el valor por defecto (10)."""

    def test_tc052_valores_limite_y_particiones(self):
        casos = ((-5, 1), (0, 1), (1, 1), (2, 2), (10, 10), (24, 24), (25, 25), (26, 25), (1000, 25),
                 ("7", 7), (7.9, 7), ("abc", 10), (None, 10), ("1; DROP TABLE restaurants", 10))
        for entrada, esperado in casos:
            self.assertEqual(d.normalizar_limite(entrada), esperado, repr(entrada))


class CoberturaGeografica(unittest.TestCase):
    """Requisito (HU-03): toda la Argentina. Particiones: zonas cubiertas, zonas fuera del país y nombres parecidos."""

    def test_tc051_zonas_cubiertas(self):
        for parametros in ({"ciudad": "Palermo"}, {"ciudad": "Lanús Oeste"}, {"provincia": "CABA"},
                           {"provincia": "Buenos Aires"}, {"provincia": "Gran Buenos Aires"},
                           {"provincia": "Córdoba"}, {"ciudad": "Rosario"}, {"ciudad": "Mar del Plata"},
                           {"provincia": "Santa Fe"}, {"provincia": "Mendoza"}, {"ciudad": "San Juan"},
                           {}, None):
            self.assertTrue(d.validar_parametros(parametros)[0], parametros)

    def test_tc051_zonas_fuera_de_cobertura(self):
        for parametros in ({"ciudad": "Montevideo"}, {"ciudad": "Madrid"}, {"ciudad": "Miami"},
                           {"ciudad": "Santiago de Chile"}, {"provincia": "Uruguay"}, {"provincia": "Chile"}):
            ok, motivo = d.validar_parametros(parametros)
            self.assertFalse(ok, parametros)
            self.assertIn("Argentina", motivo)

    def test_tc051_valores_limite_entre_nombres_parecidos(self):
        self.assertTrue(d.validar_parametros({"ciudad": "San Justo"})[0])             # partido de GBA
        self.assertTrue(d.validar_parametros({"ciudad": "San Juan"})[0])              # provincia de Cuyo
        self.assertTrue(d.validar_parametros({"ciudad": "Concepción del Uruguay"})[0])  # ciudad de Entre Ríos
        self.assertFalse(d.validar_parametros({"provincia": "Uruguay"})[0])           # país vecino
        self.assertFalse(d.validar_parametros({"ciudad": "Uruguay"})[0])

    def test_tc051_no_importan_mayusculas_ni_tildes(self):
        self.assertFalse(d.validar_parametros({"ciudad": "MONTEVIDEO"})[0])
        self.assertFalse(d.validar_parametros({"provincia": "URUGUAY"})[0])
        self.assertTrue(d.validar_parametros({"provincia": "cordoba"})[0])
        self.assertTrue(d.validar_parametros({"ciudad": "CÓRDOBA"})[0])

    def test_tc051_limite_conocido_ciudad_desconocida_se_acepta(self):
        # Límite de diseño: se rechaza una lista de ciudades conocidas de otras provincias, no se exige una lista
        # blanca. Una ciudad que no figura (p. ej. Tandil) pasa y la base devuelve cero resultados.
        self.assertTrue(d.validar_parametros({"ciudad": "Tandil"})[0])


class LimiteDeMensajesPorMinuto(unittest.TestCase):
    """Requisito (SEG-06): 20 mensajes por minuto por cliente; el 21.º se rechaza y la ventana se desliza."""

    def test_tc053_valores_limite(self):
        lim = d.LimitadorTasa(20, 60)
        self.assertEqual([lim.permitir("ip", 0) for _ in range(20)], [True] * 20)   # 1.º a 20.º: permitidos
        self.assertFalse(lim.permitir("ip", 0))                                        # 21.º: rechazado
        self.assertFalse(lim.permitir("ip", 60))                                       # justo en el borde de la ventana
        self.assertTrue(lim.permitir("ip", 60.001))                                    # recién afuera: permitido

    def test_tc053_clientes_distintos_no_se_afectan(self):
        lim = d.LimitadorTasa(1, 60)
        self.assertTrue(lim.permitir("a", 0))
        self.assertFalse(lim.permitir("a", 1))
        self.assertTrue(lim.permitir("b", 1))


if __name__ == "__main__":
    unittest.main()
