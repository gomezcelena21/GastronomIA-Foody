"""
Pruebas del login con Google: sesión firmada y tope diario por usuario (sin internet, sin FastAPI).
    python -m unittest tests.test_sesion -v
"""
import os
import sys
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import sesion  # noqa: E402

SECRETO = "s" * 48
USUARIO = {"sub": "123", "email": "ana@example.com", "nombre": "Ana"}


class SesionFirmada(unittest.TestCase):
    def test_ida_y_vuelta(self):
        t = sesion.firmar_sesion(USUARIO, SECRETO)
        datos = sesion.verificar_sesion(t, SECRETO)
        self.assertEqual(datos["email"], "ana@example.com")

    def test_token_alterado_se_rechaza(self):
        p, f = sesion.firmar_sesion(USUARIO, SECRETO).split(".")
        falso = sesion._b64(b'{"sub":"999","email":"admin@example.com","nombre":"X","exp":9999999999}')
        with self.assertRaises(sesion.SesionInvalida):
            sesion.verificar_sesion(falso + "." + f, SECRETO)

    def test_otro_secreto_se_rechaza(self):
        t = sesion.firmar_sesion(USUARIO, SECRETO)
        with self.assertRaises(sesion.SesionInvalida):
            sesion.verificar_sesion(t, "otra" * 12)

    def test_sesion_vencida(self):
        t = sesion.firmar_sesion(USUARIO, SECRETO, ahora=1000.0, horas=1)
        with self.assertRaises(sesion.SesionInvalida):
            sesion.verificar_sesion(t, SECRETO, ahora=1000.0 + 3601)
        self.assertEqual(sesion.verificar_sesion(t, SECRETO, ahora=1000.0 + 3599)["sub"], "123")

    def test_basura_se_rechaza(self):
        for t in ("", "abc", "a.b.c", "....", None):
            with self.assertRaises(sesion.SesionInvalida):
                sesion.verificar_sesion(t, SECRETO)

    def test_secreto_corto_o_vacio_no_firma_ni_verifica(self):
        for s in ("", "corto"):
            with self.assertRaises(sesion.SesionInvalida):
                sesion.firmar_sesion(USUARIO, s)
            with self.assertRaises(sesion.SesionInvalida):
                sesion.verificar_sesion("a.b", s)

    def test_google_sin_client_id(self):
        with self.assertRaises(sesion.SesionInvalida):
            sesion.verificar_google("x" * 30, "")


class TopeDiario(unittest.TestCase):
    def test_limite_por_usuario(self):
        c = sesion.ContadorDiario(3)
        self.assertEqual([c.consumir("a") for _ in range(4)], [True, True, True, False])
        self.assertTrue(c.consumir("b"))          # otro usuario no se ve afectado
        self.assertEqual(c.restantes("a"), 0)

    def test_se_reinicia_al_cambiar_el_dia(self):
        dia = [date(2026, 11, 6)]
        c = sesion.ContadorDiario(1, hoy=lambda: dia[0])
        self.assertTrue(c.consumir("a"))
        self.assertFalse(c.consumir("a"))
        dia[0] += timedelta(days=1)
        self.assertTrue(c.consumir("a"))


if __name__ == "__main__":
    unittest.main()
