"""
Proveedor de IA de respaldo (backend/respaldo_ia.py): Gemini -> respaldo -> modo sin IA.
    python -m unittest tests.test_respaldo_ia -v
No usan Gemini, Groq ni PostgreSQL: las respuestas del proveedor se simulan.
"""
import json
import os
import sys
import unittest
from unittest import mock

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:x@localhost:5432/gastro_ia")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import chat_service as ch  # noqa: E402
import cuota  # noqa: E402
import respaldo_ia as r  # noqa: E402

CON_CLAVE = {"RESPALDO_API_KEY": "gsk_prueba123", "RESPALDO_URL": "", "RESPALDO_MODELO": ""}


def resp(status=200, mensaje=None, headers=None):
    m = mock.Mock(status_code=status, headers=headers or {})
    m.json.return_value = {"choices": [{"message": mensaje or {}}]}
    return m


def texto(t):
    return resp(mensaje={"role": "assistant", "content": t})


def herramienta(nombre, args, id_="call_1"):
    return resp(mensaje={"role": "assistant", "content": None, "tool_calls": [
        {"id": id_, "type": "function", "function": {"name": nombre, "arguments": json.dumps(args)}}]})


class Modulo(unittest.TestCase):
    def setUp(self):
        r.reiniciar()

    def test_sin_clave_esta_apagado(self):
        with mock.patch.dict(os.environ, {"RESPALDO_API_KEY": ""}):
            self.assertFalse(r.disponible())
            with self.assertRaises(r.RespaldoNoDisponible):
                r.conversar("hola", [], lambda n, a: {})

    def test_usa_las_mismas_herramientas_y_reglas_que_gemini(self):
        nombres = {h["function"]["name"] for h in r.HERRAMIENTAS}
        self.assertEqual(nombres, {"buscar_restaurantes", "obtener_detalle_restaurante",
                                   "buscar_por_cercania", "obtener_fuentes"})
        with mock.patch.dict(os.environ, CON_CLAVE), \
                mock.patch.object(r.requests, "post", return_value=texto("Hola")) as post:
            r.conversar("hola", [{"role": "user", "text": "antes"}, {"role": "model", "text": "dale"}],
                        lambda n, a: {})
        cuerpo = post.call_args.kwargs["json"]
        self.assertEqual(cuerpo["messages"][0], {"role": "system", "content": r.SYSTEM_PROMPT})
        self.assertEqual([m["role"] for m in cuerpo["messages"]], ["system", "user", "assistant", "user"])
        self.assertEqual(cuerpo["model"], r.MODELO_POR_DEFECTO)
        self.assertTrue(post.call_args.args[0].startswith("https://api.groq.com/"))

    def test_ejecuta_herramientas_contra_la_base_y_devuelve_el_texto(self):
        pedidos = []
        respuestas = [herramienta("buscar_restaurantes", {"ciudad": "Palermo", "requiere_sin_tacc": True}),
                      texto("Te recomiendo «La Esquina».")]
        with mock.patch.dict(os.environ, CON_CLAVE), \
                mock.patch.object(r.requests, "post", side_effect=respuestas) as post:
            t = r.conversar("sin tacc en palermo", [],
                            lambda n, a: pedidos.append((n, a)) or {"restaurants": [{"name": "La Esquina"}]})
        self.assertEqual(t, "Te recomiendo «La Esquina».")
        self.assertEqual(pedidos, [("buscar_restaurantes", {"ciudad": "Palermo", "requiere_sin_tacc": True})])
        ultimo = post.call_args.kwargs["json"]["messages"][-1]
        self.assertEqual((ultimo["role"], ultimo["tool_call_id"]), ("tool", "call_1"))

    def test_sin_cuota_se_pausa_y_no_insiste(self):
        with mock.patch.dict(os.environ, CON_CLAVE), \
                mock.patch.object(r.requests, "post", return_value=resp(429, headers={"retry-after": "30"})) as post:
            with self.assertRaises(r.RespaldoNoDisponible):
                r.conversar("hola", [], lambda n, a: {})
            self.assertFalse(r.disponible())
            with self.assertRaises(r.RespaldoNoDisponible):
                r.conversar("hola", [], lambda n, a: {})
        self.assertEqual(post.call_count, 1)

    def test_errores_de_red_o_formato_no_rompen(self):
        for efecto in (r.requests.ConnectionError("x"), r.requests.Timeout("x"), resp(500),
                       resp(200, mensaje={"content": ""})):
            r.reiniciar()
            with mock.patch.dict(os.environ, CON_CLAVE), mock.patch.object(r.requests, "post", side_effect=[efecto]):
                with self.assertRaises(r.RespaldoNoDisponible):
                    r.conversar("hola", [], lambda n, a: {})

    def test_no_entra_en_un_bucle_de_herramientas(self):
        with mock.patch.dict(os.environ, CON_CLAVE), \
                mock.patch.object(r.requests, "post", return_value=herramienta("obtener_fuentes", {"restaurant_id": 1})):
            with self.assertRaises(r.RespaldoNoDisponible):
                r.conversar("fuentes", [], lambda n, a: {})


class CadenaDelChat(unittest.TestCase):
    """Gemini sin cuota -> respaldo; respaldo sin cuota -> modo sin IA."""

    def setUp(self):
        r.reiniciar()
        self.servicio = ch.ChatService(db=None, gemini_api_key="")
        self.servicio._guardar_turno = mock.Mock()
        self.servicio._sin_ia = mock.Mock(return_value="MODO SIN IA")
        self.servicio._execute_tool = mock.Mock(return_value={"restaurants": [{"id": 7, "name": "Lo de Ana"}]})

    def test_sin_clave_de_gemini_responde_el_respaldo(self):
        respuestas = [herramienta("buscar_restaurantes", {"ciudad": "Flores"}), texto("Probá «Lo de Ana».")]
        with mock.patch.dict(os.environ, CON_CLAVE), mock.patch.object(r.requests, "post", side_effect=respuestas), \
                mock.patch.object(ch._SESIONES_BD, "cargar", return_value=[]):
            t = self.servicio.send_message("algo en flores", "prueba-respaldo")
        self.assertEqual(t, "Probá «Lo de Ana».")
        self.assertEqual(self.servicio.last_restaurants, [{"id": 7, "name": "Lo de Ana"}])
        self.servicio._sin_ia.assert_not_called()
        self.servicio._guardar_turno.assert_called_once()

    def test_si_el_respaldo_falla_responde_el_modo_sin_ia(self):
        with mock.patch.dict(os.environ, CON_CLAVE), mock.patch.object(r.requests, "post", return_value=resp(429)), \
                mock.patch.object(ch._SESIONES_BD, "cargar", return_value=[]):
            self.assertEqual(self.servicio.send_message("algo en flores", "prueba-respaldo"), "MODO SIN IA")

    def test_sin_respaldo_configurado_es_igual_que_antes(self):
        with mock.patch.dict(os.environ, {"RESPALDO_API_KEY": ""}), \
                mock.patch.object(r.requests, "post", side_effect=AssertionError("no debe llamar")):
            self.assertEqual(self.servicio.send_message("algo en flores", "prueba-respaldo"), "MODO SIN IA")

    def test_gemini_sin_cuota_pasa_al_respaldo(self):
        self.servicio.gemini.api_key = "clave-gemini"
        self.servicio._obtener_chat = mock.Mock(return_value=object())
        self.servicio._enviar = mock.Mock(side_effect=cuota.CuotaAgotada(60, diaria=True))
        with mock.patch.dict(os.environ, CON_CLAVE), mock.patch.object(r.requests, "post", return_value=texto("Respaldo")), \
                mock.patch.object(ch._SESIONES_BD, "cargar", return_value=[]):
            self.assertEqual(self.servicio.send_message("pizza en palermo", "prueba-respaldo"), "Respaldo")


if __name__ == "__main__":
    unittest.main()
