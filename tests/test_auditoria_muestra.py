"""Pruebas de la auditoría por muestreo (scripts/auditar_muestra.py), sin Excel ni internet.

    python -m unittest tests.test_auditoria_muestra -v
"""
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

import auditar_muestra as a  # noqa: E402


def r(**kw):
    base = {"id_origen": "U1", "nombre": "Local", "provincia": "Córdoba", "ciudad": "Córdoba",
            "barrio": "Centro", "direccion": "San Martín 100", "latitud": "-31.42", "longitud": "-64.18",
            "region": "Interior", "fuente": "overture"}
    base.update(kw)
    return base


class Muestra(unittest.TestCase):
    def test_tamano_fijo_y_reproducible(self):
        filas = [r(id_origen="U%d" % i, fuente="overture") for i in range(500)]
        filas += [r(id_origen="K%d" % i, fuente="guia_kosher") for i in range(8)]
        filas += [r(id_origen="C1", fuente="guia_celiacos")]
        m1, asig1 = a.muestra_estratificada(filas, 100, semilla=7)
        m2, asig2 = a.muestra_estratificada(filas, 100, semilla=7)
        self.assertEqual(len(m1), 100)
        self.assertEqual(asig1, asig2)
        self.assertEqual([x["id_origen"] for x in m1], [x["id_origen"] for x in m2])
        self.assertEqual(asig1["guia_celiacos"], 1)          # la fuente con un solo caso no queda afuera

    def test_estratos_no_se_pasan_del_tamano(self):
        filas = [r(id_origen="K%d" % i, fuente="guia_kosher") for i in range(3)]
        muestra, asig = a.muestra_estratificada(filas, 50, minimo=5)
        self.assertEqual(len(muestra), 3)
        self.assertEqual(asig["guia_kosher"], 3)


class Comparaciones(unittest.TestCase):
    def test_coordenadas_guardadas_como_enteros(self):
        self.assertAlmostEqual(a._coord_escalada("-345805799", -55.5, -21.0), -34.5805799)
        self.assertAlmostEqual(a._coord_escalada("-34529084", -55.5, -21.0), -34.529084)
        self.assertAlmostEqual(a._coord_escalada("-584811731", -74.0, -53.0), -58.4811731)
        self.assertAlmostEqual(a._coord_escalada("-34.58", -55.5, -21.0), -34.58)
        self.assertIsNone(a._coord_escalada("40.4", -55.5, -21.0))

    def test_clave_de_duplicado_estricta(self):
        base = a.clave_duplicado(r())
        self.assertEqual(base, a.clave_duplicado(r()))
        self.assertNotEqual(base, a.clave_duplicado(r(direccion="San Martín 200")))
        self.assertNotEqual(base, a.clave_duplicado(r(provincia="Santa Fe")))
        # Sin dirección se usan las coordenadas: dos sucursales no son duplicados.
        self.assertNotEqual(a.clave_duplicado(r(direccion="", latitud="-31.42", longitud="-64.18")),
                            a.clave_duplicado(r(direccion="", latitud="-31.43", longitud="-64.18")))

    def test_provincia_dudosa(self):
        self.assertEqual(a.provincia_dudosa(r(), {"Provincia": "Córdoba", "Fuente(s)": "Overture"}), [])
        motivos = a.provincia_dudosa(r(region="Sin confirmar", ciudad="Sin confirmar"),
                                     {"Provincia": "Buenos Aires / CABA (confirmar)", "Fuente(s)": "OpenStreetMap"})
        self.assertIn("región Sin confirmar", motivos)
        self.assertIn("ciudad Sin confirmar", motivos)
        self.assertIn("provincia a confirmar en el Excel", motivos)
        self.assertIn("provincia distinta al Excel",
                      a.provincia_dudosa(r(), {"Provincia": "Santa Fe", "Fuente(s)": "Overture"}))

    def test_match_crudo_acepta_ba_data_sin_coordenadas(self):
        e = {"ID de origen (OSM / BA Data)": "1010"}
        crudo = {"1010": ("LA CAMPIÑA", None, None)}
        self.assertTrue(a.match_fuente_cruda(r(nombre="LA CAMPIÑA", fuente="ba_data"), e, {}, crudo))

    def test_match_crudo_por_id_nombre_y_coordenadas(self):
        e = {"ID de origen (OSM / BA Data)": "abc"}
        crudo = {"abc": ("Local", -31.42, -64.18)}
        self.assertTrue(a.match_fuente_cruda(r(), e, crudo, {}))
        self.assertFalse(a.match_fuente_cruda(r(nombre="Otro"), e, crudo, {}))
        self.assertFalse(a.match_fuente_cruda(r(), e, {"abc": ("Local", -31.0, -64.0)}, {}))


if __name__ == "__main__":
    unittest.main()
