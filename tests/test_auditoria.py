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


class ClasificacionNpm(unittest.TestCase):
    """npm audit: FALLA solo si lo vulnerable se publica; el build queda como advertencia."""

    def _datos(self, *nombres, severidad="high", total=None):
        return {"vulnerabilities": {n: {"severity": severidad} for n in nombres},
                "metadata": {"vulnerabilities": {"high": len(nombres), "critical": 0,
                                                 "total": len(nombres) if total is None else total}}}

    def test_falla_con_vulnerabilidades_de_produccion(self):
        estado, _ = auditar.clasificar_auditoria_npm(self._datos("vite"), self._datos("vite"))
        self.assertEqual(estado, auditar.FALLA)

    def test_solo_desarrollo_queda_como_advertencia(self):
        estado, detalle = auditar.clasificar_auditoria_npm(self._datos("vite", "picomatch"), self._datos())
        self.assertEqual(estado, auditar.ADV)
        self.assertIn("desarrollo", detalle)
        self.assertIn("picomatch", detalle)

    def test_sin_vulnerabilidades(self):
        vacio = {"vulnerabilities": {}, "metadata": {"vulnerabilities": {"total": 0}}}
        self.assertEqual(auditar.clasificar_auditoria_npm(vacio, vacio)[0], auditar.OK)


if __name__ == "__main__":
    unittest.main()
