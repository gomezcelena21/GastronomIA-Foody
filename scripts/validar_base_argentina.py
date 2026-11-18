#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Valida, sin salir a internet, que la base de GastronomIA solo tenga lugares de Argentina.

Revisa el CSV nacional y, opcionalmente, la base PostgreSQL:
  - la provincia es una de las 24 jurisdicciones argentinas (23 provincias + CABA);
  - las coordenadas (si existen) caen dentro del recuadro de Argentina;
  - no hay coordenadas incompletas;
  - la región es una de las que usa el sistema (CABA, GBA, Interior o Sin confirmar).

    python scripts/validar_base_argentina.py
    python scripts/validar_base_argentina.py --db
    python scripts/validar_base_argentina.py --db --desactivar
    python scripts/validar_base_argentina.py --limpiar-csv

Opciones:
  --csv RUTA         CSV a validar (por defecto data/dataset_unificado_ARGENTINA.csv)
  --db               valida también la tabla restaurants
  --limpiar-csv      reescribe el CSV sin filas inválidas y con la provincia canónica
  --desactivar       con --db, marca is_active = FALSE en las filas inválidas
  --reporte RUTA     Markdown de salida (por defecto docs/pruebas/validacion_argentina_<fecha>.md)
  --muestra N        filas de ejemplo por problema (por defecto 10)

No descarta lugares por nombres extranjeros en la calle («Montevideo 1480» es una
dirección de CABA): solo valida provincia y coordenadas.
"""
import argparse
import csv
import sys
from collections import Counter
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))
from geografia import (  # noqa: E402
    coordenadas_en_argentina,
    normalizar_provincia,
)

CSV_POR_DEFECTO = RAIZ / "data" / "dataset_unificado_ARGENTINA.csv"
REGIONES_VALIDAS = ("CABA", "GBA", "Interior", "Sin confirmar")
CAMPOS = ["id_origen", "nombre", "provincia", "ciudad", "barrio", "region", "partido", "zona", "direccion",
          "latitud", "longitud", "cocina", "categoria", "telefono", "website", "sin_tacc", "vegetariano",
          "vegano", "sin_lactosa", "dato_inferido", "fuente", "fecha_dato"]


def _numero(valor):
    try:
        return float(valor) if str(valor or "").strip() else None
    except (TypeError, ValueError):
        return None


def analizar_csv(filas):
    """Devuelve un informe con los problemas encontrados en el CSV."""
    total = len(filas)
    provincias = Counter()
    provincias_invalidas = []
    regiones = Counter()
    regiones_invalidas = []
    coords_fuera = []
    coords_incompletas = []
    sin_ciudad = []
    sin_zona = []
    con_coords = 0
    for r in filas:
        canonica = normalizar_provincia(r.get("provincia"))
        provincias[canonica or (r.get("provincia") or "(vacía)")] += 1
        if not canonica:
            provincias_invalidas.append(r)
        region = (r.get("region") or "").strip()
        regiones[region or "(vacía)"] += 1
        if region not in REGIONES_VALIDAS:
            regiones_invalidas.append(r)
        la, lo = _numero(r.get("latitud")), _numero(r.get("longitud"))
        if (la is None) != (lo is None):
            coords_incompletas.append(r)
        elif la is not None:
            con_coords += 1
            if not coordenadas_en_argentina(la, lo):
                coords_fuera.append(r)
        if not (r.get("ciudad") or "").strip():
            sin_ciudad.append(r)
        if not (r.get("zona") or "").strip():
            sin_zona.append(r)
    return {
        "total": total,
        "con_coords": con_coords,
        "provincias": provincias,
        "provincias_invalidas": provincias_invalidas,
        "regiones": regiones,
        "regiones_invalidas": regiones_invalidas,
        "coords_fuera": coords_fuera,
        "coords_incompletas": coords_incompletas,
        "sin_ciudad": sin_ciudad,
        "sin_zona": sin_zona,
    }


def filas_invalidas_csv(filas):
    """Índices de las filas que no son de Argentina (provincia o coordenadas)."""
    malas = set()
    for i, r in enumerate(filas):
        if not normalizar_provincia(r.get("provincia")):
            malas.add(i)
            continue
        la, lo = _numero(r.get("latitud")), _numero(r.get("longitud"))
        if la is not None and lo is not None and not coordenadas_en_argentina(la, lo):
            malas.add(i)
    return malas


def limpiar_csv(filas):
    """Saca filas de otro país, normaliza la provincia y descarta coordenadas incompletas."""
    limpias, quitadas = [], 0
    malas = filas_invalidas_csv(filas)
    for i, r in enumerate(filas):
        if i in malas:
            quitadas += 1
            continue
        r = dict(r)
        r["provincia"] = normalizar_provincia(r["provincia"])
        la, lo = _numero(r.get("latitud")), _numero(r.get("longitud"))
        if (la is None) != (lo is None):       # media coordenada: no sirve para el mapa
            r["latitud"], r["longitud"] = "", ""
        limpias.append(r)
    return limpias, quitadas


def escribir_csv(ruta, filas):
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(filas)


def analizar_db(conn):
    """Valida las filas de restaurants. Devuelve el informe y los ids inválidos."""
    cur = conn.cursor()
    cur.execute("SELECT restaurant_id, name, province, city, region, latitude, longitude, is_active, source_type "
                "FROM restaurants")
    columnas = [d[0] for d in cur.description]
    filas = [dict(zip(columnas, fila)) for fila in cur.fetchall()]
    cur.close()
    total = len(filas)
    activas = sum(1 for r in filas if r["is_active"])
    provincias = Counter()
    provincias_invalidas = []
    regiones_invalidas = []
    coords_fuera = []
    coords_incompletas = []
    for r in filas:
        canonica = normalizar_provincia(r["province"])
        provincias[canonica or (r["province"] or "(vacía)")] += 1
        if not canonica:
            provincias_invalidas.append(r)
        if r.get("region") and r["region"] not in REGIONES_VALIDAS:
            regiones_invalidas.append(r)
        la, lo = _numero(r["latitude"]), _numero(r["longitude"])
        if (la is None) != (lo is None):
            coords_incompletas.append(r)
        elif la is not None and not coordenadas_en_argentina(la, lo):
            coords_fuera.append(r)
    invalidas = provincias_invalidas + coords_fuera + coords_incompletas
    ids = sorted({r["restaurant_id"] for r in invalidas})
    return {
        "total": total,
        "activas": activas,
        "provincias": provincias,
        "provincias_invalidas": provincias_invalidas,
        "regiones_invalidas": regiones_invalidas,
        "coords_fuera": coords_fuera,
        "coords_incompletas": coords_incompletas,
        "ids_invalidos": ids,
    }


def desactivar_db(conn, ids):
    if not ids:
        return 0
    cur = conn.cursor()
    cur.execute("UPDATE restaurants SET is_active = FALSE WHERE is_active = TRUE AND restaurant_id = ANY(%s)", (ids,))
    n = cur.rowcount
    conn.commit()
    cur.close()
    return n


def _tabla_provincias(contador):
    lineas = ["| Provincia | Lugares |", "|---|---:|"]
    for nombre, n in contador.most_common():
        lineas.append("| %s | %s |" % (nombre, format(n, ",").replace(",", ".")))
    return "\n".join(lineas)


def _lista_ejemplos(filas, muestra):
    if not filas:
        return "_Ninguno._"
    lineas = ["| ID | Nombre | Provincia | Ciudad | Latitud | Longitud |", "|---|---|---|---|---:|---:|"]
    for r in filas[:muestra]:
        lineas.append("| %s | %s | %s | %s | %s | %s |" % (
            r.get("id_origen", r.get("restaurant_id", "")), str(r.get("nombre", r.get("name", "")))[:45],
            r.get("provincia", r.get("province", "")), str(r.get("ciudad", r.get("city", "")))[:30],
            r.get("latitud", r.get("latitude", "")), r.get("longitud", r.get("longitude", ""))))
    if len(filas) > muestra:
        lineas.append("\n_(se muestran %d de %d)_" % (muestra, len(filas)))
    return "\n".join(lineas)


def escribir_reporte(ruta, inf_csv, inf_db, acciones, ruta_csv, muestra):
    hoy = date.today().isoformat()
    lineas = [
        "# Validación geográfica de Argentina",
        "",
        "- **Fecha:** %s" % hoy,
        "- **CSV:** `%s`" % ruta_csv,
        "- **Fuente de provincias:** `backend/geografia.py` (23 provincias + CABA).",
        "- **Criterio:** se descarta solo lo que no se puede ubicar en Argentina (provincia no argentina o "
        "coordenadas fuera del recuadro del país). No se descartan direcciones con nombres extranjeros "
        "(por ejemplo, «Montevideo 1480» en CABA).",
        "",
        "## CSV",
        "",
        "- Filas: **%s**" % format(inf_csv["total"], ",").replace(",", "."),
        "- Con coordenadas: **%s** (%.1f %%)" % (
            format(inf_csv["con_coords"], ",").replace(",", "."),
            100.0 * inf_csv["con_coords"] / inf_csv["total"] if inf_csv["total"] else 0),
        "- Provincias no argentinas: **%d**" % len(inf_csv["provincias_invalidas"]),
        "- Coordenadas fuera de Argentina: **%d**" % len(inf_csv["coords_fuera"]),
        "- Coordenadas incompletas: **%d**" % len(inf_csv["coords_incompletas"]),
        "- Regiones desconocidas: **%d**" % len(inf_csv["regiones_invalidas"]),
        "- Sin ciudad: **%d** · Sin zona: **%d**" % (len(inf_csv["sin_ciudad"]), len(inf_csv["sin_zona"])),
        "",
        "### Provincias",
        "",
        _tabla_provincias(inf_csv["provincias"]),
        "",
        "### Ejemplos de provincias no argentinas",
        "",
        _lista_ejemplos(inf_csv["provincias_invalidas"], muestra),
        "",
        "### Ejemplos de coordenadas fuera de Argentina",
        "",
        _lista_ejemplos(inf_csv["coords_fuera"], muestra),
        "",
        "### Ejemplos de coordenadas incompletas",
        "",
        _lista_ejemplos(inf_csv["coords_incompletas"], muestra),
    ]
    if inf_db is not None:
        lineas += [
            "",
            "## Base de datos (`restaurants`)",
            "",
            "- Filas: **%s** · activas: **%s**" % (
                format(inf_db["total"], ",").replace(",", "."), format(inf_db["activas"], ",").replace(",", ".")),
            "- Provincias no argentinas: **%d**" % len(inf_db["provincias_invalidas"]),
            "- Coordenadas fuera de Argentina: **%d**" % len(inf_db["coords_fuera"]),
            "- Coordenadas incompletas: **%d**" % len(inf_db["coords_incompletas"]),
            "- Regiones desconocidas: **%d**" % len(inf_db["regiones_invalidas"]),
            "",
            "### Ejemplos de provincias no argentinas en la base",
            "",
            _lista_ejemplos(inf_db["provincias_invalidas"], muestra),
            "",
            "### Ejemplos de coordenadas fuera de Argentina en la base",
            "",
            _lista_ejemplos(inf_db["coords_fuera"], muestra),
        ]
    lineas += ["", "## Acciones", ""]
    lineas += ["- %s" % a for a in acciones] if acciones else ["- Solo validación: no se modificó ningún archivo ni fila."]
    lineas += ["", "## Conclusión", ""]
    problemas = (len(inf_csv["provincias_invalidas"]) + len(inf_csv["coords_fuera"])
                 + len(inf_csv["coords_incompletas"]))
    if inf_db is not None:
        problemas += len(inf_db["ids_invalidos"])
    if problemas:
        lineas.append("Se encontraron **%d** casos para revisar. Ver las tablas de arriba." % problemas)
    else:
        lineas.append("**Sin fallas geográficas:** todas las filas tienen una provincia argentina y, cuando "
                      "tienen coordenadas, caen dentro de Argentina.")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return ruta


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default=str(CSV_POR_DEFECTO))
    ap.add_argument("--db", action="store_true", help="valida también la tabla restaurants")
    ap.add_argument("--limpiar-csv", action="store_true")
    ap.add_argument("--desactivar", action="store_true", help="con --db, desactiva las filas inválidas")
    ap.add_argument("--reporte")
    ap.add_argument("--muestra", type=int, default=10)
    a = ap.parse_args(argv)

    ruta_csv = Path(a.csv)
    if not ruta_csv.exists():
        print("No encuentro %s." % ruta_csv)
        return 1
    with open(ruta_csv, encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    inf_csv = analizar_csv(filas)
    print("CSV: %d filas | provincias inválidas: %d | coords fuera: %d | coords incompletas: %d" % (
        inf_csv["total"], len(inf_csv["provincias_invalidas"]), len(inf_csv["coords_fuera"]),
        len(inf_csv["coords_incompletas"])))

    acciones = []
    if a.limpiar_csv:
        limpias, quitadas = limpiar_csv(filas)
        escribir_csv(ruta_csv, limpias)
        acciones.append("Se reescribió el CSV: %d filas eliminadas por no ser de Argentina; provincia normalizada."
                        % quitadas)
        print("CSV limpiado: %d filas eliminadas, quedan %d." % (quitadas, len(limpias)))
        filas = limpias
        inf_csv = analizar_csv(filas)

    inf_db = None
    if a.db or a.desactivar:
        try:
            from _db import conectar
            conn = conectar()
        except SystemExit as exc:
            print(exc)
            return 1
        try:
            inf_db = analizar_db(conn)
            print("Base: %d filas | provincias inválidas: %d | coords fuera: %d | coords incompletas: %d" % (
                inf_db["total"], len(inf_db["provincias_invalidas"]), len(inf_db["coords_fuera"]),
                len(inf_db["coords_incompletas"])))
            if a.desactivar:
                n = desactivar_db(conn, inf_db["ids_invalidos"])
                acciones.append("Se desactivaron %d filas inválidas en restaurants (is_active = FALSE)." % n)
                print("Desactivadas %d filas." % n)
        finally:
            conn.close()

    ruta_reporte = Path(a.reporte) if a.reporte else (
        RAIZ / "docs" / "pruebas" / ("validacion_argentina_%s.md" % date.today().isoformat()))
    ruta_reporte = escribir_reporte(ruta_reporte, inf_csv, inf_db, acciones, ruta_csv, a.muestra)
    print("Reporte: %s" % ruta_reporte)
    problemas = (len(inf_csv["provincias_invalidas"]) + len(inf_csv["coords_fuera"])
                 + len(inf_csv["coords_incompletas"]))
    if inf_db is not None:
        problemas += len(inf_db["ids_invalidos"])
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
