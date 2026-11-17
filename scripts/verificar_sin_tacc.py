#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reporte de verificación sin TACC.

Genera un CSV con todos los locales y el estado del dato sin TACC para que el
equipo pueda llamarlos y confirmar. No inventa datos: solo refleja lo que hay
en la base.

Uso:
    python scripts/verificar_sin_tacc.py
    python scripts/verificar_sin_tacc.py --solo-confirmados
    python scripts/verificar_sin_tacc.py --ciudad CABA --csv data/reporte_sin_tacc.csv

Estados:
    si               la fuente declara opciones sin TACC
    no               la fuente dice que no ofrece opciones sin TACC
    sin_dato         no hay información (hay que confirmar con el local)

Después de llamar a los locales, cargá el resultado con
scripts/importar_sin_tacc_csv.py usando la misma plantilla.
"""

import argparse
import csv
import sys
from pathlib import Path

from _db import RAIZ, conectar

CSV_DEFECTO = RAIZ / "data" / "reporte_sin_tacc.csv"


def estado(valor) -> str:
    if valor is True:
        return "si"
    if valor is False:
        return "no"
    return "sin_dato"


def main() -> int:
    p = argparse.ArgumentParser(description="Genera el reporte de estado sin TACC.")
    p.add_argument("--csv", default=str(CSV_DEFECTO), help="Archivo CSV de salida.")
    p.add_argument("--solo-confirmados", action="store_true", help="Solo locales con opciones sin TACC.")
    p.add_argument("--ciudad", default="", help="Filtra por ciudad (ej.: CABA).")
    p.add_argument("--dry-run", action="store_true", help="Muestra el resumen sin escribir el CSV.")
    args = p.parse_args()

    conn = conectar()
    sql = """
        SELECT r.restaurant_id, r.name, r.city, r.neighborhood, r.address,
               r.phone, r.website, rf.has_gluten_free_options,
               rf.celiac_certified, COALESCE(rf.confidence_level, 'no_verified'),
               COALESCE(s.name, ''), r.data_date
        FROM restaurants r
        LEFT JOIN LATERAL (
            SELECT * FROM restaurant_features rf0
            WHERE rf0.restaurant_id = r.restaurant_id
            ORDER BY rf0.id
            LIMIT 1
        ) rf ON TRUE
        LEFT JOIN sources s ON s.source_id = rf.source_id
        WHERE r.is_active IS NOT FALSE
    """
    params = []
    if args.ciudad:
        sql += " AND r.city ILIKE %s"
        params.append(args.ciudad)
    if args.solo_confirmados:
        sql += " AND rf.has_gluten_free_options IS TRUE"
    sql += " ORDER BY r.city, r.neighborhood NULLS LAST, r.name"

    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            filas = cur.fetchall()
    finally:
        conn.close()

    # celiac_certified tiene FALSE por defecto en la base: solo se informa "si"
    # cuando alguien lo confirmó. Un FALSE por defecto no es un "no" verificado.
    filas = [(f[0], f[1], f[2], f[3], f[4], f[5], f[6], estado(f[7]),
              "si" if f[8] is True else "sin_dato",
              f[9], f[10], f[11]) for f in filas]

    conteo = {"si": 0, "no": 0, "sin_dato": 0}
    for f in filas:
        conteo[f[7]] += 1
    certificados = sum(1 for f in filas if f[8] == "si")
    verificados = sum(1 for f in filas if f[9] in ("official", "community", "declarado_comercio"))

    print("Locales analizados: %d" % len(filas))
    print("  con opciones sin TACC declaradas: %d" % conteo["si"])
    print("  sin opciones sin TACC:            %d" % conteo["no"])
    print("  sin dato (confirmar con el local): %d" % conteo["sin_dato"])
    print("  certificados sin TACC:             %d" % certificados)
    print("  con confianza oficial/declarada:   %d" % verificados)

    if args.dry_run:
        print("\nDry-run: no se escribió el CSV.")
        return 0

    destino = Path(args.csv)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "restaurant_id", "nombre", "ciudad", "barrio", "direccion", "telefono",
            "website", "sin_tacc", "celiac_certified", "confidence_level",
            "fuente", "data_date",
        ])
        w.writerows(filas)

    print("\nReporte escrito en: %s" % destino)
    print("Para cargar lo que confirmes, usá: python scripts/importar_sin_tacc_csv.py %s" % destino)
    return 0


if __name__ == "__main__":
    sys.exit(main())
