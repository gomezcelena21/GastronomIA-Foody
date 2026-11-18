"""
Pruebas automatizadas de SEGURIDAD que leen el código del proyecto (análisis estático).
Cada prueba corresponde a un hallazgo de la auditoría (docs/seguridad_ciberseguridad.md).
    python -m unittest discover -s tests -v
"""
import os
import re
import tempfile
import unittest
from pathlib import Path

import sys
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))
import diseno  # noqa: E402

SALTAR = {"node_modules", ".git", "__pycache__", "dist", "raw", "data", "backend_old", "docs_tpi_backup", "tests"}


def archivos(exts, base=RAIZ):
    for dp, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SALTAR]
        for f in files:
            if f.endswith(exts):
                yield Path(dp) / f


def leer(p):
    return Path(p).read_text(encoding="utf-8", errors="ignore")


class SecretosEnElCodigo(unittest.TestCase):
    def test_sin_contrasenas_de_bd_en_el_codigo(self):
        url = re.compile(r"postgres(?:ql)?://[^:/\s'\"]+:([^@\s'\"]+)@")
        falsos = ("tu_clave", "clave", "***", "{", "%", "$", "usuario")
        malos = []
        for p in archivos((".py", ".bat", ".md", ".sql", ".html")):
            for m in url.finditer(leer(p)):
                if not any(f in m.group(1).lower() for f in falsos):
                    malos.append("%s: %s" % (p.relative_to(RAIZ), m.group(0)[:30]))
            if re.search(r"['\"]password['\"]\s*:\s*['\"][^'\"]+['\"]", leer(p)):
                malos.append("%s: password literal" % p.relative_to(RAIZ))
        self.assertEqual(malos, [], "Contraseñas escritas en el código")

    def test_tc031_sin_claves_de_api_en_archivos_versionables(self):
        patron = re.compile(r"AIza[0-9A-Za-z_\-]{30,}|AQ\.Ab[0-9A-Za-z_\-]{20,}|sk-[A-Za-z0-9]{30,}")
        malos = [str(p.relative_to(RAIZ)) for p in archivos((".py", ".md", ".example", ".bat", ".json", ".html", ".tsx", ".ts"))
                 if patron.search(leer(p)) and "package-lock" not in p.name]
        # los .env.example también
        for ej in (RAIZ / ".env.example", RAIZ / "backend" / ".env.example"):
            if ej.exists() and patron.search(leer(ej)):
                malos.append(str(ej.relative_to(RAIZ)))
        self.assertEqual(malos, [], "Hay claves de API reales en archivos que se comparten")

    def test_gitignore_protege_el_env(self):
        lineas = [l.strip() for l in leer(RAIZ / ".gitignore").splitlines()]
        self.assertIn(".env", lineas)

    def test_dockerignore_protege_el_env_y_los_backups(self):
        lineas = [l.strip() for l in leer(RAIZ / ".dockerignore").splitlines()]
        self.assertIn(".env", lineas)
        self.assertIn("**/.env", lineas)
        self.assertIn("backups", lineas)

    def test_database_exige_variable_de_entorno(self):
        src = leer(RAIZ / "backend" / "database.py")
        self.assertIn('os.getenv("DATABASE_URL"', src)
        self.assertNotIn("postgresql://", src.replace("postgresql://usuario:clave@localhost:5432/gastro_ia", ""))


class InyeccionSQL(unittest.TestCase):
    def test_tc032_sql_sin_interpolar_variables(self):
        """Las consultas deben usar parámetros (:nombre), no f-strings con variables."""
        malos = []
        for p in (RAIZ / "backend").glob("*.py"):
            for n, linea in enumerate(leer(p).splitlines(), 1):
                if re.search(r"(query\s*\+?=\s*f[\"']|text\(\s*f[\"']|execute\(\s*f[\"'])", linea):
                    malos.append("%s:%d %s" % (p.name, n, linea.strip()[:70]))
                if re.search(r"LIMIT\s*\{", linea):
                    malos.append("%s:%d LIMIT interpolado" % (p.name, n))
        self.assertEqual(malos, [])

    def test_limite_malicioso_se_neutraliza(self):
        for ataque in ("1; DROP TABLE restaurants; --", "1 OR 1=1", "-1", 10 ** 9, "∞", [1], {"a": 1}):
            self.assertIn(diseno.normalizar_limite(ataque), range(1, 26), ataque)


class DescargasSeguras(unittest.TestCase):
    """Hallazgo: /api/downloads permitía leer archivos fuera de analytics (path traversal)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        raiz = Path(self.tmp.name)
        (raiz / "analytics" / "csv").mkdir(parents=True)
        (raiz / "analytics" / "csv" / "datos.csv").write_text("a,b\n1,2\n")
        (raiz / "analytics" / "script.py").write_text("print('x')")
        (raiz / ".env").write_text("GEMINI_API_KEY=secreta")
        self.base = raiz / "analytics"

    def tearDown(self):
        self.tmp.cleanup()

    def test_archivo_valido(self):
        self.assertIsNotNone(diseno.resolver_descarga(self.base, "csv/datos.csv"))

    def test_tc028_path_traversal_bloqueado(self):
        for ruta in ("../.env", "../../.env", "csv/../../.env", "..\\.env", "/etc/passwd",
                     "C:\\Windows\\win.ini", "csv/../../../etc/passwd", "ni\x00ho.csv"):
            self.assertIsNone(diseno.resolver_descarga(self.base, ruta), ruta)

    def test_extension_no_permitida(self):
        self.assertIsNone(diseno.resolver_descarga(self.base, "script.py"))

    def test_el_endpoint_usa_la_funcion_segura(self):
        self.assertIn("diseno.resolver_descarga", leer(RAIZ / "backend" / "main.py"))


class ConfiguracionSegura(unittest.TestCase):
    def setUp(self):
        self.main = leer(RAIZ / "backend" / "main.py")

    def test_cors_sin_comodines(self):
        self.assertNotIn('allow_origins=["*"]', self.main)
        self.assertNotIn('allow_methods=["*"]', self.main)
        self.assertIn("allow_credentials=False", self.main)

    def test_errores_sin_detalles_internos(self):
        malos = []
        for p in (RAIZ / "backend").glob("*.py"):
            for n, l in enumerate(leer(p).splitlines(), 1):
                if re.search(r'return\s*\{["\']error["\']:\s*str\(e\)|return f["\']Error[^"\']*\{(str\()?e', l) \
                        or '"database": str(e)' in l:
                    malos.append("%s:%d" % (p.name, n))
        self.assertEqual(malos, [], "Se devuelven mensajes de excepción al cliente")

    def test_chat_tiene_rate_limit_y_validacion_de_sesion(self):
        self.assertIn("limitar_chat", self.main)
        self.assertIn("sesion_valida", self.main)

    def test_no_se_expone_el_servidor_a_la_red(self):
        src = leer(RAIZ / "run_backend.py")
        self.assertNotIn("0.0.0.0", src)

    def test_frontend_sin_html_crudo(self):
        for p in archivos((".tsx", ".ts"), RAIZ / "frontend" / "src"):
            s = leer(p)
            self.assertNotIn("dangerouslySetInnerHTML", s, p.name)
            self.assertNotIn("rehype-raw", s, p.name)

    def test_frontend_con_csp_y_hsts(self):
        """Si un XSS llegara a ejecutarse, la CSP limita a donde puede mandar el token."""
        v = leer(RAIZ / "frontend" / "vercel.json")
        self.assertIn("Content-Security-Policy", v)
        self.assertIn("Strict-Transport-Security", v)
        self.assertIn("frame-ancestors 'none'", v)
        self.assertNotIn("'unsafe-eval'", v)


if __name__ == "__main__":
    unittest.main()
