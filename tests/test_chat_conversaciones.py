"""
Pruebas de las conversaciones del chat: cada cuenta puede tener varias y solo ve las suyas.
    python -m unittest tests.test_chat_conversaciones -v
Con PostgreSQL: PRUEBAS_CON_BD=1 (las que necesitan base se saltean si no está).
"""
import os
import sys
import time
import unittest

RAIZ = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(RAIZ, "backend"))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:x@localhost:5432/gastro_ia")

try:
    from fastapi.testclient import TestClient
    import diseno
    import main
    import sesion
    DISPONIBLE, MOTIVO = True, ""
except Exception as e:  # dependencias sin instalar
    DISPONIBLE, MOTIVO = False, "Faltan dependencias: %s" % e

SECRETO = "s" * 48


@unittest.skipUnless(DISPONIBLE, MOTIVO)
class ClavesDeConversacion(unittest.TestCase):
    """La clave de cada chat lleva el uid del token: no se puede pedir el de otra persona."""

    def test_cada_chat_tiene_su_clave_y_la_cuenta_manda(self):
        self.assertEqual(main._clave_chat(7, ""), "u7")
        self.assertEqual(main._clave_chat(7, "principal"), "u7")
        self.assertEqual(main._clave_chat(7, "chat_123"), "u7_chat_123")
        self.assertNotEqual(main._clave_chat(7, "chat_1"), main._clave_chat(8, "chat_1"))
        self.assertEqual(main._chat_id_de(7, "u7_chat_123"), "chat_123")
        self.assertEqual(main._chat_id_de(7, "u7"), "principal")
        self.assertIsNone(main._chat_id_de(7, "u8_chat_1"))
        self.assertIsNone(main._chat_id_de(7, "a123456"))

    def test_chat_id_invalido_se_rechaza(self):
        for malo in ("", "x" * 41, "../otro", "con espacio", "a;b", None):
            self.assertFalse(main._chat_id_valido(malo), malo)
        self.assertTrue(main._chat_id_valido("chat_1750000000000"))


@unittest.skipUnless(DISPONIBLE and os.getenv("PRUEBAS_CON_BD") == "1",
                     "Definí PRUEBAS_CON_BD=1 (necesita PostgreSQL)")
class ConversacionesPorCuenta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = TestClient(main.app)
        from database import engine
        from models_diseno import crear_tablas_diseno
        crear_tablas_diseno(engine)             # asegura conversaciones y mensajes
        cls.email = "chats_%d@example.com" % int(time.time())
        # El `sub` identifica la cuota diaria: único por corrida para no agotar la de otra prueba.
        cls.sub = "chats_%d" % int(time.time() * 1000)
        # Crear la cuenta exige identidad (igual que en el login real); después se usa un token firmado.
        main.app.dependency_overrides[main.usuario_actual] = lambda: {
            "sub": cls.sub, "uid": 0, "email": cls.email, "nombre": "Chats"}
        r = cls.c.post("/api/usuarios", json={"nombre": "Chats", "email": cls.email})
        main.app.dependency_overrides.pop(main.usuario_actual, None)
        cls.uid = r.json()["id_usuario"]
        os.environ["SESSION_SECRET"] = SECRETO    # token real: /api/chat acepta cuenta o invitado
        cls.h = cls._cabecera(cls.uid, cls.sub)
        main._limitador_chat = diseno.LimitadorTasa(60, 60)

    @classmethod
    def tearDownClass(cls):
        os.environ.pop("SESSION_SECRET", None)

    @classmethod
    def _cabecera(cls, uid: int, sub: str) -> dict:
        datos = {"sub": sub, "uid": uid, "email": cls.email, "nombre": "Chats"}
        return {"Authorization": "Bearer " + sesion.firmar_sesion(datos, SECRETO)}

    def test_01_una_cuenta_puede_tener_varias_conversaciones(self):
        a = self.c.post("/api/chat", json={"message": "Busco pizza en Palermo", "session_id": "s1", "chat_id": "chat_a"}, headers=self.h)
        b = self.c.post("/api/chat", json={"message": "Busco vegano en Belgrano", "session_id": "s2", "chat_id": "chat_b"}, headers=self.h)
        self.assertEqual(a.status_code, 200, a.text)
        self.assertEqual(b.status_code, 200, b.text)

        lista = self.c.get("/api/chat/conversaciones", headers=self.h).json()["conversaciones"]
        ids = [x["chat_id"] for x in lista]
        self.assertIn("chat_a", ids)
        self.assertIn("chat_b", ids)
        self.assertTrue(all(x["titulo"] for x in lista), "cada chat muestra su primer mensaje como título")

        # Cada conversación tiene solo sus mensajes: el contexto no se mezcla.
        ha = self.c.get("/api/chat/historial", params={"chat_id": "chat_a"}, headers=self.h).json()
        self.assertEqual(ha["chat_id"], "chat_a")
        self.assertTrue(any("pizza" in m["contenido"] for m in ha["mensajes"]))
        self.assertFalse(any("vegano" in m["contenido"] for m in ha["mensajes"]))
        hb = self.c.get("/api/chat/historial", params={"chat_id": "chat_b"}, headers=self.h).json()
        self.assertTrue(any("vegano" in m["contenido"] for m in hb["mensajes"]))

    def test_02_otra_cuenta_no_ve_las_conversaciones_ajenas(self):
        h_otro = self._cabecera(self.uid + 1000000, self.sub + "_otro")
        lista = self.c.get("/api/chat/conversaciones", headers=h_otro).json()["conversaciones"]
        self.assertNotIn("chat_a", [x["chat_id"] for x in lista])
        h = self.c.get("/api/chat/historial", params={"chat_id": "chat_a"}, headers=h_otro).json()
        self.assertEqual(h["mensajes"], [])

    def test_03_chat_id_invalido_es_422(self):
        self.assertEqual(self.c.get("/api/chat/historial", params={"chat_id": "x" * 41}, headers=self.h).status_code, 422)
        r = self.c.post("/api/chat", json={"message": "hola", "chat_id": "../otro"}, headers=self.h)
        self.assertEqual(r.status_code, 422)

    def test_04_sin_token_no_hay_historial(self):
        self.assertEqual(self.c.get("/api/chat/historial").status_code, 401)
        self.assertEqual(self.c.get("/api/chat/conversaciones").status_code, 401)


if __name__ == "__main__":
    unittest.main()
