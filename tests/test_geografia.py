"""Pruebas de la geografía argentina común (backend/geografia.py) y de la validación offline.

No usan internet ni base de datos:
    python -m unittest tests.test_geografia -v
"""
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))
sys.path.insert(0, str(RAIZ / "scripts"))

import geografia as g  # noqa: E402
import validar_base_argentina as v  # noqa: E402


class Provincias(unittest.TestCase):
    def test_hay_23_provincias_y_caba(self):
        self.assertEqual(len(g.PROVINCIAS), 24)
        self.assertIn("CABA", g.PROVINCIAS)
        self.assertIn("Tierra del Fuego", g.PROVINCIAS)
        self.assertNotIn("Uruguay", g.PROVINCIAS)

    def test_alias_argentinos(self):
        casos = {
            "CABA": "CABA", "Capital Federal": "CABA", "Ciudad Autónoma de Buenos Aires": "CABA",
            "Provincia de Buenos Aires": "Buenos Aires", "GBA": "Buenos Aires",
            "Gran Buenos Aires": "Buenos Aires", "Córdoba": "Córdoba", "cordoba": "Córdoba",
            "Tierra del Fuego, Antártida e Islas del Atlántico Sur": "Tierra del Fuego",
            "Buenos Aires / CABA (confirmar)": "Buenos Aires",
            "Córdoba, Argentina": "Córdoba", "Provincia de Córdoba": "Córdoba",
            "Mendoza, Argentina": "Mendoza",
        }
        for entrada, esperado in casos.items():
            self.assertEqual(g.normalizar_provincia(entrada), esperado, entrada)
            self.assertTrue(g.es_provincia_argentina(entrada), entrada)

    def test_provincias_extranjeras_o_inventadas(self):
        for valor in ("Uruguay", "Chile", "Brasil", "Madrid", "Texas", "Sin confirmar", "", None):
            self.assertIsNone(g.normalizar_provincia(valor), valor)
            self.assertFalse(g.es_provincia_argentina(valor), valor)


class LugaresFuera(unittest.TestCase):
    def test_paises_y_ciudades_extranjeras(self):
        for valor in ("Montevideo", "MONTEVIDEO", "Madrid", "Miami", "Santiago de Chile",
                      "Montevideo, Uruguay", "Santiago, Chile", "Uruguay", "España"):
            self.assertTrue(g.es_lugar_extranjero(valor), valor)

    def test_localidades_argentinas_con_nombres_parecidos(self):
        # No se rechazan: son localidades argentinas reales.
        for valor in ("Concepción del Uruguay", "La Paz", "Lima", "Asunción", "Tandil",
                      "San Justo", "San Juan", "Córdoba", "Rosario", "Mar del Plata"):
            self.assertFalse(g.es_lugar_extranjero(valor), valor)

    def test_mencionar_no_es_ser(self):
        # «Concepción del Uruguay» menciona Uruguay, pero no es un lugar de Uruguay.
        self.assertTrue(g.menciona_lugar_extranjero("Concepción del Uruguay"))
        self.assertFalse(g.es_lugar_extranjero("Concepción del Uruguay"))
        self.assertTrue(g.menciona_lugar_extranjero("Av. Montevideo 1480"))


class Coordenadas(unittest.TestCase):
    def test_dentro_de_argentina(self):
        for lat, lon in ((-34.60, -58.38), (-54.80, -68.30), (-22.10, -65.60), (-34.5, -58.4)):
            self.assertTrue(g.coordenadas_en_argentina(lat, lon), (lat, lon))

    def test_fuera_o_invalidas(self):
        # El recuadro es generoso a propósito: no sustituye la validación de provincia.
        # Santiago de Chile cae dentro del rectángulo, pero su provincia no es argentina.
        for lat, lon in ((40.4, -3.7), (19.43, -99.13), (-55.6, -58.4),
                         (-34.5, -74.1), ("x", -58.4), (None, None)):
            self.assertFalse(g.coordenadas_en_argentina(lat, lon), (lat, lon))

    def test_limite_conocido_del_recuadro(self):
        self.assertTrue(g.coordenadas_en_argentina(-33.45, -70.66))   # Santiago: lo rechaza la provincia, no el recuadro
        self.assertFalse(g.es_provincia_argentina("Región Metropolitana"))


class ValidacionOffline(unittest.TestCase):
    def _fila(self, **kw):
        base = {"id_origen": "U1", "nombre": "Local", "provincia": "Córdoba", "ciudad": "Córdoba",
                "region": "Interior", "latitud": "-31.42", "longitud": "-64.18"}
        base.update(kw)
        return base

    def test_csv_sin_problemas(self):
        inf = v.analizar_csv([self._fila(), self._fila(id_origen="U2", provincia="CABA", region="CABA")])
        self.assertEqual(inf["total"], 2)
        self.assertEqual(inf["provincias_invalidas"], [])
        self.assertEqual(inf["coords_fuera"], [])
        self.assertEqual(inf["coords_incompletas"], [])

    def test_csv_detecta_provincia_extranjera_y_coordenadas(self):
        filas = [
            self._fila(id_origen="U1", provincia="Uruguay", region="Interior"),
            self._fila(id_origen="U2", latitud="40.4", longitud="-3.7"),
            self._fila(id_origen="U3", latitud="-31.4", longitud=""),
        ]
        inf = v.analizar_csv(filas)
        self.assertEqual([r["id_origen"] for r in inf["provincias_invalidas"]], ["U1"])
        self.assertEqual([r["id_origen"] for r in inf["coords_fuera"]], ["U2"])
        self.assertEqual([r["id_origen"] for r in inf["coords_incompletas"]], ["U3"])
        self.assertEqual(sorted(v.filas_invalidas_csv(filas)), [0, 1])

    def test_limpiar_csv_descarta_solo_lo_no_argentino(self):
        filas = [self._fila(id_origen="U1"), self._fila(id_origen="U2", provincia="Chile"),
                 self._fila(id_origen="U3", latitud="40.4", longitud="-3.7")]
        limpias, quitadas = v.limpiar_csv(filas)
        self.assertEqual(quitadas, 2)
        self.assertEqual([r["id_origen"] for r in limpias], ["U1"])


if __name__ == "__main__":
    unittest.main()
