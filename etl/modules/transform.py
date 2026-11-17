"""
Gastro IA ETL - Transformation Module
Transforms and normalizes raw data into the standard schema.
"""

import re
import pandas as pd
from datetime import datetime


# Cuisine mapping: OSM/BA values -> normalized values
CUISINE_MAP = {
    "argentinian": "argentina",
    "regional": "argentina",
    "steak_house": "parrilla",
    "barbecue": "parrilla",
    "grill": "parrilla",
    "italian": "italiana",
    "pizza": "italiana",
    "pasta": "italiana",
    "japanese": "japonesa",
    "sushi": "japonesa",
    "chinese": "china",
    "peruvian": "peruana",
    "mexican": "mexicana",
    "american": "americana",
    "spanish": "espanola",
    "asian": "asiatica",
    "burger": "hamburguesa",
    "coffee_shop": "cafe",
    "french": "francesa",
    "arab": "arabe",
    "indian": "india",
    "thai": "tailandesa",
    "korean": "coreana",
    "greek": "griega",
    "brazilian": "brasileña",
    "vegetarian": "vegetariana",
    "vegan": "vegana",
    "seafood": "mariscos",
    "sushi_japanese": "japonesa",
    "empanada": "empanadas",
    "empanadas": "empanadas",
    "milanesa": "milanesa",
    "pastas": "italiana",
    "minutas": "comida_rapida",
    "delivery": "delivery",
    "panaderia": "panaderia",
    "confiteria": "confiteria",
    "bodegon": "bodegon",
    "vineria": "vinoteca",
    "cerveceria": "cerveceria",
    "heladeria": "heladeria",
}

# Category mapping
CATEGORY_MAP = {
    "restaurante": "restaurant",
    "restaurant": "restaurant",
    "bar": "bar",
    "cafe": "cafe",
    "cafeteria": "cafe",
    "coffee_shop": "cafe",
    "parrillada": "parrilla",
    "parrilla": "parrilla",
    "bodegon": "bodegon",
    "vineria": "vinoteca",
    "confiteria": "confiteria",
    "panaderia": "panaderia",
    "heladeria": "heladeria",
    "cerveceria": "cerveceria",
    "pizza": "pizzeria",
    "pizzeria": "pizzeria",
    "sushi": "sushi",
    "rotiseria": "rotiseria",
    "chocolateria": "chocolateria",
    "@cafe": "cafe",
}


def normalize_cuisine(cuisine_str):
    """Normalize cuisine type string to array of normalized values."""
    if not cuisine_str or pd.isna(cuisine_str):
        return []
    
    cuisine_str = str(cuisine_str).strip().lower()
    
    # Split by common separators
    parts = re.split(r'[;,/]', cuisine_str)
    
    normalized = []
    for part in parts:
        part = part.strip()
        if part in CUISINE_MAP:
            normalized.append(CUISINE_MAP[part])
        elif part and len(part) > 1:
            # Keep as-is if not in map (might be a valid cuisine)
            normalized.append(part)
    
    # Remove duplicates while preserving order
    seen = set()
    result = []
    for c in normalized:
        if c not in seen:
            seen.add(c)
            result.append(c)
    
    return result


def normalize_category(category_str):
    """Normalize category to standard values."""
    if not category_str or pd.isna(category_str):
        return "restaurant"
    
    category_str = str(category_str).strip().lower()
    return CATEGORY_MAP.get(category_str, "restaurant")


def normalize_phone(phone_str):
    """Normalize phone number to Argentine format."""
    if not phone_str or pd.isna(phone_str):
        return None
    
    phone = str(phone_str).strip()
    
    # Remove common prefixes
    phone = re.sub(r'^tel[:\s]*', '', phone, flags=re.IGNORECASE)
    phone = re.sub(r'^telefono[:\s]*', '', phone, flags=re.IGNORECASE)
    
    # Remove non-digit characters except + at start
    digits = re.sub(r'[^\d]', '', phone)
    
    if not digits:
        return None
    
    # Format: if starts with 54, keep as international
    if digits.startswith("54") and len(digits) > 10:
        return f"+{digits}"
    
    # If 8 digits, it's Buenos Aires
    if len(digits) == 8:
        return f"+5411{digits}"
    
    # If starts with 0, remove it and add +54
    if digits.startswith("0"):
        return f"+54{digits[1:]}"
    
    # Default: add +54 prefix
    return f"+54{digits}"


def normalize_address(street, number, city=None, province=None):
    """Build normalized address string."""
    parts = []
    
    if street and not pd.isna(street):
        street = str(street).strip()
        if number and not pd.isna(number):
            parts.append(f"{street} {number}")
        else:
            parts.append(street)
    
    if city and not pd.isna(city):
        parts.append(str(city).strip())
    
    if province and not pd.isna(province):
        parts.append(str(province).strip())
    
    return ", ".join(parts) if parts else None


def transform_ba_data(df):
    """Transform BA Data to standard schema."""
    print("[TRANSFORM] BA Data...")
    
    if df.empty:
        return pd.DataFrame()
    
    result = pd.DataFrame()
    
    # Name
    result["name"] = df["nombre"].apply(lambda x: str(x).strip() if pd.notna(x) else "")
    
    # Location
    result["province"] = "Buenos Aires"
    result["city"] = "Ciudad Autonoma de Buenos Aires"
    result["neighborhood"] = df["barrio"].apply(lambda x: str(x).strip() if pd.notna(x) else None)
    result["address"] = df.apply(
        lambda r: normalize_address(r.get("calle_nombre"), r.get("calle_altura"), None, None),
        axis=1
    )
    
    # Coordinates - BA Data uses comma as decimal separator
    result["latitude"] = pd.to_numeric(
        df["lat"].astype(str).str.replace(",", "."), errors="coerce"
    )
    result["longitude"] = pd.to_numeric(
        df["long"].astype(str).str.replace(",", "."), errors="coerce"
    )
    
    # Cuisine
    result["cuisine_type"] = df["cocina"].apply(normalize_cuisine)
    
    # Category
    result["category"] = df["categoria"].apply(normalize_category)
    
    # Contact
    result["phone"] = df["telefono"].apply(normalize_phone)
    result["email"] = df["mail"].apply(lambda x: str(x).strip() if pd.notna(x) and str(x).strip() else None)
    result["website"] = df["mail"].apply(lambda x: None)  # Not available in this dataset
    
    # Opening hours
    result["opening_hours"] = df["horario"].apply(lambda x: str(x).strip() if pd.notna(x) else None)
    
    # Metadata
    result["source_type"] = "ba_data"
    result["confidence_level"] = "official"
    result["data_date"] = "2019-08-05"
    result["fetched_date"] = df["_fetched_date"].iloc[0] if "_fetched_date" in df.columns else datetime.now().strftime("%Y-%m-%d")
    
    # Features from BA Data
    result["has_vegetarian_options"] = None  # Not available
    result["has_vegan_options"] = None
    result["has_gluten_free_options"] = None
    
    print(f"  Transformed: {len(result)} records")
    return result


def transform_osm(df, region_name):
    """Transform OSM data to standard schema."""
    print(f"[TRANSFORM] OSM {region_name}...")
    
    if df.empty:
        return pd.DataFrame()
    
    result = pd.DataFrame()
    
    # Name
    result["name"] = df["name"].apply(lambda x: str(x).strip() if pd.notna(x) and str(x).strip() else "")
    
    # Location
    province_map = {
        "CABA": "Buenos Aires",
        "Provincia Buenos Aires": "Buenos Aires",
        "Cordoba Capital": "Cordoba",
        "Mendoza Capital": "Mendoza",
        "Rosario": "Santa Fe",
    }
    result["province"] = province_map.get(region_name, "Buenos Aires")
    result["city"] = region_name
    result["neighborhood"] = df["addr_suburb"].apply(lambda x: str(x).strip() if pd.notna(x) and str(x).strip() else None)
    result["address"] = df.apply(
        lambda r: normalize_address(r.get("addr_street"), r.get("addr_housenumber"), None, None),
        axis=1
    )
    
    # Coordinates
    result["latitude"] = pd.to_numeric(df["lat"], errors="coerce")
    result["longitude"] = pd.to_numeric(df["lon"], errors="coerce")
    
    # Cuisine
    result["cuisine_type"] = df["cuisine"].apply(normalize_cuisine)
    
    # Category - all OSM restaurants
    result["category"] = "restaurant"
    
    # Contact
    result["phone"] = df["phone"].apply(normalize_phone)
    result["email"] = None
    result["website"] = df["website"].apply(lambda x: str(x).strip() if pd.notna(x) and str(x).strip() else None)
    
    # Opening hours
    result["opening_hours"] = df["opening_hours"].apply(lambda x: str(x).strip() if pd.notna(x) and str(x).strip() else None)
    
    # Metadata
    result["source_type"] = "osm"
    result["confidence_level"] = "public_source"
    result["data_date"] = datetime.now().strftime("%Y-%m-%d")
    result["fetched_date"] = df["_fetched_date"].iloc[0] if "_fetched_date" in df.columns else datetime.now().strftime("%Y-%m-%d")
    
    # Features from OSM tags
    def has_diet_option(val):
        if pd.isna(val) or not val:
            return None
        val = str(val).lower()
        if val in ("yes", "only", "some"):
            return True
        if val == "no":
            return False
        return None
    
    result["has_vegetarian_options"] = df["diet_vegetarian"].apply(has_diet_option)
    result["has_vegan_options"] = df["diet_vegan"].apply(has_diet_option)
    result["has_gluten_free_options"] = df["diet_gluten_free"].apply(has_diet_option)
    
    print(f"  Transformed: {len(result)} records")
    return result


def transform_mendoza(df):
    """Transform Mendoza official data to standard schema."""
    print("[TRANSFORM] Mendoza Oficial...")
    
    if df.empty:
        return pd.DataFrame()
    
    result = pd.DataFrame()
    
    # Name
    result["name"] = df["nombre de fantasia"].apply(
        lambda x: str(x).strip() if pd.notna(x) and str(x).strip() else ""
    )
    
    # Location
    result["province"] = "Mendoza"
    result["city"] = df["localidad"].apply(
        lambda x: str(x).strip().title() if pd.notna(x) and str(x).strip() else ""
    )
    result["neighborhood"] = None
    result["address"] = df.apply(
        lambda r: normalize_address(
            r.get("calle"),
            r.get("nro."),
            None,
            None
        ),
        axis=1
    )
    
    # No coordinates in Mendoza dataset
    result["latitude"] = None
    result["longitude"] = None
    
    # Cuisine - use rubro as category
    result["cuisine_type"] = [[] for _ in range(len(df))]
    
    # Category
    result["category"] = df["rubro"].apply(normalize_category)
    
    # Contact
    result["phone"] = df["telefonos"].apply(normalize_phone)
    result["email"] = None
    result["website"] = None
    
    # Opening hours
    result["opening_hours"] = None
    
    # Metadata
    result["source_type"] = "mendoza_official"
    result["confidence_level"] = "official"
    result["data_date"] = "2019-07-01"
    result["fetched_date"] = df["_fetched_date"].iloc[0] if "_fetched_date" in df.columns else datetime.now().strftime("%Y-%m-%d")
    
    # Features - not available
    result["has_vegetarian_options"] = None
    result["has_vegan_options"] = None
    result["has_gluten_free_options"] = None
    
    print(f"  Transformed: {len(result)} records")
    return result


def transform_all(extracted_data):
    """Transform all extracted data to standard schema."""
    print("\n" + "=" * 60)
    print("PHASE 2: TRANSFORMATION")
    print("=" * 60)
    
    transformed = {}
    
    # BA Data
    if "ba_data" in extracted_data and not extracted_data["ba_data"].empty:
        transformed["ba_data"] = transform_ba_data(extracted_data["ba_data"])
    
    # OSM regions
    osm_region_map = {
        "osm_caba": "CABA",
        "osm_pba": "Provincia Buenos Aires",
        "osm_cordoba": "Cordoba Capital",
        "osm_mendoza_osm": "Mendoza Capital",
        "osm_rosario": "Rosario",
    }
    
    for key, region in osm_region_map.items():
        if key in extracted_data and not extracted_data[key].empty:
            transformed[key] = transform_osm(extracted_data[key], region)
    
    # Mendoza Official
    if "mendoza_official" in extracted_data and not extracted_data["mendoza_official"].empty:
        transformed["mendoza_official"] = transform_mendoza(extracted_data["mendoza_official"])
    
    # Summary
    total = sum(len(df) for df in transformed.values())
    print(f"\n[TRANSFORM] Total records transformed: {total}")
    
    return transformed
