#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enriquece restaurantes con Google Places API (New): rating, cantidad de
reseñas, rango de precio, teléfono y sitio web.

Es OPCIONAL y requiere una cuenta de Google Cloud con facturación y la
"Places API (New)" habilitada:

    set GOOGLE_MAPS_API_KEY=...         (Windows)
    export GOOGLE_MAPS_API_KEY=...      (Linux/macOS)
    python scripts/enriquecer_google_places.py --dry-run --limit 10
    python scripts/enriquecer_google_places.py --limit 100

Qué hace:
  - Busca locales activos (por defecto, solo los que no tienen rating).
  - Consulta Text Search con sesgo por coordenadas cuando existen.
  - Completa rating, review_count, price_range, phone y website.
  - No pisa datos cargados por el comercio salvo rating/review_count.
  - Guarda caché para no repetir consultas ni gastar cuota.

Condiciones de uso: los datos de Google Maps requieren atribución ("Powered by
Google") y no deben almacenarse más de 30 días según sus términos. Usá este
script para completar/refrescar datos y revisá esas condiciones antes de
publicarlos. Si no querés depender de Google, el proyecto funciona sin esto.
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

URL = "https://places.googleapis.com/v1/places:searchText"
CACHE_DEFECTO = RAIZ / "data" / "cache_google_places.json"
CAMPOS = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.rating",
    "places.userRatingCount",
    "places.priceLevel",
    "places.nationalPhoneNumber",
    "places.websiteUri",
    "places.location",
])

PRECIOS = {
    "PRICE_LEVEL_INEXPENSIVE": 1,
    "PRICE_LEVEL_MODERATE": 2,
    "PRICE_LEVEL_EXPENSIVE": 3,
    "PRICE_LEVEL_VERY_EXPENSIVE": 4,
}


def cargar_cache(ruta: Path) -> dict:
    if not ruta.exists():
        return {}
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return {}


def guardar_cache(ruta: Path, cache: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(ruta.suffix + ".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(ruta)


def clave(rid: int, consulta: str) -> str:
    return hashlib.sha256(("%s|%s" % (rid, consulta.lower())).encode("utf-8")).hexdigest()[:32]


def obtener(rid, nombre, direccion, barrio, ciudad, lat, lon, api_key, timeout=20):
    consulta = ", ".join(str(x).strip() for x in (nombre, direccion, barrio, ciudad, "Argentina")
                         if x and str(x).strip())
    cuerpo = {
        "textQuery": consulta,
        "languageCode": "es",
        "regionCode": "AR",
        "maxResultCount": 1,
    }
    if lat is not None and lon is not None:
        cuerpo["locationBias"] = {
            "circle": {"center": {"latitude": float(lat), "longitude": float(lon)}, "radius": 800.0}
        }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": CAMPOS,
    }
    try:
        r = requests.post(URL, json=cuerpo, headers=headers, timeout=timeout)
    except requests.RequestException as e:
        print("  Error de red: %s" % e)
        return None, consulta
    if r.status_code == 429:
        print("  Cuota de Google agotada (429). Se corta para no seguir gastando.")
        return "CUOTA", consulta
    if r.status_code in (401, 403):
        print("  Google rechazó la clave (%s). Revisá GOOGLE_MAPS_API_KEY y la facturación." % r.status_code)
        return "CLAVE", consulta
    if r.status_code != 200:
        print("  Google respondió %s: %s" % (r.status_code, r.text[:200]))
        return None, consulta
    datos = r.json().get("places") or []
    return (datos[0] if datos else None), consulta


def main() -> int:
    p = argparse.ArgumentParser(description="Completa datos con Google Places API (New).")
    p.add_argument("--limit", type=int, default=0, help="Máximo de locales a consultar (0 = todos).")
    p.add_argument("--dry-run", action="store_true", help="Muestra qué consultaría, sin llamar a Google.")
    p.add_argument("--todos", action="store_true", help="Incluye locales que ya tienen rating.")
    p.add_argument("--sleep", type=float, default=0.25, help="Pausa entre consultas (segundos).")
    p.add_argument("--cache", default=str(CACHE_DEFECTO), help="Archivo de caché JSON.")
    args = p.parse_args()

    api_key = (os.getenv("GOOGLE_MAPS_API_KEY") or "").strip()
    if not api_key and not args.dry_run:
        print("Falta GOOGLE_MAPS_API_KEY. Creá una clave con 'Places API (New)' habilitada.")
        print("Sin clave, el resto de GastronomIA funciona normalmente.")
        return 2

    conn = conectar()
    sql = """
        SELECT restaurant_id, name, address, neighborhood, city, latitude, longitude
        FROM restaurants
        WHERE is_active IS NOT FALSE
    """
    if not args.todos:
        sql += " AND rating IS NULL"
    sql += " ORDER BY restaurant_id"
    if args.limit and args.limit > 0:
        sql += " LIMIT %s"
    with conn.cursor() as cur:
        cur.execute(sql, (args.limit,) if args.limit and args.limit > 0 else ())
        filas = cur.fetchall()

    if not filas:
        print("No hay locales para enriquecer.")
        return 0

    print("Locales a consultar: %d" % len(filas))
    if args.dry_run:
        for rid, nombre, direccion, barrio, ciudad, lat, lon in filas[: max(1, args.limit or 20)]:
            print("  #%s  %s | %s, %s" % (rid, nombre, direccion or "sin dirección", ciudad))
        print("\nDry-run: no se llamó a Google ni se modificó la base.")
        return 0

    cache = cargar_cache(Path(args.cache))
    actualizados = 0
    sin_datos = 0
    try:
        with conn.cursor() as cur:
            for i, (rid, nombre, direccion, barrio, ciudad, lat, lon) in enumerate(filas, start=1):
                consulta_base = ", ".join(str(x).strip() for x in (nombre, direccion, barrio, ciudad) if x)
                k = clave(rid, consulta_base)
                if k in cache:
                    lugar = cache[k]
                else:
                    print("[%d/%d] #%s %s" % (i, len(filas), rid, nombre))
                    lugar, _ = obtener(rid, nombre, direccion, barrio, ciudad, lat, lon, api_key)
                    if lugar == "CUOTA":
                        break
                    if lugar == "CLAVE":
                        return 2
                    cache[k] = lugar
                    guardar_cache(Path(args.cache), cache)
                    time.sleep(max(0.0, args.sleep))
                if not lugar:
                    sin_datos += 1
                    continue

                precio = PRECIOS.get(lugar.get("priceLevel"))
                rating = lugar.get("rating")
                resenas = lugar.get("userRatingCount")
                telefono = lugar.get("nationalPhoneNumber")
                web = lugar.get("websiteUri")

                cur.execute(
                    """
                    UPDATE restaurants
                    SET rating = COALESCE(%s, rating),
                        review_count = COALESCE(%s, review_count),
                        price_range = COALESCE(price_range, %s),
                        phone = COALESCE(NULLIF(phone, ''), %s),
                        website = COALESCE(NULLIF(website, ''), %s),
                        data_date = CURRENT_DATE,
                        updated_at = NOW()
                    WHERE restaurant_id = %s
                    """,
                    (rating, resenas, precio, telefono, web, rid),
                )
                conn.commit()
                actualizados += 1
                print("  OK: rating=%s (%s reseñas), precio=%s" % (rating, resenas, precio))
    except KeyboardInterrupt:
        conn.rollback()
        print("\nInterrumpido. Se conservan los cambios ya confirmados.")
    finally:
        conn.close()
        guardar_cache(Path(args.cache), cache)

    print("\nEnriquecimiento terminado: %d actualizados, %d sin coincidencia." % (actualizados, sin_datos))
    print("Caché: %s" % args.cache)
    return 0


if __name__ == "__main__":
    sys.exit(main())
