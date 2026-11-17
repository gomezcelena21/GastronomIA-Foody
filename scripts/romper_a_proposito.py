#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROMPER A PROPÓSITO (prueba de las pruebas) - apunte de la unidad 7, regla de oro 4.

Idea: una prueba que pasa no demuestra que sirva. Para saber si las pruebas realmente controlan el código,
se introduce un error a propósito en una COPIA temporal (nunca en tu código), se corren las pruebas y se
comprueba que alguna falle. Si ninguna falla, el defecto "sobrevive" y falta una prueba.

    python scripts/romper_a_proposito.py            # muestra la tabla
    python scripts/romper_a_proposito.py --informe  # además escribe docs/pruebas/romper_a_proposito.md
"""
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULOS = ["tests.test_diseno", "tests.test_casos_uso_ia", "tests.test_caja_blanca", "tests.test_caja_negra",
           "tests.test_modo_sin_ia", "tests.test_comercios", "tests.test_evaluacion_interprete"]

# (id, qué se rompe, texto original en backend/diseno.py, texto con el error)
MUTACIONES = [
    ("M1", "El mínimo de resultados pasa de 1 a 0 (valor límite)",
     "return max(1, min(n, maximo))", "return max(0, min(n, maximo))"),
    ("M2", "Se quita el control de que la descarga quede dentro de la carpeta permitida (BUG-01)",
     "if not destino.is_relative_to(base_real):", "if False:"),
    ("M3", "Se invierte la validación de provincia (acepta las de afuera)",
     "if prov and not any(x in prov for x in _PROVINCIAS_OK):", "if prov and any(x in prov for x in _PROVINCIAS_OK):"),
    ("M4", "Error de uno en el limitador: deja pasar un mensaje de más (> en vez de >=)",
     "if len(d) >= self.max_eventos:", "if len(d) > self.max_eventos:"),
    ("M5", "El mensaje ya no se recorta a 1.500 caracteres",
     "return limpio[:maximo]", "return limpio"),
    ("M6", "El modo sin IA afloja también la restricción sin TACC al no encontrar resultados",
     "p2 = {k: v for k, v in params.items() if k != quitar}",
     "p2 = {k: v for k, v in params.items() if k != quitar and k not in _CLAVES_DIETA}"),
    ("M7", "El seguimiento deja de retomar la zona de la consulta anterior",
     'if "ciudad" not in nuevo and "zona_sin_datos" not in nuevo and "ciudad" in base:', "if False:"),
    ("M8", "Se cambia la advertencia alimentaria (ya no pide confirmar con el local)",
     "Confirmá con el local antes de ir.", "Andá tranquilo."),
    ("M9", "Los datos de comercios ya no se limpian de < y > antes de dárselos a la IA",
     '_RE_LIMPIEZA_IA = re.compile(r"[`<>]")', '_RE_LIMPIEZA_IA = re.compile(r"[`]")'),
    ("M10", "«Lanús» deja de entenderse como «Lanús Oeste» (zona con datos)",
     "if cercano:", "if False:"),
    ("M11", "Un partido de GBA sin datos deja de reconocerse (se ignora la zona)",
     "p[\"zona_sin_datos\"] = partido", "pass"),
    ("M12", "El detector de órdenes para la IA deja de reconocer «ignorá las instrucciones»",
     'r"\\b(ignor\\w*|olvid\\w*|omit\\w*|desobedec\\w*|anul\\w*|reemplaz\\w*)\\b', 'r"\\b(xxignor\\w*|xxolvid\\w*|xxomit\\w*|xxdesobedec\\w*|xxanul\\w*|xxreemplaz\\w*)\\b'),
]


def correr(carpeta):
    r = subprocess.run([sys.executable, "-m", "unittest", *MODULOS], cwd=carpeta, capture_output=True, text=True)
    salida = r.stderr + r.stdout
    fallos = re.search(r"FAILED \((?:failures=(\d+))?(?:, )?(?:errors=(\d+))?", salida)
    n = sum(int(x) for x in fallos.groups() if x) if fallos else 0
    return r.returncode == 0, n, salida


def main():
    resultados = []
    with tempfile.TemporaryDirectory() as tmp:
        for carpeta in ("backend", "tests"):
            shutil.copytree(os.path.join(RAIZ, carpeta), os.path.join(tmp, carpeta),
                            ignore=shutil.ignore_patterns("__pycache__", ".env*"))
        ruta = os.path.join(tmp, "backend", "diseno.py")
        with open(ruta, encoding="utf-8") as f:
            original = f.read()
        ok, _, salida = correr(tmp)
        if not ok:
            print("Las pruebas no pasan ni siquiera sin romper nada. Arreglalas primero.\n", salida[-1500:])
            return 1
        for id_, que, viejo, nuevo in MUTACIONES:
            if original.count(viejo) != 1:
                resultados.append((id_, que, "NO APLICA (el código cambió)", 0))
                continue
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(original.replace(viejo, nuevo))
            ok, n, _ = correr(tmp)
            resultados.append((id_, que, "SOBREVIVIÓ (falta una prueba)" if ok else "DETECTADO", n))
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(original)
    detectados = sum(1 for r in resultados if r[2] == "DETECTADO")
    print("%-4s %-92s %-30s %s" % ("ID", "Error introducido", "Resultado", "Pruebas que fallaron"))
    for id_, que, res, n in resultados:
        print("%-4s %-92s %-30s %s" % (id_, que[:92], res, n))
    print("\nDetectados: %d de %d" % (detectados, len(resultados)))
    if "--informe" in sys.argv:
        lineas = ["# Romper a propósito (prueba de las pruebas)", "",
                  "Ejecutado el %s con Python %s por `python scripts/romper_a_proposito.py --informe`." % (date.today().isoformat(), platform.python_version()), "",
                  "Se introduce un error a propósito en una **copia temporal** de `backend/diseno.py` (tu código no se toca) y se corren las "
                  "pruebas (%s). Si alguna falla, el error fue **detectado**; si todas pasan, **sobrevivió** y falta una prueba." % ", ".join(m.split(".")[-1] for m in MODULOS), "",
                  "**Resultado: %d de %d errores detectados.**" % (detectados, len(resultados)), "",
                  "| ID | Error introducido | Resultado | Pruebas que fallaron |", "|---|---|---|---|"]
        for id_, que, res, n in resultados:
            lineas.append("| %s | %s | %s | %s |" % (id_, que, res, n))
        lineas += ["", "Es la regla de oro 4 del apunte de la unidad 7: *verificá que la prueba pueda fallar*."]
        destino = os.path.join(RAIZ, "docs", "pruebas", "romper_a_proposito.md")
        with open(destino, "w", encoding="utf-8") as f:
            f.write("\n".join(lineas) + "\n")
        print("Informe escrito en", destino)
    return 0 if detectados == len(resultados) else 2


if __name__ == "__main__":
    sys.exit(main())
