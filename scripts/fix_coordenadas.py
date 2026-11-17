#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corrige coordenadas escaladas mal y deja el mapa y la cercanía confiables.

Algunos registros del CSV traen el entero de 1e7 con ceros finales perdidos
(ej. -3461369 en vez de -34613690). El importador viejo los guardaba como
-0.3461369 / -58.4162428, así que el restaurante aparecía en el océano.

Uso:
    python scripts/fix_coordenadas.py
    DATABASE_URL=postgresql://... python scripts/fix_coordenadas.py
"""
import os

import psycopg2
from psycopg2.extras import execute_batch

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "gastro_ia",
    "user": "postgres",
    "password": os.getenv("PGPASSWORD", ""),
}


def _a_grados(valor, referencia):
    try:
        texto = str(valor).strip().replace(",", ".")
        if not texto:
            return None
        grados = float(texto)
        if abs(grados) < 0.001:
            return None
        for _ in range(6):
            if abs(grados) >= referencia:
                break
            grados *= 10
        return round(grados, 7)
    except (TypeError, ValueError):
        return None


def coordenada_valida(lat, lon):
    return (
        lat is not None
        and lon is not None
        and -55 <= lat <= -21
        and -74 <= lon <= -53
    )


def main():
    conn = (
        psycopg2.connect(os.environ["DATABASE_URL"])
        if os.getenv("DATABASE_URL")
        else psycopg2.connect(**DB_CONFIG)
    )
    cur = conn.cursor()

    # Solo toca filas con geometría y coordenadas fuera del rango de Argentina.
    cur.execute(
        """
        SELECT restaurant_id, latitude, longitude
        FROM restaurants
        WHERE geom IS NOT NULL
          AND (latitude NOT BETWEEN -90 AND -30 OR longitude NOT BETWEEN -75 AND -50)
        """
    )
    filas = cur.fetchall()

    cambios = []
    descartadas = 0
    for restaurant_id, lat, lon in filas:
        nlat = _a_grados(lat, 30)
        nlon = _a_grados(lon, 50)
        if not coordenada_valida(nlat, nlon):
            nlat, nlon = None, None
            descartadas += 1
        cambios.append((nlat, nlon, nlat, nlon, nlon, nlat, restaurant_id))

    if cambios:
        execute_batch(
            cur,
            """
            UPDATE restaurants
            SET latitude = %s,
                longitude = %s,
                geom = CASE
                    WHEN %s IS NULL OR %s IS NULL THEN NULL
                    ELSE ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                END
            WHERE restaurant_id = %s
            """,
            cambios,
            page_size=200,
        )
        conn.commit()

    cur.execute("ANALYZE restaurants")
    conn.commit()

    cur.execute(
        """
        SELECT count(*) FROM restaurants
        WHERE geom IS NOT NULL
          AND (latitude NOT BETWEEN -55 AND -21 OR longitude NOT BETWEEN -74 AND -53)
        """
    )
    quedan_malas = cur.fetchone()[0]

    print("Filas revisadas: %d" % len(filas))
    print("Coordenadas corregidas: %d" % (len(filas) - descartadas))
    print("Coordenadas descartadas (sin dato válido): %d" % descartadas)
    print("Filas fuera de rango que quedan: %d" % quedan_malas)
    conn.close()


if __name__ == "__main__":
    main()
