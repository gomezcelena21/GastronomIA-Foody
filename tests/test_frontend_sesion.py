"""
Controles estáticos del acceso en el frontend (no necesitan Node ni navegador): la sesión de Google se recuerda y quien ya
inició sesión entra directo al chat. El comportamiento real lo cubren las pruebas E2E de Playwright
(frontend/e2e/app.spec.ts, bloque «Sesión recordada»), que se corren en la PC del proyecto con `npm run test:e2e`.
    python -m unittest tests.test_frontend_sesion -v
"""
import re
import unittest
from pathlib import Path

FRONT = Path(__file__).resolve().parent.parent / "frontend"


def leer(ruta: str) -> str:
    return (FRONT / ruta).read_text(encoding="utf-8")


class SesionRecordada(unittest.TestCase):
    def test_tc063_la_sesion_se_guarda_en_localstorage_y_se_borra_al_cerrar_sesion(self):
        auth = leer("src/auth.ts")
        self.assertIn("localStorage.setItem(KT, token)", auth)
        self.assertIn("localStorage.setItem(KU, JSON.stringify(u))", auth)
        cerrar = auth[auth.index("export const cerrarSesion"):]
        self.assertIn("localStorage.removeItem(k)", cerrar.split("\n\n")[0])
        self.assertIn("sesionVigente", auth)             # el vencimiento se comprueba antes de reutilizar el token

    def test_tc063_la_app_restaura_la_sesion_valida_el_token_y_no_pregunta_el_rol(self):
        app = leer("src/App.tsx")
        self.assertRegex(app, r"sesionVigente\(\)\s*&&\s*!!getUser\(\)")
        self.assertIn("/api/auth/me", app)                # el servidor confirma que el token sirve
        self.assertIn("r.status === 401", app)            # si lo rechaza, se vuelve al inicio de sesión
        self.assertNotIn("<ElegirRol", app)               # ya no se manda a elegir usuario o comercio
        self.assertIn("getRol() ?? 'usuario'", app)

    def test_tc064_el_comercio_se_maneja_desde_el_perfil(self):
        app = leer("src/App.tsx")
        for texto in ("Mi comercio", "Registrar mi comercio", "Ir a mi comercio", "onRol('comercio')", "onRol('admin')"):
            self.assertIn(texto, app)
        # el botón «Quiero sumarme» de la landing lleva al Perfil (donde está «Mi comercio»)
        self.assertTrue(re.search(r'href="/perfil".{0,120}ir\(\'perfil\'\).{0,40}Quiero sumarme', leer("src/Landing.tsx"), re.S))

    def test_el_invitado_sigue_sin_persistir(self):
        auth = leer("src/auth.ts")
        self.assertIn("sessionStorage.setItem(KI, '1')", auth)

    def test_las_pruebas_e2e_cubren_la_sesion_recordada(self):
        e2e = leer("e2e/app.spec.ts")
        for nombre in ("entra directo al chat", "si la sesión venció", "401", "cerrar sesión borra"):
            self.assertIn(nombre, e2e)
        self.assertEqual(len(re.findall(r"Sesión recordada", e2e)), 1)


if __name__ == "__main__":
    unittest.main()
