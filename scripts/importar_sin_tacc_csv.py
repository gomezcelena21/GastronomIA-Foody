#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Importa el resultado de la verificación sin TACC hecha por el equipo.

Uso:
    python scripts/importar_sin_tacc_csv.py data/reporte_sin_tacc.csv --dry-run
    python scripts/importar_sin_tacc_csv.py verificados.csv

Columnas del CSV (encabezado obligatorio):
    restaurant_id     obligatorio
    sin_tacc          si | no | opciones | sin_dato
    celiac_certified  si | no (opcional)
    confidence_level  official | community | no_verified (opcional; por defecto community)
    fuente            texto libre, ej.: "Llamado telefónico 2026-11-10"
    fecha             AAAA-MM-DD (opcional; por defecto hoy)

Solo se actualizan los datos de restaurant_features. No se toca el resto del
local. Si el local no tenía fila de características, se crea.
"""

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

from _db import booleano, conectar, texto

VALIDOS = {"official", "public_source", "community", "inferred", "no_verified", "declarado_comercio"}


def estado_sin_tacc(valor):
    v = texto(valor).lower()
    if v in ("si", "sí", "s", "opciones", "apto", "apta", "true", "1"):
        return True
    if v in ("no", "false", "0"):
        return False
    return None


def obtener_fuente(cur, nombre: str) -> int:
    nombre = nombre or "Verificación manual sin TACC"
    cur.execute(
        "SELECT source_id FROM sources WHERE source_type = 'verificacion_manual' AND name = %s LIMIT 1",
        (nombre,),
    )
    fila = cur.fetchone()
    if fila:
        return fila[0]
    cur.execute(
        """
        INSERT INTO sources (name, url, source_type, license, update_frequency,
                             last_updated, reliability, notes, fetched_date)
        VALUES (%s, NULL, 'verificacion_manual', 'Datos verificados por el equipo',
                'manual', CURRENT_DATE, 'community',
                'Verificación directa con el comercio. Confirmar nuevamente si cambia la carta.', CURRENT_DATE)
        RETURNING source_id
        """,
        (nombre,),
    )
    return cur.fetchone()[0]


def leer(ruta: Path):
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        if not lector.fieldnames or "restaurant_id" not in lector.fieldnames:
            sys.exit("El CSV debe tener la columna restaurant_id.")
        for n, fila in enumerate(lector, start=2):
            yield n, fila


def main() -> int:
    p = argparse.ArgumentParser(description="Importa verificaciones sin TACC desde CSV.")
    p.add_argument("csv", help="Ruta del CSV.")
    p.add_argument("--dry-run", action="store_true", help="Valida y muestra el resumen sin escribir.")
    args = p.parse_args()

    ruta = Path(args.csv)
    if not ruta.exists():
        sys.exit("No existe el archivo: %s" % ruta)

    conn = conectar()
    validos, errores = [], []
    omitidos = 0
    try:
        with conn.cursor() as cur:
            for n, fila in leer(ruta):
                rid_txt = texto(fila.get("restaurant_id"), 20)
                if not rid_txt.isdigit():
                    errores.append("línea %d: restaurant_id inválido" % n)
                    continue
                rid = int(rid_txt)
                cur.execute("SELECT 1 FROM restaurants WHERE restaurant_id = %s", (rid,))
                if not cur.fetchone():
                    errores.append("línea %d: no existe restaurant_id %s" % (n, rid))
                    continue

                sin_tacc = estado_sin_tacc(fila.get("sin_tacc"))
                celiaco = booleano(fila.get("celiac_certified"))
                crudo = texto(fila.get("sin_tacc")).lower()
                # El reporte generado trae miles de filas "sin_dato": se omiten
                # sin ruido, porque no hay nada que actualizar todavía.
                if sin_tacc is None and celiaco is None and crudo in (
                        "", "sin_dato", "sin dato", "sin datos", "?", "n/d", "nd"):
                    omitidos += 1
                    continue
                if sin_tacc is None and celiaco is None:
                    errores.append("línea %d: sin_tacc/celiac_certified inválidos" % n)
                    continue
                confianza = texto(fila.get("confidence_level"), 30) or "community"
                if confianza not in VALIDOS:
                    confianza = "community"
                validos.append((n, rid, sin_tacc, celiaco, confianza,
                                texto(fila.get("fuente"), 200),
                                texto(fila.get("fecha"), 10) or date.today().isoformat()))

        if errores:
            print("Filas con problemas (%d):" % len(errores))
            for e in errores[:30]:
                print("  - " + e)
            if not validos:
                return 1

        print("Filas válidas: %d (omitidas sin dato: %d)" % (len(validos), omitidos))
        if args.dry_run:
            for n, rid, sin_tacc, celiaco, confianza, fuente, fecha in validos[:20]:
                print("  línea %d: #%s sin_tacc=%s certificado=%s confianza=%s" % (
                    n, rid, sin_tacc, celiaco, confianza))
            print("\nDry-run: no se escribió nada en la base.")
            return 0

        actualizados = insertados = 0
        with conn.cursor() as cur:
            for n, rid, sin_tacc, celiaco, confianza, fuente, fecha in validos:
                sid = obtener_fuente(cur, fuente)
                cur.execute(
                    "SELECT id FROM restaurant_features WHERE restaurant_id = %s ORDER BY id LIMIT 1",
                    (rid,),
                )
                fila = cur.fetchone()
                if fila:
                    cur.execute(
                        """
                        UPDATE restaurant_features
                        SET has_gluten_free_options = COALESCE(%s, has_gluten_free_options),
                            celiac_certified = COALESCE(%s, celiac_certified),
                            confidence_level = %s,
                            source_id = %s
                        WHERE id = %s
                        """,
                        (sin_tacc, celiaco, confianza, sid, fila[0]),
                    )
                    actualizados += 1
                else:
                    cur.execute(
                        """
                        INSERT INTO restaurant_features (restaurant_id, has_gluten_free_options,
                                                         celiac_certified, source_id, confidence_level)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (rid, sin_tacc, celiaco if celiaco is not None else False, sid, confianza),
                    )
                    insertados += 1
            conn.commit()
        print("Actualizados %d locales; creados %d registros de características." % (actualizados, insertados))
        if errores:
            print("Se omitieron %d filas con problemas (ver arriba)." % len(errores))
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
