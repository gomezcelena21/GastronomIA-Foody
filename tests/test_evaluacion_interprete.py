"""
EVALUACIÓN DEL INTÉRPRETE LOCAL (modo sin IA) con un conjunto de ejemplos - ver docs/pruebas/evaluacion_interprete.md
Es la misma idea que evaluar un modelo de IA con ejemplos: una persona preparó la respuesta correcta de cada consulta
(a partir del REQUISITO: entender zona, tipo de comida y restricción) y se mide el porcentaje de aciertos.
No se espera 100 %: se fija un mínimo aceptable (UMBRAL) y se documentan los fallos conocidos.

    python -m unittest tests.test_evaluacion_interprete -v
    python tests/test_evaluacion_interprete.py --escribir      # regenera docs/pruebas/evaluacion_interprete.md
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import diseno as d  # noqa: E402

UMBRAL = 0.85   # mínimo aceptable de aciertos exactos

# (categoría, consulta, ciudad, {cocinas}, {restricciones}, zona_sin_datos)
# restricciones: "sin_tacc", "vegano", "vegetariano"
E = [
    # --- consultas normales
    ("normal", "Restaurantes en Palermo", "Palermo", set(), set(), None),
    ("normal", "pizzería sin TACC en Palermo", "Palermo", {"pizzeria"}, {"sin_tacc"}, None),
    ("normal", "opciones veganas en Villa Crespo", "Villa Crespo", set(), {"vegano"}, None),
    ("normal", "comida vegetariana en Caballito", "Caballito", set(), {"vegetariano"}, None),
    ("normal", "sushi en Recoleta", "Recoleta", {"japonesa"}, set(), None),
    ("normal", "parrilla en Belgrano", "Belgrano", {"parrilla"}, set(), None),
    ("normal", "heladería en Núñez", "Núñez", {"heladeria"}, set(), None),
    ("normal", "comida china en Flores", "Flores", {"china"}, set(), None),
    ("normal", "empanadas en Almagro", "Almagro", {"empanadas"}, set(), None),
    ("normal", "café vegetariano en San Telmo", "San Telmo", {"cafe"}, {"vegetariano"}, None),
    # --- formas de escribir (mayúsculas, sin tildes, sinónimos)
    ("escritura", "SIN TACC EN CABALLITO", "Caballito", set(), {"sin_tacc"}, None),
    ("escritura", "pizzeria sin tacc en palermo", "Palermo", {"pizzeria"}, {"sin_tacc"}, None),
    ("escritura", "soy celíaco, busco algo en Belgrano", "Belgrano", set(), {"sin_tacc"}, None),
    ("escritura", "una panadería sin gluten en Boedo", "Boedo", {"panaderia"}, {"sin_tacc"}, None),
    ("escritura", "algo con asado por Villa Urquiza", "Villa Urquiza", {"parrilla"}, set(), None),
    ("escritura", "hamburguesas veganas en Palermo", "Palermo", {"hamburguesa"}, {"vegano"}, None),
    # --- combinadas (varias restricciones y cocinas)
    ("combinada", "pizzería vegana y sin TACC en Palermo", "Palermo", {"pizzeria"}, {"vegano", "sin_tacc"}, None),
    ("combinada", "café o pastelería sin gluten en Colegiales", "Colegiales", {"cafe", "pasteleria"}, {"sin_tacc"}, None),
    # --- ambiguas o sin datos (no debe inventar parámetros)
    ("ambigua", "tengo hambre", None, set(), set(), None),
    ("ambigua", "hola", None, set(), set(), None),
    ("ambigua", "asdf qwerty", None, set(), set(), None),
    ("ambigua", "", None, set(), set(), None),
    # --- cobertura nacional: capitales y ciudades del interior (la base cubre todo el país)
    ("nacional", "restaurante en Córdoba", "Córdoba", set(), set(), None),
    ("nacional", "pizzería en Rosario", "Rosario", {"pizzeria"}, set(), None),
    ("nacional", "algo sin TACC en Mar del Plata", "Mar del Plata", set(), {"sin_tacc"}, None),
    ("nacional", "restaurante en Mendoza", "Mendoza", set(), set(), None),
    # --- fuera del país (la base solo tiene datos de Argentina; hay que avisar y no consultar)
    ("fuera", "restaurante en Montevideo", "Montevideo", set(), set(), None),
    ("fuera", "pizzería en Madrid", "Madrid", {"pizzeria"}, set(), None),
    ("fuera", "algo sin TACC en Santiago de Chile", "Santiago de Chile", set(), {"sin_tacc"}, None),
    # --- equidad geográfica: GBA con locales en la base y partidos sin locales (hay que avisar, no ignorarlos)
    ("gba", "sushi en Lomas de Zamora", "Lomas de Zamora", {"japonesa"}, set(), None),
    ("gba", "milanesas en Avellaneda", "Avellaneda", set(), set(), None),
    ("gba", "algo vegano cerca de Lanús", "Lanús", set(), {"vegano"}, None),
    ("gba", "hamburguesas veganas en Tigre", "Tigre", {"hamburguesa"}, {"vegano"}, None),
    ("gba", "pizzería en Quilmes", "Quilmes", {"pizzeria"}, set(), None),
    ("gba", "comer en Morón sin TACC", "Morón", set(), {"sin_tacc"}, None),
    ("gba", "café en Béccar", "Béccar", {"cafe"}, set(), None),
    ("gba", "sushi en Hurlingham", "Hurlingham", {"japonesa"}, set(), None),
    ("gba", "pizzería en Cañuelas", "Cañuelas", {"pizzeria"}, set(), None),
    ("gba", "parrilla en Marcos Paz", "Marcos Paz", {"parrilla"}, set(), None),
    ("gba", "pizzería en Presidente Perón", None, {"pizzeria"}, set(), "Presidente Perón"),
    # --- casos difíciles que hoy NO se resuelven (errores de tipeo): quedan documentados como límite
    ("tipeo", "pizeria en palermo", "Palermo", {"pizzeria"}, set(), None),
    ("tipeo", "sin tak en belgrano", "Belgrano", set(), {"sin_tacc"}, None),
]


def interpretado(consulta):
    p = d.interpretar_consulta_local(consulta)
    dieta = {n for n, k in (("sin_tacc", "requiere_sin_tacc"), ("vegano", "requiere_vegano"),
                            ("vegetariano", "requiere_vegetariano")) if p.get(k)}
    return p.get("ciudad"), set(p.get("tipo_cocina", [])), dieta, p.get("zona_sin_datos")


def evaluar():
    """Devuelve (aciertos, total, detalle) donde detalle es [(categoría, consulta, ok, obtenido)]."""
    detalle, aciertos = [], 0
    for categoria, consulta, ciudad, cocinas, dieta, sin_datos in E:
        obtenido = interpretado(consulta)
        ok = obtenido == (ciudad, cocinas, dieta, sin_datos)
        aciertos += ok
        detalle.append((categoria, consulta, ok, obtenido))
    return aciertos, len(E), detalle


class EvaluacionDelInterprete(unittest.TestCase):
    def test_hay_suficientes_ejemplos_y_casos_dificiles(self):
        self.assertGreaterEqual(len(E), 20)
        categorias = {c[0] for c in E}
        self.assertTrue({"ambigua", "nacional", "fuera", "gba", "tipeo"} <= categorias)

    def test_tc054_porcentaje_de_aciertos_supera_el_minimo(self):
        aciertos, total, detalle = evaluar()
        fallos = ["%s: %r -> %r" % (c, q, o) for c, q, ok, o in detalle if not ok]
        self.assertGreaterEqual(aciertos / total, UMBRAL, "Aciertos %d/%d. Fallos: %s" % (aciertos, total, fallos))

    def test_las_consultas_normales_y_ambiguas_acierta_todas(self):
        # Lo básico no puede fallar: las categorías de uso habitual deben dar 100 %
        _, _, detalle = evaluar()
        malas = [q for c, q, ok, _ in detalle if c in ("normal", "ambigua", "nacional", "fuera", "gba") and not ok]
        self.assertEqual(malas, [])


def escribir_informe():
    aciertos, total, detalle = evaluar()
    por_cat = {}
    for c, _, ok, _ in detalle:
        a, t = por_cat.get(c, (0, 0))
        por_cat[c] = (a + ok, t + 1)
    f = ["# Evaluación del intérprete del modo sin IA", "",
         "Generado por `python tests/test_evaluacion_interprete.py --escribir`. Es el equivalente de evaluar un modelo con un conjunto de "
         "ejemplos: una persona preparó la respuesta correcta de cada consulta a partir del requisito (entender zona, tipo de comida y "
         "restricción) y se mide el porcentaje de aciertos exactos.", "",
         "**Resultado: %d de %d aciertos (%.0f %%). Mínimo aceptable: %.0f %%.**" % (aciertos, total, 100 * aciertos / total, 100 * UMBRAL), "",
         "| Categoría | Aciertos |", "|---|---|"]
    for c, (a, t) in por_cat.items():
        f.append("| %s | %d de %d |" % (c, a, t))
    f += ["", "## Detalle", "", "| Categoría | Consulta | Resultado | Obtenido (zona, cocinas, restricciones, zona sin datos) |", "|---|---|---|---|"]
    for c, q, ok, o in detalle:
        f.append("| %s | %s | %s | %s |" % (c, q or "(vacía)", "Acierta" if ok else "**Falla**", (o[0], sorted(o[1]), sorted(o[2]), o[3])))
    f += ["", "## Qué muestra", "",
          "- Las consultas normales, ambiguas, nacionales (interior del país), fuera de Argentina y de GBA se resuelven bien. "
          "Una consulta ambigua no inventa parámetros.",
          "- **Límite conocido (tipeo):** el intérprete trabaja por palabras clave y no corrige errores de escritura («pizeria», «sin tak»).",
          "- **Cobertura nacional:** con la base cargada (más de 71.000 lugares de todo el país) se reconocen %s barrios, localidades, "
          "ciudades y partidos. Para los partidos de GBA sin locales cargados (por ejemplo Presidente Perón) el sistema lo dice en lugar "
          "de mostrar locales de otra zona." % format(len(d.BARRIOS), ",").replace(",", "."),
          "- Cuando se cambia el intérprete, esta evaluación se vuelve a correr (es la prueba de regresión de la IA)."]
    ruta = os.path.join(os.path.dirname(__file__), "..", "docs", "pruebas", "evaluacion_interprete.md")
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write("\n".join(f) + "\n")
    print("Escrito", os.path.normpath(ruta), "(%d/%d)" % (aciertos, total))


if __name__ == "__main__":
    if "--escribir" in sys.argv:
        escribir_informe()
    else:
        unittest.main()
