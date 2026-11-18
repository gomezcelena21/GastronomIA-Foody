# -*- coding: utf-8 -*-
"""Geografía de Argentina para validar la cobertura y los datos, sin salir a internet.

La base solo tiene establecimientos de Argentina. Este módulo centraliza:
  - las 24 jurisdicciones argentinas (23 provincias + CABA) y sus alias;
  - los países y las ciudades del exterior que se rechazan en el chat;
  - el recuadro geográfico de Argentina para descartar coordenadas de otro país.

No usa dependencias externas: lo importan el backend, los scripts de conversión/carga y la auditoría.
"""
import re
import unicodedata
from typing import Optional

# --------------------------------------------------------------- provincias
# Nombres canónicos: los que se guardan en la columna `province` de la base.
PROVINCIAS = (
    "CABA",
    "Buenos Aires",
    "Catamarca",
    "Chaco",
    "Chubut",
    "Córdoba",
    "Corrientes",
    "Entre Ríos",
    "Formosa",
    "Jujuy",
    "La Pampa",
    "La Rioja",
    "Mendoza",
    "Misiones",
    "Neuquén",
    "Río Negro",
    "Salta",
    "San Juan",
    "San Luis",
    "Santa Cruz",
    "Santa Fe",
    "Santiago del Estero",
    "Tierra del Fuego",
    "Tucumán",
)


def norm(texto) -> str:
    """Minúsculas, sin tildes y con espacios simples (mismo criterio que el backend)."""
    t = unicodedata.normalize("NFD", str(texto or ""))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t.lower()).strip()


ALIAS_PROVINCIA = {norm(p): p for p in PROVINCIAS}
ALIAS_PROVINCIA.update({
    # CABA
    "caba": "CABA",
    "capital federal": "CABA",
    "ciudad autonoma de buenos aires": "CABA",
    "ciudad de buenos aires": "CABA",
    "ciudad autonoma de la ciudad de buenos aires": "CABA",
    # Buenos Aires y su conurbano
    "buenos aires / caba (confirmar)": "Buenos Aires",
    "provincia de buenos aires": "Buenos Aires",
    "pba": "Buenos Aires",
    "gba": "Buenos Aires",
    "gran buenos aires": "Buenos Aires",
    "conurbano": "Buenos Aires",
    "conurbano bonaerense": "Buenos Aires",
    # Nombre completo de la provincia de Tierra del Fuego
    "tierra del fuego, antartida e islas del atlantico sur": "Tierra del Fuego",
})


def normalizar_provincia(valor) -> Optional[str]:
    """Devuelve el nombre canónico de una provincia argentina, o None si no lo es."""
    n = norm(valor)
    n = re.sub(r"\s*,\s*argentina$", "", n)
    n = re.sub(r"\s+argentina$", "", n)
    if n.startswith("provincia de "):
        n = n[len("provincia de "):]
    return ALIAS_PROVINCIA.get(n)


def es_provincia_argentina(valor) -> bool:
    return normalizar_provincia(valor) is not None


# ------------------------------------------------------ lugares del exterior
# Países (nombre normalizado -> nombre para mostrar). Se rechazan en el chat.
PAISES = {
    "uruguay": "Uruguay", "chile": "Chile", "brasil": "Brasil", "paraguay": "Paraguay",
    "bolivia": "Bolivia", "peru": "Perú", "colombia": "Colombia", "ecuador": "Ecuador",
    "venezuela": "Venezuela", "mexico": "México", "espana": "España", "italia": "Italia",
    "francia": "Francia", "alemania": "Alemania", "portugal": "Portugal",
    "estados unidos": "Estados Unidos", "eeuu": "Estados Unidos", "canada": "Canadá",
    "cuba": "Cuba", "republica dominicana": "República Dominicana", "panama": "Panamá",
    "costa rica": "Costa Rica", "guatemala": "Guatemala", "honduras": "Honduras",
    "el salvador": "El Salvador", "nicaragua": "Nicaragua", "puerto rico": "Puerto Rico",
    "reino unido": "Reino Unido", "inglaterra": "Inglaterra", "irlanda": "Irlanda",
    "suiza": "Suiza", "austria": "Austria", "belgica": "Bélgica", "paises bajos": "Países Bajos",
    "holanda": "Países Bajos", "dinamarca": "Dinamarca", "suecia": "Suecia", "noruega": "Noruega",
    "finlandia": "Finlandia", "rusia": "Rusia", "ucrania": "Ucrania", "polonia": "Polonia",
    "grecia": "Grecia", "turquia": "Turquía", "marruecos": "Marruecos", "egipto": "Egipto",
    "sudafrica": "Sudáfrica", "australia": "Australia", "nueva zelanda": "Nueva Zelanda",
    "japon": "Japón", "china": "China", "corea del sur": "Corea del Sur", "india": "India",
    "tailandia": "Tailandia", "vietnam": "Vietnam", "israel": "Israel",
    "emiratos arabes unidos": "Emiratos Árabes Unidos",
}

# Ciudades del exterior que no se confunden con localidades argentinas. Las ambiguas
# (Lima, La Paz, Asunción, Concepción, Salto...) quedan afuera a propósito: hay
# localidades argentinas con esos nombres y rechazarlas sería un error.
CIUDADES_FUERA = {
    "montevideo": "Montevideo", "punta del este": "Punta del Este",
    "colonia del sacramento": "Colonia del Sacramento", "santiago de chile": "Santiago de Chile",
    "valparaiso": "Valparaíso", "vina del mar": "Viña del Mar", "antofagasta": "Antofagasta",
    "iquique": "Iquique", "la serena": "La Serena", "temuco": "Temuco",
    "puerto montt": "Puerto Montt", "punta arenas": "Punta Arenas", "arica": "Arica",
    "sao paulo": "São Paulo", "rio de janeiro": "Río de Janeiro", "florianopolis": "Florianópolis",
    "brasilia": "Brasilia", "curitiba": "Curitiba", "porto alegre": "Porto Alegre",
    "belo horizonte": "Belo Horizonte", "ciudad del este": "Ciudad del Este",
    "bogota": "Bogotá", "quito": "Quito", "guayaquil": "Guayaquil", "caracas": "Caracas",
    "madrid": "Madrid", "barcelona": "Barcelona", "miami": "Miami", "nueva york": "Nueva York",
    "los angeles": "Los Ángeles", "chicago": "Chicago", "paris": "París", "londres": "Londres",
    "roma": "Roma", "milan": "Milán", "venecia": "Venecia", "lisboa": "Lisboa",
    "tokio": "Tokio", "pekin": "Pekín", "shanghai": "Shanghái", "dubai": "Dubái",
    "ciudad de mexico": "Ciudad de México",
}

LUGARES_FUERA = {**PAISES, **CIUDADES_FUERA}
_RE_FUERA = re.compile(
    r"\b(?:%s)\b" % "|".join(re.escape(c) for c in sorted(LUGARES_FUERA, key=len, reverse=True))
)


def buscar_lugar_extranjero(texto) -> Optional[str]:
    """Nombre para mostrar si `texto` ES un país o ciudad del exterior, o None.

    Es deliberadamente estricto: solo acepta coincidencia completa o al inicio
    («Montevideo», «Montevideo, Uruguay»). Así no se rechazan localidades
    argentinas que contienen un nombre extranjero, como «Concepción del Uruguay»
    (Entre Ríos) o «La Paz» (Mendoza).
    """
    n = norm(texto).strip(" ,.;")
    if not n:
        return None
    if n in LUGARES_FUERA:
        return LUGARES_FUERA[n]
    # «Montevideo, Uruguay» / «Montevideo (Uruguay)»: el lugar empieza con el nombre.
    for clave in sorted(LUGARES_FUERA, key=len, reverse=True):
        if n.startswith(clave + " ") or n.startswith(clave + ",") or n.startswith(clave + " ("):
            return LUGARES_FUERA[clave]
    # «Santiago, Chile»: el país/ciudad aparece como último tramo de la dirección.
    partes = [p.strip(" .;()") for p in re.split(r"[,/]", n) if p.strip(" .;()")]
    for parte in reversed(partes[1:]):
        if parte in LUGARES_FUERA:
            return LUGARES_FUERA[parte]
    return None


def es_lugar_extranjero(texto) -> bool:
    return buscar_lugar_extranjero(texto) is not None


def menciona_lugar_extranjero(texto) -> bool:
    """True si el texto menciona un país o ciudad del exterior en cualquier posición.

    Sirve para revisar textos libres (auditoría), no para validar una zona: nombres
    como «Uruguay» aparecen dentro de localidades argentinas («Concepción del Uruguay»).
    """
    return _RE_FUERA.search(norm(texto)) is not None


# ------------------------------------------------------------- coordenadas
# Recuadro generoso que contiene todo el territorio argentino (incluye islas y Antártida reclamada).
LAT_MIN, LAT_MAX = -55.5, -21.0
LON_MIN, LON_MAX = -74.0, -53.0


def coordenadas_en_argentina(lat, lon) -> bool:
    """True si (lat, lon) cae dentro del recuadro de Argentina (y son números válidos)."""
    try:
        la, lo = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    return LAT_MIN <= la <= LAT_MAX and LON_MIN <= lo <= LON_MAX
