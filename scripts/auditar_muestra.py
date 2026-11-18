#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auditoría por muestreo de la base nacional de GastronomIA (sin salir a internet).

Toma una muestra estratificada por fuente (~200 casos, semilla fija), la compara con
la planilla de origen y, cuando existe, con el archivo crudo de la fuente. Responde:

  - ¿qué porcentaje se puede rastrear hasta una fila del Excel de origen?
  - ¿qué porcentaje conserva provincia, ciudad y dirección coherentes?
  - ¿qué porcentaje aparece además en el archivo crudo (Overture, OSM/BA Data)?
  - ¿cuántos duplicados hay en toda la base y en la muestra?
  - ¿qué provincias quedan dudosas («Sin confirmar», sin coincidencia o sin ciudad)?

    python scripts/auditar_muestra.py
    python scripts/auditar_muestra.py --n 300 --semilla 20261116
    python scripts/auditar_muestra.py --reporte docs/pruebas/auditoria_muestra.md

Los archivos crudos son opcionales. Si no están, el informe lo indica y sigue con
la trazabilidad contra el Excel. No se consulta cada localidad en internet.
"""
import argparse
import csv
import math
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))
from geografia import normalizar_provincia  # noqa: E402

CSV_POR_DEFECTO = RAIZ / "data" / "dataset_unificado_ARGENTINA.csv"
BASE_CABA_GBA = RAIZ / "etl" / "raw" / "dataset_gastronomia_CABA_GBA.csv"
CARPETA_DATOS = Path.home() / "Documents" / "Base de datos Gastronomia"
EXCEL_POR_DEFECTO = CARPETA_DATOS / "Base_Unificada_Restricciones_Argentina.xlsx"
OVERTURE_POR_DEFECTO = CARPETA_DATOS / "overture_ar.csv"
SEMILLA_POR_DEFECTO = 20261116
CAMPOS_EXCEL = ["ID", "Nombre", "Región", "Provincia", "Ciudad / barrio (original)", "Partido (GBA)",
                "Zona (macro)", "Localidad / barrio", "Dirección", "Latitud", "Longitud", "Fuente(s)",
                "ID de origen (OSM / BA Data)", "Google place_id"]


# ----------------------------------------------------------------------------- utilidades
def norm(texto) -> str:
    """Minúsculas, sin tildes y con espacios simples (mismo criterio que el backend)."""
    t = unicodedata.normalize("NFD", str(texto or ""))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t.lower()).strip()


def texto(valor) -> str:
    if valor is None:
        return ""
    s = str(valor).strip()
    return "" if s.lower() in ("nan", "none", "nat") else s


def numero(valor):
    try:
        return float(valor) if texto(valor) else None
    except (TypeError, ValueError):
        return None


def fuente_tipo(fuente) -> str:
    """Misma clasificación que scripts/convertir_base_unificada.py."""
    f = norm(fuente)
    if "overture" in f:
        return "overture"
    if "google" in f and "openstreetmap" not in f:
        return "google_places"
    if "ba data" in f:
        return "ba_data"
    if "kosher" in f:
        return "guia_kosher"
    if "celiacos" in f:
        return "guia_celiacos"
    return "osm"


def distancia_km(lat1, lon1, lat2, lon2) -> float:
    """Distancia aproximada entre dos coordenadas (haversine)."""
    radio = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radio * math.asin(math.sqrt(a))


def nombres_coinciden(a, b) -> bool:
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na


def coords_cerca(r, lat, lon, tolerancia_km=0.25) -> bool:
    la, lo = numero(r.get("latitud")), numero(r.get("longitud"))
    if la is None or lo is None or lat is None or lon is None:
        return False
    return distancia_km(la, lo, lat, lon) <= tolerancia_km


# ----------------------------------------------------------------------------- lectura
def leer_csv(ruta):
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def leer_excel(ruta):
    try:
        import pandas as pd
    except ImportError:
        sys.exit("Falta pandas y openpyxl: pip install pandas openpyxl")
    df = pd.read_excel(ruta, sheet_name="Lugares", dtype=str, usecols=CAMPOS_EXCEL)
    indice = {}
    for fila in df.to_dict("records"):
        clave = texto(fila.get("ID"))
        if clave and clave not in indice:
            indice[clave] = {c: texto(fila.get(c)) for c in CAMPOS_EXCEL}
    return indice


def leer_overture(ruta):
    indice = {}
    if not ruta or not Path(ruta).exists():
        return indice
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        for fila in csv.DictReader(f):
            indice[texto(fila.get("id"))] = (texto(fila.get("nombre")), numero(fila.get("lat")),
                                             numero(fila.get("lon")))
    return indice


def _coord_escalada(valor, minimo, maximo):
    """Normaliza coordenadas guardadas como enteros (×1e6 o ×1e7) a grados decimales."""
    v = numero(valor)
    if v is None:
        return None
    if minimo <= v <= maximo:
        return v
    for factor in (1e7, 1e6, 1e5):
        candidato = v / factor
        if minimo <= candidato <= maximo:
            return candidato
    return None


def leer_base_caba_gba(ruta):
    indice = {}
    if not ruta or not Path(ruta).exists():
        return indice
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        for fila in csv.DictReader(f):
            # La base OSM/BA Data guarda las coordenadas como enteros (×1e6 o ×1e7, según la fila).
            lat = _coord_escalada(fila.get("latitud"), -55.5, -21.0)
            lon = _coord_escalada(fila.get("longitud"), -74.0, -53.0)
            indice[texto(fila.get("id_origen"))] = (texto(fila.get("nombre")), lat, lon)
    return indice


# ----------------------------------------------------------------------------- muestra
def muestra_estratificada(filas, n=200, minimo=5, semilla=SEMILLA_POR_DEFECTO):
    """Elige `n` filas repartidas por fuente, con semilla fija y mínimo por estrato."""
    grupos = defaultdict(list)
    for r in filas:
        grupos[r.get("fuente") or "sin_fuente"].append(r)
    total = len(filas)
    # 1) Un mínimo por fuente para que ninguna quede sin auditar.
    asignacion = {f: min(len(g), minimo) for f, g in grupos.items()}
    restante = n - sum(asignacion.values())
    # 2) El resto, proporcional al peso de cada fuente (método del mayor resto).
    if restante > 0 and total:
        cuotas = {f: restante * len(grupos[f]) / total for f in grupos}
        for f, cuota in cuotas.items():
            extra = min(int(cuota), len(grupos[f]) - asignacion[f])
            asignacion[f] += extra
        sobra = n - sum(asignacion.values())
        for f, _ in sorted(cuotas.items(), key=lambda kv: kv[1] - int(kv[1]), reverse=True):
            if sobra <= 0:
                break
            if asignacion[f] < len(grupos[f]):
                asignacion[f] += 1
                sobra -= 1
    rng = random.Random(semilla)
    muestra = []
    for fuente in sorted(grupos):
        muestra.extend(rng.sample(grupos[fuente], asignacion[fuente]))
    return muestra, asignacion


# ----------------------------------------------------------------------------- comparación
def provincia_excel(e):
    return normalizar_provincia(e.get("Provincia")) if e else None


def ciudad_consistente(r, e) -> bool:
    """Compara la ciudad/barrio del CSV con los campos equivalentes del Excel (tolerante a la jerarquía)."""
    if not e:
        return False
    candidatos = {norm(e.get("Localidad / barrio")), norm(e.get("Partido (GBA)")),
                  norm(e.get("Ciudad / barrio (original)")), norm(e.get("Zona (macro)"))}
    candidatos.discard("")
    if not candidatos:
        return True                          # el Excel no trae ciudad: no hay nada que contradecir
    propios = {norm(r.get("ciudad")), norm(r.get("barrio"))}
    propios.discard("")
    for c in candidatos:
        for p in propios:
            if c == p or c in p or p in c:
                return True
    return False


def direccion_consistente(r, e):
    """True/False, o None si el Excel no trae dirección (no es un fallo)."""
    if not e:
        return False
    d_excel, d_csv = norm(e.get("Dirección")), norm(r.get("direccion"))
    if not d_excel:
        return None
    return d_excel == d_csv


def coordenadas_consistentes(r, e):
    """True/False, o None si falta alguna coordenada en el Excel (no es un fallo)."""
    if not e:
        return False
    la, lo = numero(e.get("Latitud")), numero(e.get("Longitud"))
    if la is None or lo is None or numero(r.get("latitud")) is None or numero(r.get("longitud")) is None:
        return None
    return coords_cerca(r, la, lo)


def match_fuente_cruda(r, e, overture, caba):
    """True/False, o None si la fuente no tiene archivo crudo disponible."""
    fuente = r.get("fuente")
    if fuente not in ("overture", "osm", "ba_data"):
        return None
    if not e:
        return False
    crudo_id = texto(e.get("ID de origen (OSM / BA Data)"))
    item = (overture if fuente == "overture" else caba).get(crudo_id)
    if not item:
        return False
    nombre, lat, lon = item
    if lat is None or lon is None:
        return True                          # el identificador existe en el crudo; no hay coordenadas para comparar
    if not nombres_coinciden(r.get("nombre"), nombre):
        return False
    if numero(r.get("latitud")) is None or numero(r.get("longitud")) is None:
        return True                          # el CSV no conserva coordenadas (p. ej. BA Data): alcanza el ID
    return coords_cerca(r, lat, lon, tolerancia_km=1.0)


def clave_duplicado(r):
    """Nombre + dirección + provincia; si no hay dirección, coordenadas redondeadas (~10 m)."""
    nombre, provincia, direccion = norm(r.get("nombre")), norm(r.get("provincia")), norm(r.get("direccion"))
    if direccion:
        return (nombre, provincia, direccion)
    la, lo = numero(r.get("latitud")), numero(r.get("longitud"))
    if la is not None and lo is not None:
        return (nombre, provincia, round(la, 4), round(lo, 4))
    return (nombre, provincia, "")


def clave_gruesa(r):
    return (norm(r.get("nombre")), norm(r.get("provincia")), norm(r.get("ciudad")))


def provincia_dudosa(r, e):
    """Motivos por los que la provincia/zona no se puede afirmar del todo."""
    motivos = []
    if (r.get("region") or "").strip() == "Sin confirmar":
        motivos.append("región Sin confirmar")
    if (r.get("ciudad") or "").strip().lower() == "sin confirmar":
        motivos.append("ciudad Sin confirmar")
    if e and texto(e.get("Provincia")) == "Buenos Aires / CABA (confirmar)":
        motivos.append("provincia a confirmar en el Excel")
    elif e and provincia_excel(e) != normalizar_provincia(r.get("provincia")):
        motivos.append("provincia distinta al Excel")
    return motivos


# ----------------------------------------------------------------------------- informe
def _pct(parte, total):
    return (100.0 * parte / total) if total else 0.0


def _fmt(n):
    return format(n, ",").replace(",", ".")


def auditar(filas, muestra, asignacion, excel, overture, caba, ruta_excel, ruta_overture, ruta_caba):
    total = len(filas)
    conteo_exacto = Counter(clave_duplicado(r) for r in filas)
    grupos_exactos = {k: v for k, v in conteo_exacto.items() if v > 1}
    extra_exacto = sum(v - 1 for v in grupos_exactos.values())
    conteo_grueso = Counter(clave_gruesa(r) for r in filas)
    grupos_gruesos = {k: v for k, v in conteo_grueso.items() if v > 1}

    resumen = defaultdict(Counter)
    casos = []
    for r in muestra:
        fuente = r.get("fuente") or "sin_fuente"
        e = excel.get(texto(r.get("id_origen")))
        resumen[fuente]["muestra"] += 1
        trazable = bool(e) and norm(texto(e.get("Nombre"))[:300]) == norm(r.get("nombre"))
        resumen[fuente]["trazable"] += int(trazable)
        resumen[fuente]["fuente_ok"] += int(bool(e) and fuente_tipo(e.get("Fuente(s)")) == fuente)
        resumen[fuente]["provincia_ok"] += int(bool(e) and provincia_excel(e) == normalizar_provincia(r.get("provincia")))

        ciudad = ciudad_consistente(r, e) if e else False
        resumen[fuente]["ciudad_ok"] += int(ciudad)
        direccion = direccion_consistente(r, e)
        if direccion is not None:
            resumen[fuente]["direccion_comparable"] += 1
            resumen[fuente]["direccion_ok"] += int(direccion)
        coords = coordenadas_consistentes(r, e)
        if coords is not None:
            resumen[fuente]["coords_comparable"] += 1
            resumen[fuente]["coords_ok"] += int(coords)
        crudo = match_fuente_cruda(r, e, overture, caba)
        if crudo is not None:
            resumen[fuente]["crudo_comparable"] += 1
            resumen[fuente]["crudo_ok"] += int(crudo)
        resumen[fuente]["duplicado"] += int(conteo_exacto[clave_duplicado(r)] > 1)
        motivos = provincia_dudosa(r, e)
        resumen[fuente]["dudosa"] += int(bool(motivos))
        if motivos or not trazable:
            casos.append({
                "id": r.get("id_origen"), "nombre": r.get("nombre"), "fuente": fuente,
                "provincia": r.get("provincia"), "ciudad": r.get("ciudad"),
                "trazable": trazable, "motivos": motivos or ([] if trazable else ["no está en el Excel"]),
            })
    poblacion = Counter(r.get("fuente") or "sin_fuente" for r in filas)
    for fuente, c in resumen.items():
        c["poblacion"] = poblacion[fuente]
    return {
        "resumen": dict(resumen),
        "casos": casos,
        "grupos_exactos": len(grupos_exactos),
        "extra_exacto": extra_exacto,
        "grupos_gruesos": len(grupos_gruesos),
        "extra_grueso": sum(v - 1 for v in grupos_gruesos.values()),
        "asignacion": asignacion,
        "archivos": {
            "excel": str(ruta_excel) if ruta_excel and Path(ruta_excel).exists() else "",
            "overture": str(ruta_overture) if ruta_overture and Path(ruta_overture).exists() else "",
            "caba_gba": str(ruta_caba) if ruta_caba and Path(ruta_caba).exists() else "",
        },
    }


def escribir_reporte(ruta, informe, n, semilla):
    resumen = informe["resumen"]
    orden = sorted(resumen, key=lambda f: -resumen[f]["poblacion"])
    total_m = sum(c["muestra"] for c in resumen.values())
    def suma(clave):
        return sum(c[clave] for c in resumen.values())
    lineas = [
        "# Auditoría por muestreo de la base nacional",
        "",
        "- **Fecha:** %s" % date.today().isoformat(),
        "- **Muestra:** %s casos estratificados por fuente, semilla fija `%s`." % (_fmt(total_m), semilla),
        "- **Población:** %s lugares." % _fmt(sum(c["poblacion"] for c in resumen.values())),
        "- **Método:** sin consultas a internet. Se compara cada caso con la planilla de origen por `ID` y, "
        "cuando hay archivo crudo, con Overture u OSM/BA Data por identificador, nombre y coordenadas "
        "(tolerancia 1 km).",
        "",
        "## Resultado global",
        "",
        "| Indicador | Resultado |",
        "|---|---:|",
        "| Rastreables en el Excel de origen | %d/%d (%.1f %%) |" % (suma("trazable"), total_m, _pct(suma("trazable"), total_m)),
        "| Fuente coincide con el Excel | %d/%d (%.1f %%) |" % (suma("fuente_ok"), total_m, _pct(suma("fuente_ok"), total_m)),
        "| Provincia coincide con el Excel | %d/%d (%.1f %%) |" % (suma("provincia_ok"), total_m, _pct(suma("provincia_ok"), total_m)),
        "| Ciudad/barrio coherente | %d/%d (%.1f %%) |" % (suma("ciudad_ok"), total_m, _pct(suma("ciudad_ok"), total_m)),
        "| Dirección coincide (sobre las comparables) | %d/%d (%.1f %%) |" % (
            suma("direccion_ok"), suma("direccion_comparable"), _pct(suma("direccion_ok"), suma("direccion_comparable"))),
        "| Coordenadas coinciden (sobre las comparables) | %d/%d (%.1f %%) |" % (
            suma("coords_ok"), suma("coords_comparable"), _pct(suma("coords_ok"), suma("coords_comparable"))),
        "| Aparece en el archivo crudo (sobre las comparables) | %d/%d (%.1f %%) |" % (
            suma("crudo_ok"), suma("crudo_comparable"), _pct(suma("crudo_ok"), suma("crudo_comparable"))),
        "| Duplicados exactos en la muestra | %d/%d (%.1f %%) |" % (
            suma("duplicado"), total_m, _pct(suma("duplicado"), total_m)),
        "| Provincias dudosas en la muestra | %d/%d (%.1f %%) |" % (
            suma("dudosa"), total_m, _pct(suma("dudosa"), total_m)),
        "",
        "## Por fuente",
        "",
        "| Fuente | Población | Muestra | Rastreable | Provincia OK | Ciudad OK | Crudo OK | Duplicados | Dudosas |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for fuente in orden:
        c = resumen[fuente]
        lineas.append("| %s | %s | %d | %.0f %% | %.0f %% | %.0f %% | %s | %.0f %% | %.0f %% |" % (
            fuente, _fmt(c["poblacion"]), c["muestra"], _pct(c["trazable"], c["muestra"]),
            _pct(c["provincia_ok"], c["muestra"]), _pct(c["ciudad_ok"], c["muestra"]),
            ("%.0f %%" % _pct(c["crudo_ok"], c["crudo_comparable"])) if c["crudo_comparable"] else "n/d",
            _pct(c["duplicado"], c["muestra"]), _pct(c["dudosa"], c["muestra"])))
    lineas += [
        "",
        "## Duplicados en toda la base",
        "",
        "- Clave estricta (nombre + dirección + provincia; sin dirección, coordenadas a ~10 m): "
        "**%s grupos**, **%s filas extra**." % (_fmt(informe["grupos_exactos"]), _fmt(informe["extra_exacto"])),
        "- Clave gruesa (nombre + provincia + ciudad): **%s grupos**, **%s filas extra**. "
        "La clave gruesa sobrecuenta cadenas con varias sucursales; no se usa para borrar." % (
            _fmt(informe["grupos_gruesos"]), _fmt(informe["extra_grueso"])),
        "",
        "## Casos para revisar en la muestra",
        "",
    ]
    if informe["casos"]:
        lineas += ["| ID | Nombre | Fuente | Provincia | Ciudad | Motivo |", "|---|---|---|---|---|---|"]
        for c in informe["casos"][:40]:
            lineas.append("| %s | %s | %s | %s | %s | %s |" % (
                c["id"], str(c["nombre"])[:45], c["fuente"], c["provincia"], str(c["ciudad"])[:30],
                "; ".join(c["motivos"])))
    else:
        lineas.append("_Ninguno._")
    lineas += [
        "",
        "## Cobertura de archivos",
        "",
        "- Excel de origen: `%s`" % (informe["archivos"]["excel"] or "no disponible"),
        "- Overture crudo: `%s`" % (informe["archivos"]["overture"] or "no disponible"),
        "- OSM/BA Data crudo: `%s`" % (informe["archivos"]["caba_gba"] or "no disponible"),
        "",
        "## Limitaciones",
        "",
        "- No se valida cada localidad contra un mapa en línea: la auditoría es de **trazabilidad** "
        "(¿el dato existe en la fuente?) y de **coherencia interna** (provincia, ciudad, dirección y coordenadas).",
        "- Las fuentes Google Places, guías kosher y guías de celíacos no tienen archivo crudo en el "
        "repositorio; para ellas se informa `n/d` en la columna de archivo crudo.",
        "- Una fila «dudosa» no es un error: marca datos que el sistema ya señala como provisorios "
        "(por ejemplo, región «Sin confirmar»).",
        "",
        "## Conclusión",
        "",
    ]
    trazable = _pct(suma("trazable"), total_m)
    crudo = _pct(suma("crudo_ok"), suma("crudo_comparable"))
    dudosas = _pct(suma("dudosa"), total_m)
    if trazable >= 99 and (suma("crudo_comparable") == 0 or crudo >= 99) and dudosas <= 5:
        lineas.append("**Muestra consistente:** prácticamente todos los casos se rastrean a la planilla y a las "
                      "fuentes crudas, y las dudas de provincia son marginales.")
    else:
        lineas.append("La muestra es mayoritariamente trazable, pero conviene revisar los casos listados antes de "
                      "considerar la base cerrada.")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return ruta


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default=str(CSV_POR_DEFECTO))
    ap.add_argument("--excel", default=str(EXCEL_POR_DEFECTO))
    ap.add_argument("--overture", default=str(OVERTURE_POR_DEFECTO))
    ap.add_argument("--base-caba", default=str(BASE_CABA_GBA))
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--semilla", type=int, default=SEMILLA_POR_DEFECTO)
    ap.add_argument("--reporte")
    a = ap.parse_args(argv)

    ruta_csv = Path(a.csv)
    if not ruta_csv.exists():
        print("No encuentro %s." % ruta_csv)
        return 1
    filas = leer_csv(ruta_csv)
    muestra, asignacion = muestra_estratificada(filas, a.n, semilla=a.semilla)
    print("Muestra: %d casos de %d filas (%s)." % (len(muestra), len(filas), asignacion))

    excel = {}
    if Path(a.excel).exists():
        print("Leyendo el Excel de origen (tarda un poco)...")
        excel = leer_excel(a.excel)
        print("Excel: %d filas indexadas por ID." % len(excel))
    else:
        print("Aviso: no encuentro el Excel %s; la trazabilidad quedará en 0." % a.excel)
    overture = leer_overture(a.overture)
    caba = leer_base_caba_gba(a.base_caba)
    print("Crudos: Overture %d · OSM/BA Data %d." % (len(overture), len(caba)))

    informe = auditar(filas, muestra, asignacion, excel, overture, caba, a.excel, a.overture, a.base_caba)
    ruta_reporte = Path(a.reporte) if a.reporte else (
        RAIZ / "docs" / "pruebas" / ("auditoria_muestra_%s.md" % date.today().isoformat()))
    ruta_reporte = escribir_reporte(ruta_reporte, informe, a.n, a.semilla)
    print("Reporte: %s" % ruta_reporte)
    return 0


if __name__ == "__main__":
    sys.exit(main())
