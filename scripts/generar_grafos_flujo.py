#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dibuja los grafos de flujo de docs/pruebas/caja_blanca.md y comprueba que V(G) = A - N + 2 = D + 1.
Requiere matplotlib (solo para este script):  pip install matplotlib
    python scripts/generar_grafos_flujo.py
"""
import os
import sys
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SALIDA = os.path.join(os.path.dirname(__file__), "..", "docs", "pruebas", "img")

# nombre -> (nodos {id: (x, y, etiqueta, es_decision)}, aristas [(origen, destino, etiqueta)], V(G) esperado)
GRAFOS = {
    "normalizar_limite": (
        {1: (2, 4, "1", True), 2: (1, 2.6, "2", False), 3: (3, 2.6, "3", False), 4: (2, 1, "4\nfin", False)},
        [(1, 2, "falla"), (1, 3, "ok"), (2, 4, ""), (3, 4, "")],
        2,
        "1: try n = int(float(valor)) - 2: return por_defecto - 3: return max(1, min(n, maximo)) - 4: fin",
    ),
    "validar_parametros": (
        {1: (3, 9, "1", True), 2: (2, 7.6, "2", False), 3: (4, 7.6, "3", False), 4: (3, 6.2, "4", True),
         5: (1.2, 4.6, "5", True), 6: (0, 2.6, "6", False), 7: (3.6, 4.6, "7", True), 8: (4.6, 3.0, "8", True),
         9: (5.6, 1.6, "9", False), 10: (2.6, 0.8, "10", False), 11: (2, -0.6, "11\nfin", False)},
        [(1, 2, "sí"), (1, 3, "no"), (2, 4, ""), (3, 4, ""), (4, 5, "prov"), (4, 7, "sin prov"), (5, 6, "no cubierta"),
         (5, 7, "cubierta"), (6, 11, ""), (7, 8, "ciudad"), (7, 10, "sin ciudad"), (8, 9, "fuera"), (8, 10, "cubierta"),
         (9, 11, ""), (10, 11, "")],
        6,
        "1: parametros or {} - 2: p = parametros - 3: p = {} - 4: prov - 5: provincia de otro país - 6: return False - "
        "7: ciudad - 8: ciudad de otro país - 9: return False - 10: return True - 11: fin",
    ),
    "resolver_descarga": (
        {1: (3, 8, "1", True), 2: (1, 6.4, "2", False), 3: (4.4, 6.4, "3", True), 4: (2.4, 4.8, "4", False),
         5: (5.4, 4.8, "5", True), 6: (5.4, 3.2, "6", True), 7: (3.6, 2.0, "7", False), 8: (7.2, 2.0, "8", False),
         9: (4.4, 0.2, "9\nfin", False)},
        [(1, 2, "error"), (1, 3, "ok"), (2, 9, ""), (3, 4, "fuera"), (3, 5, "dentro"), (4, 9, ""), (5, 7, "ext. no"),
         (5, 6, "ext. ok"), (6, 7, "no existe"), (6, 8, "existe"), (7, 9, ""), (8, 9, "")],
        5,
        "1: resolver rutas - 2: return None - 3: ¿dentro de base? - 4: return None - 5: ¿extensión permitida? - "
        "6: ¿es archivo? - 7: return None - 8: return destino - 9: fin",
    ),
}


def dibujar(nombre, nodos, aristas, v_esperado, leyenda):
    n, a = len(nodos), len(aristas)
    d = sum(1 for x in nodos.values() if x[3])
    assert a - n + 2 == v_esperado, "%s: A-N+2 = %d (esperado %d)" % (nombre, a - n + 2, v_esperado)
    assert d + 1 == v_esperado, "%s: D+1 = %d (esperado %d)" % (nombre, d + 1, v_esperado)
    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    for o, dest, et in aristas:
        x1, y1 = nodos[o][:2]
        x2, y2 = nodos[dest][:2]
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", color="#1F4E79", lw=1.3, shrinkA=14, shrinkB=14))
        if et:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2, et, fontsize=7.5, color="#555555", ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none"))
    for x, y, et, dec in nodos.values():
        ax.scatter([x], [y], s=900, c="#F8D7A8" if dec else "#DCE6F2", edgecolors="#1F4E79", zorder=3)
        ax.text(x, y, et, ha="center", va="center", fontsize=9, fontweight="bold", zorder=4)
    ax.set_title("%s  |  N = %d, A = %d, D = %d  ->  V(G) = %d" % (nombre, n, a, d, v_esperado), fontsize=10)
    ax.text(0.5, -0.02, "\n".join(textwrap.wrap(leyenda, 95)), transform=ax.transAxes, ha="center", va="top", fontsize=7, color="#444444")
    ax.text(0.99, 0.99, "naranja = nodo de decisión", transform=ax.transAxes, ha="right", va="top", fontsize=7.5, color="#B36B00")
    ax.axis("off")
    ax.margins(0.12)
    os.makedirs(SALIDA, exist_ok=True)
    fig.savefig(os.path.join(SALIDA, "grafo_%s.png" % nombre), dpi=130, bbox_inches="tight")
    plt.close(fig)
    print("OK %-20s N=%d A=%d D=%d V(G)=%d" % (nombre, n, a, d, v_esperado))


if __name__ == "__main__":
    for nombre, (nodos, aristas, v, leyenda) in GRAFOS.items():
        dibujar(nombre, nodos, aristas, v, leyenda)
    sys.exit(0)
