"""
Pruebas de la API (FastAPI TestClient). Necesitan las dependencias instaladas:
    pip install -r backend/requirements.txt
    python -m unittest tests.test_api_diseno -v

- Clase `ApiSinBaseDeDatos`: no necesita PostgreSQL (valida entradas, seguridad, CORS).
- Clase `ApiConBaseDeDatos`: solo corre si definís PRUEBAS_CON_BD=1 y tenés PostgreSQL con los datos.
Si falta alguna dependencia, las pruebas se saltean (no fallan).
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
    import main
    import diseno
    DISPONIBLE, MOTIVO = True, ""
except Exception as e:  # dependencias sin instalar
    DISPONIBLE, MOTIVO = False, "Faltan dependencias: %s" % e


@unittest.skipUnless(DISPONIBLE, MOTIVO)
class ApiSinBaseDeDatos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = TestClient(main.app)
        # El chat exige sesión: en estas pruebas se simula un usuario ya autenticado.
        main.app.dependency_overrides[main.usuario_actual] = lambda: {"sub": "prueba", "uid": 1, "email": "t@example.com", "nombre": "T"}

    @classmethod
    def tearDownClass(cls):
        main.app.dependency_overrides.pop(main.usuario_actual, None)

    def setUp(self):
        main._limitador_chat = diseno.LimitadorTasa(20, 60)

    # --- parámetros de búsqueda que antes daban error 500
    def test_busqueda_rechaza_limit_y_offset_invalidos(self):
        for q in ("limit=0", "limit=-5", "offset=-1", "limit=101"):
            with self.subTest(q=q):
                self.assertEqual(self.c.get("/api/restaurants?" + q).status_code, 422)

    # --- login (sin sesión no hay chat)
    def test_chat_con_token_falso_es_401_y_el_historial_exige_cuenta(self):
        r = self.c.post("/api/chat", json={"message": "hola", "session_id": "ok"}, headers={"Authorization": "Bearer falso.token"})
        self.assertEqual(r.status_code, 401)
        main.app.dependency_overrides.pop(main.usuario_actual, None)
        try:
            self.assertEqual(self.c.get("/api/chat/historial").status_code, 401)
        finally:
            main.app.dependency_overrides[main.usuario_actual] = lambda: {"sub": "prueba", "uid": 1, "email": "t@example.com", "nombre": "T"}
    def test_comercio_exige_sesion(self):
        main.app.dependency_overrides.pop(main.usuario_actual, None)
        try:
            self.assertEqual(self.c.get("/api/comercio/mio").status_code, 401)
            self.assertEqual(self.c.put("/api/comercio/mio", json={"nombre": "Local"}).status_code, 401)
            self.assertEqual(self.c.get("/api/admin/comercios").status_code, 401)
        finally:
            main.app.dependency_overrides[main.usuario_actual] = lambda: {"sub": "prueba", "uid": 1, "email": "t@example.com", "nombre": "T"}

    def test_solo_un_administrador_revisa_comercios(self):
        self.assertEqual(self.c.get("/api/admin/comercios").status_code, 403)
        self.assertEqual(self.c.post("/api/admin/comercios/1/estado", json={"estado": "aprobado"}).status_code, 403)
    def test_comercio_invalido_es_422(self):
        base = {"nombre": "Dulces de prueba", "rubros": ["pasteleria"], "modalidad": "local", "zona": "CABA",
                "localidad": "Belgrano", "direccion": "Av. Cabildo 1000", "declaracion": True}
        for malo in ({"nombre": ""}, {"rubros": []}, {"rubros": ["inventado"]}, {"rubros": ["cafe", "cafe"]},
                     {"zona": "Montevideo"}, {"sin_tacc": "tal vez"}, {"localidad": ""}, {"declaracion": False},
                     {"telefono": "abc"}, {"instagram": "con espacios"}, {"sitio_web": "javascript:alert(1)"},
                     {"direccion": ""},                                              # local físico sin dirección
                     {"modalidad": "online", "direccion": ""},                       # online sin Instagram ni web
                     {"descripcion": "escribime a ana@example.com"}):
            r = self.c.put("/api/comercio/mio", json={**base, **malo})
            self.assertEqual(r.status_code, 422, malo)
    def test_chat_responde_sin_ia_ante_datos_personales_y_temas_ajenos(self):
        r = self.c.post("/api/chat", json={"message": "mi mail es ana@example.com", "session_id": "ok"})
        self.assertEqual(r.json()["response"], diseno.MENSAJE_DATOS_PERSONALES)
        r = self.c.post("/api/chat", json={"message": "escribime un cuento", "session_id": "ok"})
        self.assertEqual(r.json()["response"], diseno.MENSAJE_FUERA_DE_TEMA)
        self.assertEqual(r.json()["restaurants"], [])

    def test_el_invitado_puede_usar_el_chat_sin_registrarse(self):
        main.app.dependency_overrides.pop(main.usuario_actual, None)
        try:
            r = self.c.post("/api/chat", json={"message": "mi mail es ana@example.com", "session_id": "ok"})
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.json()["session_id"].startswith("a"))      # sesión de invitado, no de cuenta
        finally:
            main.app.dependency_overrides[main.usuario_actual] = lambda: {"sub": "prueba", "uid": 1, "email": "t@example.com", "nombre": "T"}
    def test_login_sin_configurar_es_503(self):
        viejo = main.GOOGLE_CLIENT_ID
        main.GOOGLE_CLIENT_ID = ""
        try:
            r = self.c.post("/api/auth/google", json={"credential": "x" * 40})
            self.assertEqual(r.status_code, 503)
        finally:
            main.GOOGLE_CLIENT_ID = viejo

    # --- seguridad
    def test_tc028_descargas_no_salen_de_analytics(self):
        for ruta in ("..%2F.env", "..%2F..%2F.env", "%2e%2e%2f.env", "..%5Cbackend%5C.env", "csv%2F..%2F..%2Fbackend%2F.env"):
            r = self.c.get("/api/downloads/" + ruta)
            self.assertEqual(r.status_code, 404, ruta)
            self.assertNotIn("GEMINI_API_KEY", r.text)

    def test_tc030_cors_no_acepta_origenes_ajenos(self):
        r = self.c.options("/api/chat", headers={"Origin": "http://sitio-malo.example",
                                                  "Access-Control-Request-Method": "POST"})
        self.assertNotIn("access-control-allow-origin", {k.lower() for k in r.headers})

    def test_tc029_rate_limit_del_chat(self):
        cuerpo = {"message": "hola", "session_id": "../mala"}   # se rechaza antes de usar la BD
        codigos = [self.c.post("/api/chat", json=cuerpo).status_code for _ in range(22)]
        self.assertEqual(codigos[0], 422)
        self.assertEqual(codigos[-1], 429)

    # --- validación de entradas (HU-01, HU-11, HU-13)
    def test_tc020_tc021_chat_valida_sesion_y_largo(self):
        self.assertEqual(self.c.post("/api/chat", json={"message": "hola", "session_id": "../../x"}).status_code, 422)
        self.assertEqual(self.c.post("/api/chat", json={"message": "a" * 1501, "session_id": "ok"}).status_code, 422)
        self.assertEqual(self.c.post("/api/chat", json={"message": "", "session_id": "ok"}).status_code, 422)

    def test_tc035_usuario_con_email_invalido(self):
        r = self.c.post("/api/usuarios", json={"nombre": "Ana", "email": "no-es-un-mail"})
        self.assertEqual(r.status_code, 422)

    def test_usuario_nombre_demasiado_largo(self):
        r = self.c.post("/api/usuarios", json={"nombre": "x" * 101, "email": "a@b.com"})
        self.assertEqual(r.status_code, 422)

    def test_tc037_resena_demasiado_corta(self):
        r = self.c.post("/api/resenas", json={"id_establecimiento": 1, "texto": "ok"})
        self.assertEqual(r.status_code, 422)

    def test_id_no_numerico(self):
        self.assertEqual(self.c.get("/api/conversaciones/abc/mensajes").status_code, 422)
        self.assertEqual(self.c.get("/api/usuarios/abc").status_code, 422)


@unittest.skipUnless(DISPONIBLE and os.getenv("PRUEBAS_CON_BD") == "1", "Definí PRUEBAS_CON_BD=1 (necesita PostgreSQL)")
class ApiConBaseDeDatos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = TestClient(main.app)
        cls.email = "prueba_%d@example.com" % int(time.time())
        # Se simula una cuenta de Google ya autenticada; cada persona solo accede a su propio perfil.
        from database import engine
        from models_diseno import crear_tablas_diseno
        crear_tablas_diseno(engine)             # asegura las tablas nuevas (p. ej. comercios)
        cls.ident = {"sub": "prueba", "uid": None, "email": cls.email, "nombre": "Prueba"}
        main.app.dependency_overrides[main.usuario_actual] = lambda: cls.ident
        r = cls.c.post("/api/usuarios", json={"nombre": "Prueba", "email": cls.email, "restricciones": ["Vegano"],
                                              "preferencias": [{"tipo": "zona", "valor": "Palermo"}]})
        cls.ident["uid"] = r.json()["id_usuario"]

    @classmethod
    def tearDownClass(cls):
        main.app.dependency_overrides.pop(main.usuario_actual, None)

    def test_01_restricciones(self):
        r = self.c.get("/api/restricciones")
        self.assertEqual(r.status_code, 200)
        nombres = [x["nombre"] for x in r.json()["restricciones"]]
        self.assertIn("Vegano", nombres)

    def test_02_tc033_tc034_lectura_y_actualizacion_de_perfil_propio(self):   # HU-11, 12
        uid = self.ident["uid"]
        self.assertEqual(self.c.get("/api/usuarios/%d" % uid).json()["restricciones"], ["Vegano"])
        r = self.c.put("/api/usuarios/%d" % uid, json={"restricciones": ["Vegetariano"]})
        self.assertEqual(r.json()["restricciones"], ["Vegetariano"])
        self.assertEqual(self.c.post("/api/usuarios", json={"nombre": "Otro", "email": self.email}).json()["id_usuario"], uid)

    def test_03_tc035_restriccion_desconocida(self):
        r = self.c.put("/api/usuarios/%d" % self.ident["uid"], json={"restricciones": ["Inventada"]})
        self.assertEqual(r.status_code, 422)

    def test_03b_no_se_accede_a_perfiles_ajenos_ni_se_crean_con_otro_correo(self):
        self.assertEqual(self.c.get("/api/usuarios/%d" % (self.ident["uid"] + 1000000)).status_code, 403)
        self.assertEqual(self.c.put("/api/usuarios/%d" % (self.ident["uid"] + 1000000), json={"nombre": "X"}).status_code, 403)
        r = self.c.post("/api/usuarios", json={"nombre": "X", "email": "otra_persona@example.com"})
        self.assertEqual(r.status_code, 403)
        r = self.c.put("/api/usuarios/%d" % self.ident["uid"], json={"email": "otra_persona@example.com"})
        self.assertEqual(r.status_code, 403)

    def test_04_ficha_con_fuente_y_advertencia(self):            # HU-02, 04, 05
        lista = self.c.get("/api/establecimientos?limit=1").json()
        rid = lista["results"][0]["restaurant_id"]
        d = self.c.get("/api/establecimientos/%d" % rid).json()
        self.assertIn("advertencia_alimentaria", d)
        self.assertIn("source", d)
        self.assertEqual(self.c.get("/api/establecimientos/999999999").status_code, 404)

    def test_05_tc036_resena_y_valoraciones(self):                     # HU-13
        rid = self.c.get("/api/establecimientos?limit=1").json()["results"][0]["restaurant_id"]
        r = self.c.post("/api/resenas", json={"id_establecimiento": rid,
                                              "texto": "La comida estaba rica pero el servicio fue lento."})
        self.assertEqual(r.status_code, 200, r.text)
        aspectos = {v["aspecto"] for v in r.json()["valoraciones"]}
        self.assertTrue({"comida", "servicio"} <= aspectos)

    def test_07_registro_de_comercio(self):
        viejo = os.environ.get("COMERCIOS_AUTOAPROBADOS")
        os.environ["COMERCIOS_AUTOAPROBADOS"] = "0"        # la prueba no debe publicar nada en el catálogo
        try:
            self.assertIsNone(self.c.get("/api/comercio/mio").json()["comercio"])
            datos = {"nombre": "Dulces de prueba", "rubros": ["pasteleria"], "modalidad": "online",
                     "zona": "Provincia de Buenos Aires", "localidad": "Lomas de Zamora", "sin_tacc": "opciones",
                     "instagram": "@dulces_de_prueba", "declaracion": True}
            r = self.c.put("/api/comercio/mio", json=datos)
            self.assertEqual(r.status_code, 200)
            com = r.json()["comercio"]
            self.assertEqual((com["estado"], com["sin_tacc"], com["instagram"], com["modalidad"]),
                             ("pendiente", "opciones", "dulces_de_prueba", "online"))
            datos["rubros"] = ["pasteleria", "cafe"]
            self.assertEqual(self.c.put("/api/comercio/mio", json=datos).json()["comercio"]["rubros"], ["pasteleria", "cafe"])
            self.assertEqual(self.c.get("/api/comercio/mio").json()["comercio"]["nombre"], "Dulces de prueba")
        finally:
            if viejo is None:
                os.environ.pop("COMERCIOS_AUTOAPROBADOS", None)
            else:
                os.environ["COMERCIOS_AUTOAPROBADOS"] = viejo
    def test_06_tc038_mensajes_de_conversacion_inexistente(self):
        self.assertEqual(self.c.get("/api/conversaciones/999999999/mensajes").status_code, 404)


if __name__ == "__main__":
    unittest.main()
