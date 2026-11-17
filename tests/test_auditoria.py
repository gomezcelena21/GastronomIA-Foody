"""La auditoría automática también se prueba: debe poder correr y no encontrar fallas de diseño ni de documentación."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "auditoria"))
import auditar  # noqa: E402


class Auditoria(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # sin ejecutar las pruebas (evita recursión) y sin escribir archivos
        cls.checks, cls.cuenta = auditar.auditar(ejecutar_tests=False, escribir=False, silencioso=True)

    def test_el_diseno_del_pdf_esta_implementado(self):
        malos = [c.id + ": " + c.detalle for c in self.checks if c.seccion.startswith("1.") and c.estado == auditar.FALLA]
        self.assertEqual(malos, [])

    def test_las_16_historias_estan_auditadas(self):
        ids = [c.id for c in self.checks if c.id.startswith("HU-")]
        self.assertEqual(ids, ["HU-%02d" % i for i in range(1, 17)])
        self.assertEqual(next(c for c in self.checks if c.id == "HU-15").estado, auditar.NOIMPL)

    def test_la_documentacion_vigente_no_miente(self):
        malos = [c.id + ": " + c.detalle for c in self.checks if c.seccion.startswith("6.") and c.estado == auditar.FALLA]
        self.assertEqual(malos, [])

    def test_la_auditoria_detecta_lo_que_falta(self):
        """Prueba del detector: si una historia exige un endpoint que no existe, la auditoría tiene que marcar FALLA."""
        original = auditar.HU
        try:
            auditar.HU = [("HU-99", "inventada", [("ep", "GET", "/api/no-existe")], [], None)]
            marcado = auditar.auditar_historias(None)[0]
        finally:
            auditar.HU = original
        self.assertEqual(marcado.estado, auditar.FALLA)
        self.assertIn("/api/no-existe", marcado.detalle)
        self.assertEqual([x for x in auditar.ENDPOINTS_PDF if x not in auditar.endpoints()], [])

    def test_lee_la_planilla_de_casos(self):
        filas = auditar.leer_xlsx(auditar.EXCEL)
        self.assertEqual(filas[0][1], "ID Caso")
        self.assertGreaterEqual(len(filas), 40)


if __name__ == "__main__":
    unittest.main()
