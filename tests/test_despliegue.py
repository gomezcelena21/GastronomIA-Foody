"""
Controles estáticos del despliegue (no necesitan FastAPI ni PostgreSQL):
- /ping existe y NO toca la base (mantiene despierto el servidor sin gastar horas de la base gratis).
- El puerto 8000 del backend no se publica al exterior en el compose principal.
- El healthcheck del Dockerfile respeta la variable PORT (Render la define).
- El script de carga a la nube no borra datos sin confirmación.
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def leer(ruta: str) -> str:
    return (RAIZ / ruta).read_text(encoding="utf-8")


class Despliegue(unittest.TestCase):
    def test_tc046_ping_existe_y_no_usa_la_base(self):
        main = leer("backend/main.py")
        m = re.search(r'@app\.api_route\("/ping".*?\)\ndef ping\((.*?)\):(.*?)(?=\n\n\n@app|\Z)', main, re.S)
        self.assertIsNotNone(m, "falta el endpoint /ping")
        firma, cuerpo = m.group(1), m.group(2)
        self.assertEqual(firma.strip(), "", "/ping no debe recibir dependencias (ni la base)")
        self.assertNotIn("get_db", cuerpo)
        self.assertNotIn("execute", cuerpo)
        self.assertIn('"HEAD"', main.split("def ping")[0].split("@app.api_route")[-1])

    def test_tc045_el_backend_no_publica_el_puerto_8000(self):
        compose = leer("docker-compose.yml")
        bloque = compose.split("  backend:")[1].split("\n  caddy:")[0]
        self.assertNotRegex(bloque, r'\n\s+ports:', "el backend no debe publicar puertos en el compose principal")
        override = leer("docker-compose.override.yml")
        self.assertIn("127.0.0.1:8000:8000", override)

    def test_healthcheck_usa_port_y_ping(self):
        docker = leer("Dockerfile")
        self.assertIn("${PORT:-8000}", docker)
        self.assertIn("/ping", docker)

    def test_el_backend_solo_confia_en_el_proxy_interno(self):
        compose = leer("docker-compose.yml")
        self.assertIn("FORWARDED_ALLOW_IPS", compose)
        self.assertIn("subnet: 172.28.0.0/16", compose)
        self.assertNotIn('FORWARDED_ALLOW_IPS: "*"', compose)

    def test_el_entrypoint_no_confia_en_cualquier_proxy_por_defecto(self):
        """Con '*' cualquiera inventa su IP en X-Forwarded-For y se saltea el cupo de invitados."""
        entrada = leer("deploy/entrypoint.sh")
        self.assertNotIn("FORWARDED_ALLOW_IPS:-*", entrada)
        self.assertIn("10.0.0.0/8", entrada)

    def test_carga_a_la_nube_pide_confirmacion_y_protege_los_datos(self):
        s = leer("scripts/cargar_base_nube.py")
        self.assertIn("Escribí SI", s)
        self.assertIn("--forzar", s)
        self.assertNotIn("password", s.lower().replace("clave", ""))  # nunca imprime ni guarda la clave

    def test_la_guia_gratis_existe_y_no_trae_claves(self):
        candidatos = [
            RAIZ / "deploy" / "GUIA_GRATIS_VERCEL_RENDER_NEON.md",
            RAIZ.parent / "GUIA_GRATIS_VERCEL_RENDER_NEON.md",
            RAIZ.parent / "Entregables para subir aparte" / "GUIA_GRATIS_VERCEL_RENDER_NEON.md",
            RAIZ.parent / "Archivos no versionados" / "GUIA_GRATIS_VERCEL_RENDER_NEON.md",
        ]
        guia = None
        for p in candidatos:
            if p.exists():
                guia = p.read_text(encoding="utf-8")
                break
        if guia is None:
            self.skipTest("Guía de despliegue movida fuera del repositorio para entrega separada")
        self.assertIn("/ping", guia)
        self.assertNotRegex(guia, r"AIza[0-9A-Za-z_-]{20,}")


if __name__ == "__main__":
    unittest.main()
