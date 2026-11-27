"""
Modo sin IA conversacional: qué tan natural responde Foody cuando Gemini no tiene cuota,
sin dejar de ser seguro (solo datos de la base, nunca se afloja una restricción alimentaria).
    python -m unittest tests.test_modo_sin_ia -v
No usan Gemini ni PostgreSQL.
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import diseno as d  # noqa: E402


def local(nombre, barrio="Palermo", cocina="pizzeria", **feats):
    return {"restaurant_id": abs(hash(nombre)) % 10000, "name": nombre, "neighborhood": barrio, "city": barrio,
            "cuisine_type": [cocina], "address": "Av. Santa Fe 4789", "phone": "11 4567-8901",
            "website": "https://www.ejemplo.com.ar", "source_name": "OpenStreetMap", "features": feats}


class Buscador:
    """Base falsa: `regla(params)` decide qué locales devuelve. Guarda las llamadas."""
    def __init__(self, regla):
        self.regla, self.llamadas = regla, []

    def __call__(self, params):
        self.llamadas.append(dict(params))
        return {"total": 0, "restaurants": self.regla(params)}


def siempre(locales):
    return Buscador(lambda p: locales)


class Charla(unittest.TestCase):
    def test_saludo_responde_sin_consultar_la_base(self):
        for saludo in ("hola", "Hola Foody!", "buenas tardes", "¿qué tal?"):
            b = siempre([local("X")])
            texto, lista = d.armar_respuesta_sin_ia(saludo, b)
            self.assertIn("Foody", texto, saludo)
            self.assertIn("filtros", texto, saludo)
            self.assertEqual((lista, b.llamadas), ([], []), saludo)

    def test_gracias_ayuda_y_chau(self):
        b = siempre([local("X")])
        gracias = d.armar_respuesta_sin_ia("muchas gracias!", b)[0]
        self.assertTrue(any(x in gracias for x in ("De nada", "Un gusto", "Gracias a vos")), gracias)
        self.assertIn("pizzería sin TACC en Palermo", d.armar_respuesta_sin_ia("qué podés hacer?", b)[0])
        chau = d.armar_respuesta_sin_ia("chau", b)[0]
        self.assertTrue(any(x in chau for x in ("Chau", "Hasta la próxima")), chau)
        self.assertEqual(b.llamadas, [])

    def test_lo_que_no_se_entiende_sigue_ofreciendo_los_filtros(self):
        texto, lista = d.armar_respuesta_sin_ia("asdf qwerty", siempre([local("X")]))
        self.assertIn("filtros", texto)
        self.assertEqual(lista, [])

    def test_saludo_con_pedido_busca_igual(self):
        b = siempre([local("Pizzería Roma")])
        texto, lista = d.armar_respuesta_sin_ia("hola, busco pizzería en Palermo", b)
        self.assertIn("Pizzería Roma", texto)
        self.assertEqual(len(b.llamadas), 1)


class RespuestaDeBusqueda(unittest.TestCase):
    def test_dice_lo_que_entendio_y_sigue_siendo_valida(self):
        b = siempre([local("Verde Sin Gluten", has_gluten_free_options=True)])
        texto, lista = d.armar_respuesta_sin_ia("pizzería sin TACC en Palermo", b)
        self.assertIn("pizzería sin TACC en Palermo", texto)
        self.assertIn("Fuente: OpenStreetMap", texto)
        self.assertIn("no garantiza", texto)
        self.assertNotIn("Estas son las opciones que encontré en la base de datos", texto)
        self.assertTrue(d.validar_respuesta_ia(texto, lista)[0])

    def test_la_frase_inicial_es_estable_para_el_mismo_mensaje(self):
        b = siempre([local("A")])
        t1, _ = d.armar_respuesta_sin_ia("Restaurantes en Palermo", b)
        t2, _ = d.armar_respuesta_sin_ia("Restaurantes en Palermo", b)
        self.assertEqual(t1, t2)

    def test_hay_variedad_entre_mensajes_distintos(self):
        b = siempre([local("A")])
        intros = set()
        for zona in ("Palermo", "Belgrano", "Recoleta", "Caballito", "Almagro", "Flores", "Retiro", "Boedo"):
            texto, _ = d.armar_respuesta_sin_ia("Restaurantes en %s" % zona, b)
            intros.add(texto.split("\n\n")[1].split("\n")[0].replace(zona, "Z"))
        self.assertGreater(len(intros), 1)

    def test_sin_zona_pide_el_barrio(self):
        texto, _ = d.armar_respuesta_sin_ia("quiero pizza", siempre([local("A")]))
        self.assertIn("en qué barrio", texto)

    def test_fuera_de_cobertura_no_consulta_y_ofrece_ayuda(self):
        b = siempre([local("No debería aparecer")])
        texto, lista = d.armar_respuesta_sin_ia("pizzería en Montevideo", b)
        self.assertIn("Argentina", texto)
        self.assertIn("Decime la provincia", texto)
        self.assertEqual((lista, b.llamadas), ([], []))

    def test_el_interior_del_pais_se_consulta(self):
        b = siempre([local("A")])
        texto, lista = d.armar_respuesta_sin_ia("pizzería en Córdoba", b)
        self.assertEqual(b.llamadas[0]["ciudad"], "Córdoba")
        self.assertEqual(len(lista), 1)


class TonoYAviso(unittest.TestCase):
    def test_tc042_aviso_largo_solo_la_primera_vez(self):
        b = siempre([local("A")])
        primera, _ = d.armar_respuesta_sin_ia("pizzería en Palermo", b)
        siguiente, _ = d.armar_respuesta_sin_ia("¿y sin TACC?", b, historial=["pizzería en Palermo"], ya_avisado=True)
        self.assertIn("límite de su cuota", primera)
        self.assertNotIn("límite de su cuota", siguiente)
        self.assertIn("Sigo en modo simple", siguiente)

    def test_reconoce_sus_propias_respuestas_sin_ia(self):
        b = siempre([local("A")])
        for q in ("pizzería en Palermo", "hola", "qué podés hacer?"):
            texto, _ = d.armar_respuesta_sin_ia(q, b)
            self.assertTrue(d.es_respuesta_sin_ia(texto), q)
        self.assertTrue(d.es_respuesta_sin_ia(d.armar_respuesta_sin_ia("pizzería en Palermo", b, d.aviso_sin_ia_diaria())[0]))
        self.assertFalse(d.es_respuesta_sin_ia("Te recomiendo la Pizzería Roma en Palermo."))
        self.assertFalse(d.es_respuesta_sin_ia(None))

    def test_sin_resultados_suena_humano_y_ofrece_alternativas(self):
        texto, _ = d.armar_respuesta_sin_ia("sushi en Caballito", Buscador(lambda p: []))
        self.assertIn("todavía no encontré", texto)
        self.assertIn("flexibilizar", texto)
        self.assertIn("filtros de Explorar", texto)

    def test_el_saludo_tiene_variantes(self):
        b = siempre([])
        textos = {d.armar_respuesta_sin_ia(s, b)[0].split(".")[0] for s in ("hola", "holis", "buenas", "hey", "hola foody", "buen dia")}
        self.assertGreater(len(textos), 1)


class Seguimiento(unittest.TestCase):
    def test_tc040_seguimiento_retoma_zona_y_cocina(self):
        b = siempre([local("Verde", has_gluten_free_options=True)])
        texto, _ = d.armar_respuesta_sin_ia("¿y sin TACC?", b, historial=["pizzería en Palermo"])
        p = b.llamadas[0]
        self.assertEqual((p["ciudad"], p["tipo_cocina"], p["requiere_sin_tacc"]), ("Palermo", ["pizzeria"], True))
        self.assertIn("Sigo con tu búsqueda anterior", texto)

    def test_solo_el_barrio_nuevo_retoma_cocina_si_hay_marca(self):
        b = siempre([local("Roma", barrio="Belgrano")])
        d.armar_respuesta_sin_ia("y en Belgrano?", b, historial=["pizzería en Palermo"])
        self.assertEqual((b.llamadas[0]["ciudad"], b.llamadas[0]["tipo_cocina"]), ("Belgrano", ["pizzeria"]))

    def test_una_busqueda_nueva_con_su_zona_no_arrastra_filtros(self):
        b = siempre([local("A")])
        d.armar_respuesta_sin_ia("Restaurantes en Palermo", b, historial=["pizzería sin TACC en Belgrano"])
        p = b.llamadas[0]
        self.assertEqual(p["ciudad"], "Palermo")
        self.assertNotIn("requiere_sin_tacc", p)
        self.assertNotIn("tipo_cocina", p)

    def test_cadena_de_seguimientos(self):
        b = siempre([local("A")])
        d.armar_respuesta_sin_ia("y vegano?", b, historial=["pizzería en Palermo", "y sin TACC?"])
        p = b.llamadas[0]
        self.assertTrue(p["requiere_sin_tacc"] and p["requiere_vegano"])
        self.assertEqual(p["ciudad"], "Palermo")

    def test_sin_historial_se_comporta_como_antes(self):
        b = siempre([local("A")])
        texto, _ = d.armar_respuesta_sin_ia("¿y sin TACC?", b)
        self.assertNotIn("ciudad", b.llamadas[0])
        self.assertNotIn("Sigo con tu búsqueda", texto)


class SinResultados(unittest.TestCase):
    def test_afloja_la_cocina_pero_conserva_la_restriccion(self):
        regla = lambda p: [] if p.get("tipo_cocina") else [local("Verde Sin Gluten", cocina="cafe", has_gluten_free_options=True)]
        b = Buscador(regla)
        texto, lista = d.armar_respuesta_sin_ia("pizzería sin TACC en Palermo", b)
        self.assertIn("No encontré pizzería sin TACC en Palermo", texto)
        self.assertIn("Verde Sin Gluten", texto)
        self.assertTrue(b.llamadas[-1]["requiere_sin_tacc"])
        self.assertNotIn("tipo_cocina", b.llamadas[-1])
        self.assertEqual(len(lista), 1)
        self.assertIn("no garantiza", texto)
        self.assertTrue(d.validar_respuesta_ia(texto, lista)[0])

    def test_afloja_la_zona_conservando_cocina_y_restriccion(self):
        regla = lambda p: [] if p.get("ciudad") else [local("Roma Sin Gluten", barrio="Flores", has_gluten_free_options=True)]
        b = Buscador(regla)
        texto, lista = d.armar_respuesta_sin_ia("pizzería sin TACC en Caballito", b)
        self.assertIn("otras zonas", texto)
        ultimo = b.llamadas[-1]
        self.assertTrue(ultimo["requiere_sin_tacc"])
        self.assertEqual(ultimo["tipo_cocina"], ["pizzeria"])
        self.assertNotIn("ciudad", ultimo)
        self.assertEqual(len(lista), 1)

    def test_tc041_nunca_se_afloja_una_restriccion_alimentaria(self):
        b = Buscador(lambda p: [])
        texto, lista = d.armar_respuesta_sin_ia("pizzería sin TACC en Palermo", b)
        self.assertIn("flexibilizar", texto)
        self.assertEqual(lista, [])
        self.assertLessEqual(len(b.llamadas), 3)
        self.assertTrue(all(p.get("requiere_sin_tacc") for p in b.llamadas))

    def test_no_busca_en_toda_la_ciudad_si_solo_pidieron_una_zona(self):
        b = Buscador(lambda p: [])
        d.armar_respuesta_sin_ia("restaurantes en Palermo", b)
        self.assertEqual(len(b.llamadas), 1)        # sacar la zona dejaría una búsqueda vacía

    def test_error_de_base_en_el_reintento_no_rompe(self):
        llamadas = []

        def buscar(params):
            llamadas.append(params)
            return {"restaurants": []} if len(llamadas) == 1 else {"error": "x", "restaurants": []}

        texto, lista = d.armar_respuesta_sin_ia("pizzería en Palermo", buscar)
        self.assertEqual(lista, [])
        self.assertIn("flexibilizar", texto)
        self.assertNotIn("Traceback", texto)


class ZonaSinDatos(unittest.TestCase):
    """Si piden una zona de GBA que la base no cubre, no se muestran locales de otra zona como si fueran de esa.
    Se fija una lista de zonas chica para que estas pruebas no dependan de cuánta base haya cargada."""

    def setUp(self):
        parche = mock.patch.object(d, "BARRIOS", ("Palermo", "Lanús Oeste"))
        parche.start()
        self.addCleanup(d._reindexar_zonas)          # al restaurar BARRIOS se rehacen los índices
        self.addCleanup(parche.stop)
        d._reindexar_zonas()

    def test_tc047_zona_de_gba_sin_datos_lo_dice_y_no_consulta(self):
        for consulta, zona in (("hamburguesas veganas en Tigre", "Tigre"), ("pizzería en Quilmes", "Quilmes"),
                               ("comer en Morón sin TACC", "Morón")):
            b = siempre([local("No debería aparecer", barrio="Palermo")])
            texto, lista = d.armar_respuesta_sin_ia(consulta, b)
            self.assertIn("Todavía no tengo locales cargados en %s" % zona, texto, consulta)
            self.assertIn("Tengo un comercio", texto)
            self.assertEqual((lista, b.llamadas), ([], []), consulta)

    def test_una_zona_con_nombre_parcial_se_entiende_como_la_que_si_tiene_datos(self):
        b = siempre([local("Parrilla Oeste", barrio="Lanús Oeste", cocina="parrilla")])
        d.armar_respuesta_sin_ia("algo vegano cerca de Lanús", b)
        self.assertEqual(b.llamadas[0]["ciudad"], "Lanús Oeste")

    def test_un_seguimiento_no_hereda_la_zona_vieja_si_piden_otra_sin_datos(self):
        b = siempre([local("A")])
        texto, _ = d.armar_respuesta_sin_ia("¿y en Tigre?", b, historial=["pizzería en Palermo"])
        self.assertIn("Tigre", texto)
        self.assertEqual(b.llamadas, [])


class ZonasDeLaBaseUnificada(unittest.TestCase):
    """Con la base unificada cargada (backend/zonas_dataset.py) las zonas de GBA con locales sí se reconocen."""

    def test_tc047_las_zonas_con_locales_se_reconocen(self):
        for consulta, zona in (("pizzería en Tigre", "Tigre"), ("sushi en Quilmes", "Quilmes"), ("café en Béccar", "Béccar"),
                               ("sushi en Hurlingham", "Hurlingham")):
            self.assertEqual(d.interpretar_consulta_local(consulta).get("ciudad"), zona, consulta)

    def test_los_partidos_sin_locales_siguen_avisando(self):
        p = d.interpretar_consulta_local("pizzería en Presidente Perón")
        self.assertEqual(p.get("zona_sin_datos"), "Presidente Perón")
        self.assertNotIn("ciudad", p)


class ConexionConElChat(unittest.TestCase):
    """Control estático (chat_service necesita Gemini y la base para importarse)."""

    def test_el_chat_le_pasa_la_sesion_al_modo_sin_ia(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "backend", "chat_service.py"), encoding="utf-8") as f:
            src = f.read()
        # Gemini falla -> _sin_gemini (respaldo) -> _sin_ia: en todos los pasos viaja la sesión.
        llamadas = [l for l in src.splitlines() if "self._sin_ia(message" in l or "self._sin_gemini(message" in l]
        self.assertGreaterEqual(len(llamadas), 5)
        self.assertTrue(all("session_id" in l for l in llamadas), llamadas)
        self.assertIn("historial=previos", src)


if __name__ == "__main__":
    unittest.main()
