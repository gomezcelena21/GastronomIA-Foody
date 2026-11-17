"""
Gastro IA ETL - Extraction Module
Extracts data from BA Data, OpenStreetMap, and Mendoza official sources.
"""

import csv
import json
import os
import time
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path


RAW_DIR = Path(__file__).parent.parent / "raw"
RAW_DIR.mkdir(exist_ok=True)


def extract_ba_data():
    """Extract BA Data CABA restaurant data."""
    print("[EXTRACT] BA Data CABA...")
    
    url = "https://cdn.buenosaires.gob.ar/datosabiertos/datasets/ente-de-turismo/oferta-establecimientos-gastronomicos/oferta_gastronomica.csv"
    output_file = RAW_DIR / "ba_data_gastronomica.csv"
    
    if output_file.exists():
        print(f"  Using cached: {output_file}")
    else:
        print(f"  Downloading from: {url}")
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        with open(output_file, "wb") as f:
            f.write(response.content)
        print(f"  Downloaded: {len(response.content)} bytes")
    
    # Read CSV with semicolon delimiter
    df = pd.read_csv(output_file, sep=";", encoding="latin-1", low_memory=False)
    
    # Standardize column names
    df.columns = [c.strip().lower() for c in df.columns]
    
    # Add metadata
    df["_source"] = "ba_data"
    df["_source_url"] = url
    df["_fetched_date"] = datetime.now().strftime("%Y-%m-%d")
    
    print(f"  Records extracted: {len(df)}")
    return df


def extract_osm_region(query_name, bbox, region_name):
    """Extract restaurant data from OpenStreetMap via Overpass API."""
    print(f"[EXTRACT] OSM {region_name}...")
    
    cache_file = RAW_DIR / f"osm_{query_name}.json"
    
    if cache_file.exists():
        print(f"  Using cached: {cache_file}")
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        min_lat, min_lon, max_lat, max_lon = bbox
        query = f'[out:json][timeout:60];(node["amenity"="restaurant"]({min_lat},{min_lon},{max_lat},{max_lon}););out body;>;out skel qt;'
        
        print(f"  Querying Overpass API...")
        encoded_query = requests.utils.quote(query)
        url = f"https://overpass-api.de/api/interpreter?data={encoded_query}"
        
        headers = {"User-Agent": "GastroIA/1.0 (research project)"}
        response = requests.get(url, headers=headers, timeout=120)
        response.raise_for_status()
        
        data = response.json()
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"  Downloaded and cached")
        time.sleep(5)  # Rate limit
    
    # Parse nodes
    nodes = [e for e in data.get("elements", []) if e.get("type") == "node"]
    
    # Convert to DataFrame
    records = []
    for node in nodes:
        tags = node.get("tags", {})
        record = {
            "osm_id": node.get("id"),
            "name": tags.get("name", ""),
            "lat": node.get("lat"),
            "lon": node.get("lon"),
            "cuisine": tags.get("cuisine", ""),
            "phone": tags.get("phone", ""),
            "website": tags.get("website", ""),
            "addr_street": tags.get("addr:street", ""),
            "addr_housenumber": tags.get("addr:housenumber", ""),
            "addr_suburb": tags.get("addr:suburb", ""),
            "addr_city": tags.get("addr:city", ""),
            "opening_hours": tags.get("opening_hours", ""),
            "diet_vegetarian": tags.get("diet:vegetarian", ""),
            "diet_vegan": tags.get("diet:vegan", ""),
            "diet_gluten_free": tags.get("diet:gluten_free", ""),
            "_source": "osm",
            "_region": region_name,
            "_fetched_date": datetime.now().strftime("%Y-%m-%d"),
        }
        records.append(record)
    
    df = pd.DataFrame(records)
    print(f"  Records extracted: {len(df)}")
    return df


def extract_mendoza():
    """Extract Mendoza official gastronomy data."""
    print("[EXTRACT] Mendoza Oficial...")
    
    url = "https://datosabiertos.mendoza.gov.ar/dataset/5487232e-ddf2-49e2-b1ab-ac258f1b8dde/resource/3365b11a-e0a4-4085-a1de-44a8834a8128/download/gastronomia-locales-julio-2019.csv"
    output_file = RAW_DIR / "mendoza_gastronomia.csv"
    
    if output_file.exists():
        print(f"  Using cached: {output_file}")
    else:
        print(f"  Downloading from: {url}")
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        with open(output_file, "wb") as f:
            f.write(response.content)
        print(f"  Downloaded: {len(response.content)} bytes")
    
    df = pd.read_csv(output_file, sep=";", encoding="latin-1", low_memory=False)
    df.columns = [c.strip().lower() for c in df.columns]
    
    df["_source"] = "mendoza_official"
    df["_source_url"] = url
    df["_fetched_date"] = datetime.now().strftime("%Y-%m-%d")
    
    print(f"  Records extracted: {len(df)}")
    return df


def extract_all():
    """Extract data from all sources."""
    print("=" * 60)
    print("PHASE 1: EXTRACTION")
    print("=" * 60)
    
    results = {}
    
    # BA Data
    try:
        results["ba_data"] = extract_ba_data()
    except Exception as e:
        print(f"  ERROR extracting BA Data: {e}")
        results["ba_data"] = pd.DataFrame()
    
    # OSM regions
    osm_regions = {
        "caba": {"bbox": (-34.70, -58.55, -34.47, -58.32), "name": "CABA"},
        "pba": {"bbox": (-35.10, -59.10, -34.70, -58.32), "name": "Provincia Buenos Aires"},
        "cordoba": {"bbox": (-31.50, -64.25, -31.35, -64.05), "name": "Cordoba Capital"},
        "mendoza_osm": {"bbox": (-33.00, -68.95, -32.85, -68.75), "name": "Mendoza Capital"},
        "rosario": {"bbox": (-33.05, -60.75, -32.90, -60.60), "name": "Rosario"},
    }
    
    for key, config in osm_regions.items():
        try:
            results[f"osm_{key}"] = extract_osm_region(key, config["bbox"], config["name"])
        except Exception as e:
            print(f"  ERROR extracting OSM {config['name']}: {e}")
            results[f"osm_{key}"] = pd.DataFrame()
    
    # Mendoza Official
    try:
        results["mendoza_official"] = extract_mendoza()
    except Exception as e:
        print(f"  ERROR extracting Mendoza: {e}")
        results["mendoza_official"] = pd.DataFrame()
    
    # Summary
    total = sum(len(df) for df in results.values())
    print(f"\n[EXTRACT] Total records extracted: {total}")
    
    return results


if __name__ == "__main__":
    data = extract_all()
    for name, df in data.items():
        print(f"  {name}: {len(df)} records")
