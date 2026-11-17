"""
Pruebas del verificador previo al despliegue (scripts/verificar_despliegue.py). No usan red, Gemini ni base de datos.
    python -m unittest tests.test_verificar_despliegue -v
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import verificar_despliegue as v  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
CLAVE_FALSA = "AIza" + "B" * 35
BUENAS = {
    "DATABASE_URL": "postgresql://usuario:clave123@ep-cool-123.us-east-2.aws.neon.tech/neondb?sslmode=require",
    "GEMINI_API_KEY": CLAVE_FALSA,
    "SESSION_SECRET": "Zq8Lm2" * 8,
    "GOOGLE_CLIENT_ID": "123456-abc.apps.googleusercontent.com",
    "FRONTEND_ORIGINS": "https://gastronomia.vercel.app",
    "ADMIN_EMAILS": "yo@gmail.com",
    "COMERCIOS_AUTOAPROBADOS": "0",
    "ENTORNO": "produccion",
}


def estados(resultados):
    return {nombre: estado for estado, nombre, _ in resultados}


class Variables(unittest.TestCase):
    def test_tc061_variables_bien_cargadas_no_dan_faltas(self):
        r = v.chequear_variables(BUENAS)
        self.assertEqual([x for x in r if x[0] == "FALTA"], [])
        self.assertEqual(estados(r)["DATABASE_URL"], "OK")

    def test_tc061_detecta_cada_error_tipico(self):
        casos = (
            ("DATABASE_URL", "postgresql://postgres:clave@localhost:5432/gastro_ia"),     # apunta a la PC
            ("DATABASE_URL", "postgresql://u:c@ep-x.aws.neon.tech/neondb"),                 # falta sslmode
            ("GEMINI_API_KEY", "pega_aqui_tu_clave_nueva_de_gemini"),                        # relleno
            ("SESSION_SECRET", "corta"),
            ("SESSION_SECRET", "pega_una_clave_de_32_o_mas_caracteres_largos"),
            ("FRONTEND_ORIGINS", "https://gastronomia.vercel.app/"),                         # barra final
            ("FRONTEND_ORIGINS", "http://gastronomia.vercel.app"),                           # sin https
            ("FRONTEND_ORIGINS", ""),
        )
        for nombre, valor in casos:
            r = estados(v.chequear_variables(dict(BUENAS, **{nombre: valor})))
            self.assertEqual(r[nombre], "FALTA", "%s=%s" % (nombre, valor))

    def test_tc061_avisos_opcionales(self):
        r = estados(v.chequear_variables(dict(BUENAS, FRONTEND_ORIGINS="http://localhost:5173", COMERCIOS_AUTOAPROBADOS="1", PORT="8000", ADMIN_EMAILS="")))
        self.assertEqual(r["FRONTEND_ORIGINS"], "AVISO")
        self.assertEqual(r["COMERCIOS_AUTOAPROBADOS"], "AVISO")
        self.assertEqual(r["PORT"], "AVISO")
        self.assertEqual(r["ADMIN_EMAILS"], "AVISO")

    def test_nunca_imprime_el_valor_de_las_claves(self):
        texto = " ".join(d for _, _, d in v.chequear_variables(dict(BUENAS, SESSION_SECRET="corta")))
        for secreto in (CLAVE_FALSA, "clave123", "corta"):
            self.assertNotIn(secreto, texto)


class ChequeosDeArchivos(unittest.TestCase):
    def test_tc062_el_proyecto_real_pasa_estructura_dependencias_y_finales_de_linea(self):
        for chequeo in (v.chequear_estructura, v.chequear_dependencias):
            self.assertEqual([e for e, _, _ in chequeo(RAIZ) if e == "FALTA"], [], chequeo.__name__)
        self.assertEqual([e for e, _, _ in v.chequear_finales_de_linea(RAIZ) if e == "FALTA"], [])

    def test_tc062_detecta_crlf_en_el_script_de_arranque(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            (raiz / "deploy").mkdir()
            (raiz / "deploy" / "entrypoint.sh").write_bytes(b"#!/bin/sh\r\nexec uvicorn\r\n")
            self.assertEqual(estados(v.chequear_finales_de_linea(raiz))["Finales de línea (LF)"], "FALTA")

    def test_tc062_detecta_una_clave_escrita_en_el_codigo_pero_ignora_los_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            (raiz / ".env").write_text("GEMINI_API_KEY=%s\n" % CLAVE_FALSA, encoding="utf-8")
            self.assertEqual(estados(v.chequear_secretos(raiz))["Claves en el código"], "OK")
            (raiz / "config.py").write_text('CLAVE = "%s"\n' % CLAVE_FALSA, encoding="utf-8")
            self.assertEqual(estados(v.chequear_secretos(raiz))["Claves en el código"], "FALTA")

    def test_el_proyecto_real_no_tiene_claves_escritas(self):
        self.assertEqual(estados(v.chequear_secretos(RAIZ))["Claves en el código"], "OK")

    def test_gitattributes_fuerza_lf_en_los_scripts(self):
        contenido = (RAIZ / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("*.sh text eol=lf", contenido)
        self.assertIn("Dockerfile text eol=lf", contenido)

    def test_el_dockerfile_limpia_crlf_del_entrypoint(self):
        self.assertIn("sed -i 's/\\r$//' /app/entrypoint.sh", (RAIZ / "Dockerfile").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
