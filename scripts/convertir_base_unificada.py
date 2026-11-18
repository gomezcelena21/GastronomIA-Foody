#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convierte la «Base unificada de restricciones - Argentina» (Excel, ~96.000 lugares) al CSV que carga el sistema.

    python scripts/convertir_base_unificada.py Base_Unificada_Restricciones_Argentina.xlsx
    python scripts/convertir_base_unificada.py ARCHIVO.xlsx --alcance caba-gba          # solo CABA y GBA
    python scripts/convertir_base_unificada.py ARCHIVO.xlsx --incluir-baja                # incluye lugares de Overture con confianza baja
    python scripts/convertir_base_unificada.py ARCHIVO.xlsx --sin-google                  # excluye los lugares que solo vienen de Google Places

Genera:
  data/dataset_unificado_<alcance>.csv   (lo que carga scripts/cargar_base_unificada.py)
  backend/zonas_dataset.py               (barrios, localidades y partidos que reconoce el modo sin IA)

Decisiones de calidad (todas se pueden cambiar con las opciones de arriba):
  - Alcance por defecto: toda la Argentina (lo que cubre hoy el sistema: HU-03). «caba-gba» genera solo el recorte de CABA y GBA.
  - Se excluyen los lugares de Overture con confianza baja (< 0,5), salvo los que traen dato de restricción.
  - Las restricciones con «(inferido)» quedan marcadas como inferidas; «sin datos» queda vacío (NO es «no»).
  - De los lugares que vienen de Google Places NO se guardan calificación, reseñas, horarios ni teléfono: los términos de
    la Places API limitan guardar esos datos. Ver el aviso en docs/analisis_dataset.md.
  - Coordenadas inválidas o imprecisas se descartan (el lugar queda sin ubicación en el mapa).
  - Solo se exportan lugares de Argentina: se descarta la fila si la provincia del Excel no es una de las 24
    jurisdicciones argentinas o si sus coordenadas válidas caen fuera del recuadro del país. Una dirección con
    nombre extranjero («Montevideo 1480») no es motivo de descarte: la calle es de CABA.
Requiere pandas y openpyxl (solo para esta conversión: el CSV resultante no los necesita).
"""
import argparse
import csv
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))
from geografia import coordenadas_en_argentina, normalizar_provincia  # noqa: E402

REGIONES = {"caba-gba": {"CABA", "GBA", "CABA/GBA (confirmar)"}, "argentina": None}


def norm(texto) -> str:
    s = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s.lower()).strip()


def vacio(v) -> bool:
    return v is None or (isinstance(v, float) and v != v) or str(v).strip() in ("", "nan", "None")


def limpio(v, maximo=None):
    if vacio(v):
        return ""
    s = re.sub(r"\s+", " ", str(v)).strip()
    return s[:maximo] if maximo else s


# ----------------------------------------------------------------------------- vocabulario de cocinas
# Tipo de lugar (columna «Tipo de lugar») -> tokens de cocina del sistema (los mismos que entiende el intérprete y Gemini)
TIPO_A_COCINAS = {
    "pizzeria": ["pizzeria", "pizza"], "panaderia": ["panaderia"], "heladeria": ["heladeria"],
    "cafeteria": ["cafe"], "cafe": ["cafe"], "hamburgueseria": ["hamburguesa"], "parrilla": ["parrilla"],
    "bar y parrilla": ["parrilla"], "sushi": ["japonesa", "sushi"], "restaurante japones": ["japonesa", "sushi"],
    "pasteleria": ["pasteleria"], "postres": ["pasteleria"], "chocolateria": ["pasteleria"],
    "sandwicheria": ["sandwicheria"], "restaurante italiano": ["italiana"], "restaurante mexicano": ["mexicana"],
    "restaurante peruano": ["peruana"], "restaurante chino": ["china"], "restaurante argentino": ["argentina"],
    "restaurante vegetariano": ["vegetariana", "saludable"], "restaurante vegano": ["vegana", "saludable"],
    "comida rapida": ["comida_rapida"], "rotiseria / fiambreria": ["rotiseria"], "polleria": ["pollo"],
    "empanadas": ["empanadas"], "restaurante de mariscos": ["mariscos"],
}
# Cocina (columna «Cocina», en inglés o español) -> tokens del sistema (además se conserva el valor original en minúscula)
COCINA_A_CANONICAS = {
    "pizza": ["pizzeria", "pizza"], "pizzeria": ["pizzeria", "pizza"], "burger": ["hamburguesa"], "hamburguesa": ["hamburguesa"],
    "coffee shop": ["cafe"], "coffee_shop": ["cafe"], "cafe": ["cafe"], "italian": ["italiana"], "italiana": ["italiana"],
    "pasta": ["italiana"], "chinese": ["china"], "china": ["china"], "sushi": ["japonesa", "sushi"], "japanese": ["japonesa"],
    "japonesa": ["japonesa"], "mexican": ["mexicana"], "mexicana": ["mexicana"], "empanada": ["empanadas"], "empanadas": ["empanadas"],
    "steak house": ["parrilla"], "steak_house": ["parrilla"], "grill": ["parrilla"], "barbecue": ["parrilla"], "parrilla": ["parrilla"],
    "sandwich": ["sandwicheria"], "sandwicheria": ["sandwicheria"], "argentinian": ["argentina"], "argentina": ["argentina"],
    "fast food": ["comida_rapida"], "fast_food": ["comida_rapida"], "ice cream": ["heladeria"], "ice_cream": ["heladeria"],
    "bakery": ["panaderia"], "vegetarian": ["vegetariana", "saludable"], "vegan": ["vegana", "saludable"],
}
IGNORAR_COCINA = {"", "no especificado", "nan"}


def tokens_cocina(tipo, cocina):
    """Lista de tokens de cocina sin repetir: los del tipo de lugar + los de la columna Cocina (original y traducido)."""
    salida = []

    def agregar(t):
        if t and t not in salida:
            salida.append(t)

    for t in TIPO_A_COCINAS.get(norm(tipo), []):
        agregar(t)
    for crudo in re.split(r"[;,]", limpio(cocina)):
        k = norm(crudo)
        if k in IGNORAR_COCINA:
            continue
        for t in COCINA_A_CANONICAS.get(k, []):
            agregar(t)
        agregar(k.replace(" ", "_"))
    return salida[:8]


def categoria(tipo) -> str:
    t = norm(tipo)
    if t in ("cafeteria", "cafe"):
        return "cafe"
    if any(x in t for x in ("pub", "gastropub")):
        return "pub"
    if any(x in t for x in ("bar", "cerveceria", "vineria", "bodega")) and "parrilla" not in t:
        return "bar"
    return "restaurant"


# ----------------------------------------------------------------------------- restricciones
def restriccion(valor):
    """(valor, inferido): True = ofrece, False = la fuente dice que no, None = sin datos (NO significa que no la ofrezca)."""
    v = norm(valor)
    if v in ("si", "solo", "con opciones"):
        return True, False
    if v == "con opciones (inferido)":
        return True, True
    if v == "no":
        return False, False
    return None, False


def a_texto_bool(v):
    return "" if v is None else ("t" if v else "f")


# ----------------------------------------------------------------------------- zona, coordenadas y fuente
def zona(region, localidad, partido, ciudad_original, macro, provincia=None):
    """(provincia, ciudad, barrio). `ciudad` es lo que filtra la búsqueda (ILIKE), por eso en GBA incluye el partido."""
    loc, par = limpio(localidad), limpio(partido)
    if region == "CABA":
        barrio = loc or limpio(ciudad_original)
        barrio = "" if norm(barrio) in ("caba", "capital federal") else barrio
        return "CABA", barrio or "CABA", barrio or ""
    if region == "GBA":
        if loc and par and norm(loc) != norm(par):
            return "Buenos Aires", ("%s (%s)" % (loc, par))[:200], loc
        nombre = loc or par or limpio(macro) or "GBA"
        return "Buenos Aires", nombre, nombre
    if region == "Interior":
        # El interior usa la provincia del Excel y la localidad como ciudad/municipio.
        prov = limpio(provincia)
        if not prov or norm(prov) == "buenos aires / caba (confirmar)":
            prov = "Sin confirmar"
        nombre = loc or limpio(ciudad_original) or limpio(macro) or prov
        return prov, nombre[:200], (loc or nombre)[:200]
    if region == "CABA/GBA (confirmar)":
        return "Buenos Aires", "Sin confirmar", ""
    return "", "", ""


def jerarquia(region, partido, macro, provincia=None):
    """(region, partido, zona): la jerarquía Región > Partido > Zona del Excel (CABA; GBA con sus partidos agrupados en Norte, Oeste y Sur)."""
    if region == "CABA":
        return "CABA", "", "CABA"
    if region == "GBA":
        return "GBA", limpio(partido), limpio(macro) or "GBA (sin partido)"
    if region == "Interior":
        # La zona macro del interior es la provincia (Córdoba, Santa Fe, Mendoza...).
        return "Interior", limpio(partido), limpio(macro) or limpio(provincia) or "Sin confirmar"
    return "Sin confirmar", "", "Sin confirmar"


def coordenadas(lat, lon, estado):
    """Descarta las inválidas o imprecisas y las que caen fuera de Argentina."""
    e = norm(estado)
    if vacio(lat) or vacio(lon) or e.startswith(("invalida", "imprecisa", "sin coordenada")):
        return "", ""
    try:
        la, lo = float(lat), float(lon)
    except (TypeError, ValueError):
        return "", ""
    if not coordenadas_en_argentina(la, lo):
        return "", ""
    return "%.6f" % la, "%.6f" % lo


def motivo_fuera_de_argentina(f: dict):
    """Motivo por el que una fila del Excel no es de Argentina, o None.

    Solo se descarta lo que se puede afirmar: una provincia que no es argentina o
    coordenadas válidas que caen fuera del recuadro del país. Los valores de relleno
    (-350/-580) y las coordenadas imprecisas ya se descartan por calidad, no por país.
    """
    provincia = limpio(f.get("Provincia"))
    if provincia and not normalizar_provincia(provincia):
        return "provincia fuera de Argentina"
    estado = norm(f.get("Estado de la coordenada"))
    if not vacio(f.get("Latitud")) and not vacio(f.get("Longitud")) \
            and not estado.startswith(("invalida", "imprecisa", "sin coordenada")) \
            and not coordenadas_en_argentina(f.get("Latitud"), f.get("Longitud")):
        return "coordenadas fuera de Argentina"
    return None


def es_google(fuente) -> bool:
    return "google" in norm(fuente)


def fuente_tipo(fuente) -> str:
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


def baja_confianza(detalle) -> bool:
    return "(baja)" in norm(detalle)


CAMPOS = ["id_origen", "nombre", "provincia", "ciudad", "barrio", "region", "partido", "zona", "direccion", "latitud", "longitud", "cocina", "categoria",
          "telefono", "website", "sin_tacc", "vegetariano", "vegano", "sin_lactosa", "dato_inferido", "fuente", "fecha_dato"]


def fila_a_registro(f: dict, incluir_baja=False, sin_google=False):
    """Una fila de la hoja «Lugares» -> registro del CSV (o None si se descarta)."""
    if motivo_fuera_de_argentina(f):
        return None
    nombre = limpio(f.get("Nombre"), 300)
    if not nombre:
        return None
    fuente = limpio(f.get("Fuente(s)"))
    tipo_fuente = fuente_tipo(fuente)
    if sin_google and tipo_fuente == "google_places":
        return None
    valores = {k: restriccion(f.get(c)) for k, c in (("tacc", "Sin TACC"), ("veg", "Vegetariano"), ("vegan", "Vegano"), ("lact", "Sin lactosa / lácteos"))}
    hay_dato = any(v is True for v, _ in valores.values())
    if baja_confianza(f.get("Detalle de la evidencia")) and not incluir_baja and not hay_dato:
        return None
    provincia, ciudad, barrio = zona(limpio(f.get("Región")), f.get("Localidad / barrio"), f.get("Partido (GBA)"),
                                     f.get("Ciudad / barrio (original)"), f.get("Zona (macro)"), f.get("Provincia"))
    region, partido, zona_macro = jerarquia(limpio(f.get("Región")), f.get("Partido (GBA)"), f.get("Zona (macro)"),
                                            f.get("Provincia"))
    lat, lon = coordenadas(f.get("Latitud"), f.get("Longitud"), f.get("Estado de la coordenada"))
    solo_google = es_google(fuente)                      # de Google no se guardan teléfono ni web (ver aviso en el encabezado)
    return {
        "id_origen": limpio(f.get("ID")), "nombre": nombre, "provincia": provincia, "ciudad": ciudad, "barrio": barrio,
        "region": region, "partido": partido, "zona": zona_macro,
        "direccion": limpio(f.get("Dirección"), 500), "latitud": lat, "longitud": lon,
        "cocina": ";".join(tokens_cocina(f.get("Tipo de lugar"), f.get("Cocina"))), "categoria": categoria(f.get("Tipo de lugar")),
        "telefono": "" if solo_google else limpio(f.get("Teléfono"), 50),
        "website": "" if solo_google else limpio(f.get("Sitio web / Instagram"), 300),
        "sin_tacc": a_texto_bool(valores["tacc"][0]), "vegetariano": a_texto_bool(valores["veg"][0]),
        "vegano": a_texto_bool(valores["vegan"][0]), "sin_lactosa": a_texto_bool(valores["lact"][0]),
        "dato_inferido": "t" if any(inf for v, inf in valores.values() if v) else "f",
        "fuente": tipo_fuente, "fecha_dato": limpio(f.get("Fecha de consulta"))[:10],
    }


# ----------------------------------------------------------------------------- zonas para el modo sin IA
ZONAS_GENERICAS = {"centro", "norte", "sur", "este", "oeste", "caba", "sin confirmar", "buenos aires", "gba", "ciudad", "barrio",
                   "pueblo", "general", "capital", "interior", "villa", "parque", "plaza", "puerto", "lomas", "san", "santa"}


def zonas_reconocibles(registros, minimo=3):
    """Barrios, localidades y partidos de la base con al menos `minimo` lugares (más de 3 letras y no genéricos)."""
    cuenta, variantes = Counter(), defaultdict(Counter)
    for r in registros:
        nombres = {r["barrio"]}
        m = re.match(r"^(.*) \((.*)\)$", r["ciudad"])
        if m:
            nombres |= {m.group(1), m.group(2)}
        for nombre in nombres:
            k = norm(nombre)
            if len(k) >= 4 and k not in ZONAS_GENERICAS:
                cuenta[k] += 1
                variantes[k][nombre] += 1
    nombres = [variantes[k].most_common(1)[0][0] for k, c in cuenta.items() if c >= minimo]
    return sorted(set(nombres), key=lambda x: (-len(x), x))


def escribir_zonas(zonas, ruta):
    with open(ruta, "w", encoding="utf-8") as f:
        f.write('# -*- coding: utf-8 -*-\n"""Zonas que reconoce el modo sin IA. GENERADO por scripts/convertir_base_unificada.py (%s): no editar a mano."""\n'
                % date.today().isoformat())
        f.write("ZONAS = (\n")
        for z in zonas:
            f.write("    %r,\n" % z)
        f.write(")\n")


# ----------------------------------------------------------------------------- programa principal
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("excel")
    ap.add_argument("--alcance", choices=list(REGIONES), default="argentina")
    ap.add_argument("--incluir-baja", action="store_true")
    ap.add_argument("--sin-google", action="store_true")
    ap.add_argument("--salida")
    a = ap.parse_args(argv)
    try:
        import pandas as pd
    except ImportError:
        print("Falta pandas y openpyxl: pip install pandas openpyxl")
        return 1
    print("Leyendo la hoja «Lugares» (tarda un poco)...")
    df = pd.read_excel(a.excel, sheet_name="Lugares", dtype=str)
    permitidas = REGIONES[a.alcance]
    registros, descartes = [], Counter()
    for fila in df.to_dict("records"):
        if permitidas is not None and limpio(fila.get("Región")) not in permitidas:
            descartes["fuera de alcance"] += 1
            continue
        motivo = motivo_fuera_de_argentina(fila)
        if motivo:
            descartes[motivo] += 1
            continue
        r = fila_a_registro(fila, a.incluir_baja, a.sin_google)
        if r is None:
            descartes["confianza baja o excluido"] += 1
        else:
            registros.append(r)
    salida = Path(a.salida) if a.salida else RAIZ / "data" / ("dataset_unificado_%s.csv" % a.alcance.replace("-", "_").upper())
    with open(salida, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(registros)
    zonas = zonas_reconocibles(registros if a.alcance == "argentina"
                               else [r for r in registros if r["provincia"] in ("CABA", "Buenos Aires")])
    escribir_zonas(zonas, RAIZ / "backend" / "zonas_dataset.py")
    print("\nTotal en la hoja: %d | exportados: %d | descartados: %s" % (len(df), len(registros), dict(descartes)))
    print("Por fuente:", dict(Counter(r["fuente"] for r in registros)))
    print("Con sin TACC: %d | vegano: %d | vegetariano: %d | con ubicación: %d | con dirección: %d" % (
        sum(r["sin_tacc"] == "t" for r in registros), sum(r["vegano"] == "t" for r in registros),
        sum(r["vegetariano"] == "t" for r in registros), sum(bool(r["latitud"]) for r in registros), sum(bool(r["direccion"]) for r in registros)))
    print("Zonas reconocibles para el modo sin IA: %d" % len(zonas))
    print("CSV:", salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
