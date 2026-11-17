#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Geocodifica restaurantes sin coordenadas usando Nominatim (OpenStreetMap).

Uso:
    python scripts/geocodificar_ba_data.py --dry-run --limit 10
    python scripts/geocodificar_ba_data.py --limit 100
    python scripts/geocodificar_ba_data.py                # todos los pendientes

Qué hace:
  1. Busca restaurantes activos sin geom/lat/lon.
  2. Arma una consulta con nombre, dirección, barrio, ciudad y provincia.
  3. Consulta Nominatim respetando su política: 1 pedido por segundo y un
     User-Agent identificable (NOMINATIM_EMAIL o --email).
  4. Guarda la respuesta en un caché JSON para no repetir consultas.
  5. Actualiza latitude, longitude y geom cuando encuentra un resultado dentro
     del área de cobertura (CABA + GBA).

Ojo: Nominatim es un servicio comunitario. Para miles de registros conviene el
dataset oficial de BA Data con coordenadas o un proveedor pago. Con ~2.740
pendientes y 1 req/s el proceso completo tarda unos 46 minutos.

Variables:
    DATABASE_URL       conexión a PostgreSQL (o backend/.env)
    NOMINATIM_EMAIL    correo de contacto exigido para usos intensivos
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import requests

from _db import RAIZ, conectar

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
CACHE_DEFECTO = RAIZ / "data" / "cache_geocodificacion.json"

# Cobertura del proyecto: CABA y Gran Buenos Aires (con margen).
LAT_MIN, LAT_MAX = -35.20, -34.15
LON_MIN, LON_MAX = -59.40, -57.75


def cargar_cache(ruta: Path) -> dict:
    if not ruta.exists():
        return {}
    try:
        with ruta.open(encoding="utf-8") as f:
            datos = json.load(f)
        return datos if isinstance(datos, dict) else {}
    except Exception:
        print("Aviso: el caché no se pudo leer; se empieza de cero.")
        return {}


def guardar_cache(ruta: Path, cache: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    with temporal.open("w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)
    temporal.replace(ruta)


def clave_cache(consulta: str) -> str:
    return hashlib.sha256(consulta.lower().encode("utf-8")).hexdigest()[:32]


def consultar_nominatim(consulta: str, email: str, timeout: int = 20):
    """Devuelve (lat, lon, display_name), None si no hay resultado o False si
    hubo un error temporario (red, 403 o 429). Los errores no se guardan en el
    caché para poder reintentarlos más adelante."""

    def _error(mensaje: str):
        print("  " + mensaje)
        return False

    headers = {
        "User-Agent": "GastronomIA/1.0 (geocodificacion de restaurantes; contacto: %s)" % (email or "sin-email"),
        "Accept-Language": "es",
    }
    params = {
        "q": consulta,
        "format": "jsonv2",
        "limit": 1,
        "countrycodes": "ar",
        "addressdetails": 1,
    }
    if email:
        params["email"] = email

    for intento in (1, 2):
        try:
            r = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=timeout)
        except requests.RequestException as e:
            return _error("Error de red: %s" % e)
        if r.status_code == 429:
            print("  Nominatim pidió esperar (429); se espera 60 s...")
            time.sleep(60)
            continue
        if r.status_code != 200:
            return _error("Nominatim respondió %s (no se guarda en caché)" % r.status_code)
        try:
            datos = r.json()
        except ValueError:
            return None
        if not datos:
            return None
        d = datos[0]
        try:
            lat, lon = float(d["lat"]), float(d["lon"])
        except (KeyError, TypeError, ValueError):
            return None
        return lat, lon, d.get("display_name", "")
    return _error("Nominatim no respondió después del reintento")


def dentro_de_cobertura(lat: float, lon: float) -> bool:
    return LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX


def pendientes(conn, limite: int):
    sql = """
        SELECT restaurant_id, name, address, neighborhood, city, province
        FROM restaurants
        WHERE is_active IS NOT FALSE
          AND (geom IS NULL OR latitude IS NULL OR longitude IS NULL)
        ORDER BY restaurant_id
    """
    if limite and limite > 0:
        sql += " LIMIT %s"
    with conn.cursor() as cur:
        cur.execute(sql, (limite,) if limite and limite > 0 else ())
        return cur.fetchall()


def main() -> int:
    p = argparse.ArgumentParser(description="Geocodifica restaurantes con Nominatim (1 req/s).")
    p.add_argument("--limit", type=int, default=0, help="Máximo de registros a procesar (0 = todos).")
    p.add_argument("--dry-run", action="store_true", help="Muestra qué haría, sin consultar ni escribir.")
    p.add_argument("--sleep", type=float, default=1.1, help="Segundos entre consultas (mínimo recomendado: 1).")
    p.add_argument("--cache", default=str(CACHE_DEFECTO), help="Archivo de caché JSON.")
    p.add_argument("--email", default=os.getenv("NOMINATIM_EMAIL", ""), help="Correo de contacto para Nominatim.")
    p.add_argument("--reintentar-fallidos", action="store_true",
                   help="Vuelve a consultar los que antes no tuvieron resultado.")
    args = p.parse_args()

    if args.sleep < 1.0:
        print("Aviso: Nominatim exige como máximo 1 consulta por segundo; se usa 1.1 s.")
        args.sleep = 1.1
    if not args.dry_run and not args.email:
        print("Aviso: definí NOMINATIM_EMAIL o --email para identificar el uso del servicio.")

    cache = cargar_cache(Path(args.cache))
    conn = conectar()
    filas = pendientes(conn, args.limit)

    if not filas:
        print("No hay restaurantes pendientes de geocodificar.")
        return 0

    print("Pendientes a revisar: %d" % len(filas))
    if args.dry_run:
        for rid, nombre, direccion, barrio, ciudad, provincia in filas[: max(1, args.limit or 20)]:
            partes = [x for x in (nombre, direccion, barrio, ciudad, provincia, "Argentina") if x]
            print("  #%s  %s" % (rid, ", ".join(str(x).strip() for x in partes)))
        print("\nDry-run: no se consultó Nominatim ni se modificó la base.")
        return 0

    actualizados = 0
    sin_resultado = 0
    try:
        with conn.cursor() as cur:
            for i, (rid, nombre, direccion, barrio, ciudad, provincia) in enumerate(filas, start=1):
                partes = [str(x).strip() for x in (nombre, direccion, barrio, ciudad, provincia, "Argentina")
                          if x and str(x).strip()]
                consulta = ", ".join(partes)
                clave = clave_cache(consulta)

                if clave in cache and cache[clave] is None and not args.reintentar_fallidos:
                    sin_resultado += 1
                    continue

                if clave in cache and isinstance(cache[clave], dict):
                    lat, lon, display = cache[clave]["lat"], cache[clave]["lon"], cache[clave].get("display", "")
                else:
                    print("[%d/%d] #%s %s" % (i, len(filas), rid, consulta[:110]))
                    resultado = consultar_nominatim(consulta, args.email)
                    if resultado is False:
                        # Error temporario (red/403/429): no se cachea para
                        # poder reintentarlo en otra ejecución.
                        sin_resultado += 1
                        time.sleep(args.sleep)
                        continue
                    if resultado is None:
                        cache[clave] = None
                        sin_resultado += 1
                        guardar_cache(Path(args.cache), cache)
                        time.sleep(args.sleep)
                        continue
                    lat, lon, display = resultado
                    if not dentro_de_cobertura(lat, lon):
                        print("  Descartado: coordenadas fuera de CABA/GBA (%.5f, %.5f)" % (lat, lon))
                        cache[clave] = None
                        sin_resultado += 1
                        guardar_cache(Path(args.cache), cache)
                        time.sleep(args.sleep)
                        continue
                    cache[clave] = {"lat": lat, "lon": lon, "display": display}
                    guardar_cache(Path(args.cache), cache)
                    time.sleep(args.sleep)

                cur.execute(
                    """
                    UPDATE restaurants
                    SET latitude = %s,
                        longitude = %s,
                        geom = ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                        updated_at = NOW()
                    WHERE restaurant_id = %s
                    """,
                    (lat, lon, lon, lat, rid),
                )
                conn.commit()
                actualizados += 1
                print("  OK: %.5f, %.5f  %s" % (lat, lon, (display or consulta)[:90]))
    except KeyboardInterrupt:
        conn.rollback()
        print("\nInterrumpido. Se conservan los cambios ya confirmados y el caché.")
    finally:
        conn.close()
        guardar_cache(Path(args.cache), cache)

    print("\nGeocodificación terminada: %d actualizados, %d sin resultado o descartados." %
          (actualizados, sin_resultado))
    print("Caché: %s" % args.cache)
    return 0


if __name__ == "__main__":
    sys.exit(main())
