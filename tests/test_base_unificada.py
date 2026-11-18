"""
Base unificada (≈96.000 lugares; se carga todo el país): conversión del Excel, CSV resultante y cargador en bloques.
No necesitan pandas, Excel ni PostgreSQL: prueban las funciones de mapeo y el CSV ya generado.
    python -m unittest tests.test_base_unificada -v
"""
import csv
import os
import sys
import unittest
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "backend"))
import convertir_base_unificada as cv  # noqa: E402
import cargar_base_unificada as cg  # noqa: E402

CSV_UNIFICADO = RAIZ / "data" / "dataset_unificado_CABA_GBA.csv"
CSV_NACIONAL = RAIZ / "data" / "dataset_unificado_ARGENTINA.csv"


def fila(**kw):
    base = {"ID": "U1", "Nombre": "Local de prueba", "Región": "CABA", "Localidad / barrio": "Palermo", "Dirección": "Av. Santa Fe 1000",
            "Latitud": "-34.58", "Longitud": "-58.42", "Estado de la coordenada": "correcta (Overture)", "Tipo de lugar": "Pizzería",
            "Cocina": None, "Sin TACC": "sin datos", "Vegano": "sin datos", "Vegetariano": "sin datos", "Sin lactosa / lácteos": "sin datos",
            "Teléfono": "+54 11 5555-5555", "Sitio web / Instagram": "https://ejemplo.com.ar", "Fuente(s)": "Overture Maps (release 2026-10-21.0)",
            "Detalle de la evidencia": None, "Fecha de consulta": "2026-11-14"}
    base.update(kw)
    return base


class Mapeo(unittest.TestCase):
    def test_tc066_cocinas_se_traducen_al_vocabulario_del_sistema(self):
        self.assertEqual(cv.tokens_cocina("Pizzería", None), ["pizzeria", "pizza"])
        self.assertEqual(cv.tokens_cocina("Sushi", None), ["japonesa", "sushi"])
        self.assertEqual(cv.tokens_cocina("", "MINUTAS"), ["minutas"])
        self.assertEqual(cv.tokens_cocina("", "no especificado"), [])
        self.assertIn("hamburguesa", cv.tokens_cocina("Bar", "burger"))
        self.assertEqual(cv.tokens_cocina("Pizzería", "pizza"), ["pizzeria", "pizza"])      # sin repetidos

    def test_tc066_sin_datos_no_es_lo_mismo_que_no(self):
        self.assertEqual(cv.restriccion("sin datos"), (None, False))
        self.assertEqual(cv.restriccion("no"), (False, False))
        for v in ("sí", "solo", "con opciones"):
            self.assertEqual(cv.restriccion(v), (True, False), v)
        self.assertEqual(cv.restriccion("con opciones (inferido)"), (True, True))

    def test_tc066_zona_provincia_ciudad_y_barrio(self):
        self.assertEqual(cv.zona("CABA", "Palermo", None, None, "CABA"), ("CABA", "Palermo", "Palermo"))
        self.assertEqual(cv.zona("GBA", "Olivos", "Vicente López", None, "GBA Norte"), ("Buenos Aires", "Olivos (Vicente López)", "Olivos"))
        self.assertEqual(cv.zona("GBA", "Tigre", "Tigre", None, "GBA Norte"), ("Buenos Aires", "Tigre", "Tigre"))
        self.assertEqual(cv.zona("CABA/GBA (confirmar)", None, None, None, "Sin confirmar"), ("Buenos Aires", "Sin confirmar", ""))

    def test_tc066_coordenadas_invalidas_se_descartan(self):
        self.assertEqual(cv.coordenadas("-34.5", "-58.4", "correcta"), ("-34.500000", "-58.400000"))
        self.assertEqual(cv.coordenadas("-350", "-580", "inválida (valor de relleno -350/-580: geocodificar por dirección)"), ("", ""))
        self.assertEqual(cv.coordenadas("-34.5", "-58.4", "imprecisa (error de 1 km o más)"), ("", ""))
        self.assertEqual(cv.coordenadas("40.4", "-3.7", "correcta"), ("", ""))          # fuera de Argentina
        self.assertEqual(cv.coordenadas(None, None, "sin coordenada"), ("", ""))

    def test_tc066_se_descarta_todo_lo_que_no_es_de_argentina(self):
        self.assertEqual(cv.motivo_fuera_de_argentina(fila(**{"Provincia": "Uruguay"})), "provincia fuera de Argentina")
        self.assertEqual(cv.motivo_fuera_de_argentina(fila(**{"Provincia": "Madrid"})), "provincia fuera de Argentina")
        self.assertEqual(cv.motivo_fuera_de_argentina(fila(**{"Latitud": "40.4", "Longitud": "-3.7"})),
                         "coordenadas fuera de Argentina")
        self.assertIsNone(cv.motivo_fuera_de_argentina(fila(**{"Provincia": "Buenos Aires / CABA (confirmar)"})))
        self.assertIsNone(cv.motivo_fuera_de_argentina(fila(**{"Provincia": "Tierra del Fuego"})))
        # Una dirección con nombre extranjero no alcanza para descartar: «Montevideo 1480» es una calle de CABA.
        self.assertIsNone(cv.motivo_fuera_de_argentina(fila(**{"Dirección": "Montevideo 1480"})))
        self.assertIsNone(cv.fila_a_registro(fila(**{"Provincia": "Uruguay"})))
        self.assertIsNone(cv.fila_a_registro(fila(**{"Latitud": "40.4", "Longitud": "-3.7"})))

    def test_tc066_fila_normal_se_convierte(self):
        r = cv.fila_a_registro(fila())
        self.assertEqual((r["provincia"], r["ciudad"], r["fuente"], r["categoria"]), ("CABA", "Palermo", "overture", "restaurant"))
        self.assertEqual((r["sin_tacc"], r["dato_inferido"], r["telefono"]), ("", "f", "+54 11 5555-5555"))

    def test_tc066_de_google_no_se_guardan_telefono_ni_web_y_la_restriccion_se_conserva(self):
        r = cv.fila_a_registro(fila(**{"Fuente(s)": "Google Places (05/10/2026)", "Sin TACC": "solo"}))
        self.assertEqual((r["telefono"], r["website"], r["sin_tacc"], r["fuente"]), ("", "", "t", "google_places"))
        self.assertIsNone(cv.fila_a_registro(fila(**{"Fuente(s)": "Google Places (05/10/2026)"}), sin_google=True))

    def test_tc066_confianza_baja_se_excluye_salvo_que_tenga_dato_de_restriccion(self):
        baja = {"Detalle de la evidencia": "Overture (baja)"}
        self.assertIsNone(cv.fila_a_registro(fila(**baja)))
        self.assertIsNotNone(cv.fila_a_registro(fila(**baja), incluir_baja=True))
        self.assertIsNotNone(cv.fila_a_registro(fila(**baja, **{"Vegano": "con opciones (inferido)"})))

    def test_tc066_lo_inferido_queda_marcado(self):
        self.assertEqual(cv.fila_a_registro(fila(**{"Sin TACC": "con opciones (inferido)"}))["dato_inferido"], "t")
        self.assertEqual(cv.fila_a_registro(fila(**{"Sin TACC": "sí"}))["dato_inferido"], "f")

    def test_zonas_reconocibles_no_incluye_genericas_ni_pocas(self):
        regs = [{"barrio": "Palermo", "ciudad": "Palermo"}] * 3 + [{"barrio": "Olivos", "ciudad": "Olivos (Vicente López)"}] * 3 \
               + [{"barrio": "Centro", "ciudad": "Centro"}] * 5 + [{"barrio": "Rara", "ciudad": "Rara"}]
        z = cv.zonas_reconocibles(regs)
        self.assertEqual(set(z), {"Palermo", "Olivos", "Vicente López"})


class CsvGenerado(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(CSV_UNIFICADO, encoding="utf-8", newline="") as f:
            cls.filas = list(csv.DictReader(f))

    def test_tc067_estructura_y_tamano(self):
        self.assertEqual(list(self.filas[0].keys()), cv.CAMPOS)
        self.assertGreater(len(self.filas), 20000)

    def test_tc067_ids_unicos_y_nombres_completos(self):
        ids = [r["id_origen"] for r in self.filas]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual([r["id_origen"] for r in self.filas if not r["nombre"].strip()], [])

    def test_tc067_solo_caba_y_gba_con_valores_validos(self):
        self.assertEqual({r["provincia"] for r in self.filas}, {"CABA", "Buenos Aires"})
        for campo in ("sin_tacc", "vegetariano", "vegano", "sin_lactosa"):
            self.assertLessEqual({r[campo] for r in self.filas}, {"t", "f", ""}, campo)
        self.assertLessEqual({r["fuente"] for r in self.filas}, set(cg.FUENTES))

    def test_tc067_coordenadas_dentro_de_argentina(self):
        for r in self.filas:
            if r["latitud"]:
                self.assertTrue(-55.5 <= float(r["latitud"]) <= -21 and -74 <= float(r["longitud"]) <= -53, r["id_origen"])

    def test_tc067_de_google_no_hay_telefono_ni_web_ni_calificaciones(self):
        google = [r for r in self.filas if r["fuente"] == "google_places"]
        self.assertTrue(google)
        self.assertEqual([r["id_origen"] for r in google if r["telefono"] or r["website"]], [])
        self.assertNotIn("calificacion", self.filas[0])

    def test_tc067_la_restriccion_sin_datos_queda_vacia_no_falsa(self):
        con_dato = sum(1 for r in self.filas if r["sin_tacc"] == "t")
        sin_dato = sum(1 for r in self.filas if r["sin_tacc"] == "")
        self.assertGreater(con_dato, 50)
        self.assertGreater(sin_dato, len(self.filas) * 0.9)          # la gran mayoría no tiene dato: y NO se marca como «no»

    def test_las_zonas_generadas_incluyen_barrios_y_partidos(self):
        import zonas_dataset
        for zona in ("Palermo", "Tigre", "Quilmes", "Lanús", "Vicente López"):
            self.assertIn(zona, zonas_dataset.ZONAS)
        self.assertNotIn("CABA", zonas_dataset.ZONAS)


class CsvNacional(unittest.TestCase):
    """El CSV que se carga en la base solo contiene las 24 jurisdicciones argentinas."""

    @classmethod
    def setUpClass(cls):
        with open(CSV_NACIONAL, encoding="utf-8", newline="") as f:
            cls.filas = list(csv.DictReader(f))

    def test_tc067_todo_el_pais_y_solo_argentina(self):
        from geografia import PROVINCIAS, normalizar_provincia
        self.assertGreater(len(self.filas), 70000)
        provincias = {normalizar_provincia(r["provincia"]) for r in self.filas}
        self.assertEqual(provincias, set(PROVINCIAS))
        for r in self.filas:
            self.assertTrue(normalizar_provincia(r["provincia"]), r["id_origen"])
            if r["latitud"]:
                self.assertTrue(-55.5 <= float(r["latitud"]) <= -21 and -74 <= float(r["longitud"]) <= -53,
                                r["id_origen"])


class Cargador(unittest.TestCase):
    R = {"nombre": "X", "provincia": "CABA", "ciudad": "Palermo", "barrio": "Palermo", "direccion": "Calle 1", "latitud": "-34.5",
         "longitud": "-58.4", "cocina": "pizzeria;pizza", "categoria": "restaurant", "telefono": "", "website": "", "sin_tacc": "t",
         "vegetariano": "", "vegano": "f", "sin_lactosa": "", "dato_inferido": "t", "fuente": "overture", "fecha_dato": "2026-11-14",
         "region": "GBA", "partido": "Lomas de Zamora", "zona": "GBA Sur"}

    def test_tc068_valores_de_restaurants(self):
        v = cg.valores_restaurante(self.R, 7, date(2026, 11, 14))
        self.assertEqual(len(v), 19)                                  # una por columna del INSERT
        self.assertEqual((v[0], v[1], v[5], v[7], v[11], v[13]), ("X", "CABA", -34.5, ["pizzeria", "pizza"], 7, "no_verified"))
        self.assertIsNone(v[9])                                       # teléfono vacío -> NULL
        self.assertEqual(v[16:], ("GBA", "Lomas de Zamora", "GBA Sur"))   # jerarquía región > partido > zona

    def test_jerarquia_region_partido_zona(self):
        self.assertEqual(cv.jerarquia("CABA", "", "CABA"), ("CABA", "", "CABA"))
        self.assertEqual(cv.jerarquia("GBA", "Tigre", "GBA Norte"), ("GBA", "Tigre", "GBA Norte"))
        self.assertEqual(cv.jerarquia("GBA", "", ""), ("GBA", "", "GBA (sin partido)"))
        self.assertEqual(cv.jerarquia("CABA/GBA (confirmar)", "", "Sin confirmar"), ("Sin confirmar", "", "Sin confirmar"))

    def test_tc068_valores_de_features_distinguen_si_no_y_sin_datos(self):
        v = cg.valores_features(99, self.R, 7)
        self.assertEqual(len(v), 8)
        self.assertEqual(v[:5], (99, True, None, False, None))        # sí, sin datos (NULL), no, sin datos (NULL)
        self.assertEqual((v[5], v[7]), (False, "inferred"))           # nunca «certificado»; lo inferido se marca

    def test_tc068_el_cargador_no_pisa_comercios_ni_carga_a_ciegas(self):
        fuente = (RAIZ / "scripts" / "cargar_base_unificada.py").read_text(encoding="utf-8")
        self.assertIn("--forzar", fuente)
        self.assertIn("source_type IS DISTINCT FROM 'registro_comercio'", fuente)
        self.assertIn("execute_values", fuente)                       # en bloques, no un INSERT por fila

    def test_cargador_filtra_filas_no_argentinas(self):
        self.assertTrue(cg.fila_argentina(self.R))
        self.assertFalse(cg.fila_argentina({**self.R, "provincia": "Uruguay"}))
        self.assertFalse(cg.fila_argentina({**self.R, "latitud": "40.4", "longitud": "-3.7"}))
        self.assertFalse(cg.fila_argentina({**self.R, "latitud": "-34.5", "longitud": ""}))
        self.assertTrue(cg.fila_argentina({**self.R, "latitud": "", "longitud": ""}))

    def test_cargar_base_nube_usa_la_base_unificada_si_existe(self):
        fuente = (RAIZ / "scripts" / "cargar_base_nube.py").read_text(encoding="utf-8")
        self.assertIn("dataset_unificado_CABA_GBA.csv", fuente)
        self.assertIn("cargar_base_unificada", fuente)


if __name__ == "__main__":
    unittest.main()
