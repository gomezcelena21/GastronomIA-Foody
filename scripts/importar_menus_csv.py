#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Importa menús y platos desde un CSV a las tablas menus y dish_features.

Uso:
    python scripts/importar_menus_csv.py data/plantillas/menus.csv --dry-run
    python scripts/importar_menus_csv.py data/plantillas/menus.csv
    python scripts/importar_menus_csv.py mi_menu.csv --reemplazar

Columnas del CSV (la primera fila es el encabezado):
    restaurant_id   obligatorio, debe existir en restaurants
    dish_name       obligatorio
    category        opcional (entrada, principal, postre, bebida...)
    description     opcional
    price           opcional; acepta 12500, 12.500,50 o $12.500
    currency        opcional; por defecto ARS
    ingredients     opcional; separados por | o ;
    gluten_free, vegetarian, vegan, lactose_free,
    contains_gluten, contains_lactose, contains_egg, contains_nuts
                    opcionales; si / no
    carbohydrates, sugars, fiber, proteins, fats, portion_size   opcionales
    confidence_level  opcional; por defecto community
    data_date         opcional; por defecto la fecha de hoy

Los datos quedan con la fuente "Carga manual de menús". Nada se publica como
garantía alimentaria: para celiaquía o alergias siempre hay que confirmar con el
local.
"""

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

from _db import booleano, conectar, decimal, texto

CAMPOS_BOOL = (
    "gluten_free", "vegetarian", "vegan", "lactose_free",
    "contains_gluten", "contains_lactose", "contains_egg", "contains_nuts",
)
CAMPOS_NUM = ("carbohydrates", "sugars", "fiber", "proteins", "fats")


def fuente_manual(cur) -> int:
    cur.execute("SELECT source_id FROM sources WHERE source_type = 'carga_manual' ORDER BY source_id LIMIT 1")
    fila = cur.fetchone()
    if fila:
        return fila[0]
    cur.execute(
        """
        INSERT INTO sources (name, url, source_type, license, update_frequency,
                             last_updated, reliability, notes, fetched_date)
        VALUES ('Carga manual de menús', NULL, 'carga_manual', 'Datos del comercio',
                'manual', CURRENT_DATE, 'community',
                'Menús cargados por el equipo o el comercio; verificar con el local.', CURRENT_DATE)
        RETURNING source_id
        """
    )
    return cur.fetchone()[0]


def leer_filas(ruta: Path):
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        if not lector.fieldnames:
            sys.exit("El CSV no tiene encabezado.")
        faltan = [c for c in ("restaurant_id", "dish_name") if c not in lector.fieldnames]
        if faltan:
            sys.exit("Faltan columnas obligatorias: %s" % ", ".join(faltan))
        for n, fila in enumerate(lector, start=2):
            yield n, fila


def main() -> int:
    p = argparse.ArgumentParser(description="Importa menús desde CSV a PostgreSQL.")
    p.add_argument("csv", help="Ruta del archivo CSV.")
    p.add_argument("--dry-run", action="store_true", help="Valida y muestra el resumen sin escribir.")
    p.add_argument("--reemplazar", action="store_true",
                   help="Borra los menús existentes de los restaurantes incluidos antes de importar.")
    args = p.parse_args()

    ruta = Path(args.csv)
    if not ruta.exists():
        sys.exit("No existe el archivo: %s" % ruta)

    conn = conectar()
    validos, errores = [], []
    ids_restaurantes = set()
    try:
        with conn.cursor() as cur:
            for n, fila in leer_filas(ruta):
                rid_txt = texto(fila.get("restaurant_id"), 20)
                nombre = texto(fila.get("dish_name"), 300)
                if not rid_txt.isdigit() or not nombre:
                    errores.append("línea %d: restaurant_id/dish_name inválidos" % n)
                    continue
                rid = int(rid_txt)
                cur.execute("SELECT 1 FROM restaurants WHERE restaurant_id = %s", (rid,))
                if not cur.fetchone():
                    errores.append("línea %d: no existe el restaurant_id %s" % (n, rid))
                    continue
                validos.append((n, rid, fila))
                ids_restaurantes.add(rid)

        if errores:
            print("Filas con problemas (%d):" % len(errores))
            for e in errores[:30]:
                print("  - " + e)
            if len(errores) > 30:
                print("  ... y %d más" % (len(errores) - 30))
            if not validos:
                return 1

        print("Filas válidas: %d para %d restaurantes." % (len(validos), len(ids_restaurantes)))
        if args.dry_run:
            for n, rid, fila in validos[:15]:
                print("  línea %d: #%s %s (%s) precio=%s" % (
                    n, rid, texto(fila.get("dish_name"), 80),
                    texto(fila.get("category"), 40) or "sin categoría",
                    texto(fila.get("price"), 20) or "sin precio"))
            print("\nDry-run: no se escribió nada en la base.")
            return 0

        with conn.cursor() as cur:
            sid = fuente_manual(cur)
            if args.reemplazar:
                cur.execute(
                    "DELETE FROM menus WHERE restaurant_id = ANY(%s)",
                    (list(ids_restaurantes),),
                )
                print("Menús previos borrados para %d restaurantes." % len(ids_restaurantes))

            insertados = 0
            for n, rid, fila in validos:
                fecha = texto(fila.get("data_date"), 10) or date.today().isoformat()
                cur.execute(
                    """
                    INSERT INTO menus (restaurant_id, dish_name, category, description, price,
                                       currency, ingredients, source_id, confidence_level, data_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING menu_id
                    """,
                    (
                        rid,
                        texto(fila.get("dish_name"), 300),
                        texto(fila.get("category"), 100) or None,
                        texto(fila.get("description"), 2000) or None,
                        decimal(fila.get("price"), 9999999),
                        (texto(fila.get("currency"), 3) or "ARS").upper(),
                        [x.strip() for x in texto(fila.get("ingredients"), 1000).replace(";", "|").split("|") if x.strip()] or None,
                        sid,
                        texto(fila.get("confidence_level"), 30) or "community",
                        fecha,
                    ),
                )
                menu_id = cur.fetchone()[0]

                valores = {c: booleano(fila.get(c)) for c in CAMPOS_BOOL}
                numeros = {c: decimal(fila.get(c), 10000) for c in CAMPOS_NUM}
                porcion = texto(fila.get("portion_size"), 50) or None
                if any(v is not None for v in valores.values()) or any(v is not None for v in numeros.values()) or porcion:
                    cur.execute(
                        """
                        INSERT INTO dish_features (menu_id, gluten_free, vegetarian, vegan, lactose_free,
                                                   contains_gluten, contains_lactose, contains_egg, contains_nuts,
                                                   carbohydrates, sugars, fiber, proteins, fats, portion_size,
                                                   source_id, confidence_level)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            menu_id,
                            valores["gluten_free"], valores["vegetarian"], valores["vegan"], valores["lactose_free"],
                            valores["contains_gluten"], valores["contains_lactose"],
                            valores["contains_egg"], valores["contains_nuts"],
                            numeros["carbohydrates"], numeros["sugars"], numeros["fiber"],
                            numeros["proteins"], numeros["fats"], porcion,
                            sid, texto(fila.get("confidence_level"), 30) or "community",
                        ),
                    )
                insertados += 1
            conn.commit()
        print("Importados %d platos." % insertados)
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
