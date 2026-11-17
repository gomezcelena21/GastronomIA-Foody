"""
Gastro IA ETL - Validation Module
Validates data quality and filters invalid records.
"""

import pandas as pd
import re


def validate_coordinates(lat, lon, province=None):
    """Validate that coordinates are within Argentina bounds."""
    if lat is None or lon is None or pd.isna(lat) or pd.isna(lon):
        return False, "Missing coordinates"
    
    try:
        lat = float(lat)
        lon = float(lon)
    except (ValueError, TypeError):
        return False, "Invalid coordinate format"
    
    # Argentina bounds (approximate)
    if lat < -55.0 or lat > -20.0:
        return False, f"Latitude {lat} out of Argentina bounds"
    if lon < -75.0 or lon > -50.0:
        return False, f"Longitude {lon} out of Argentina bounds"
    
    # Check for zero coordinates
    if lat == 0.0 and lon == 0.0:
        return False, "Coordinates are (0,0)"
    
    return True, "OK"


def validate_name(name):
    """Validate restaurant name."""
    if not name or pd.isna(name):
        return False, "Missing name"
    
    name = str(name).strip()
    
    if len(name) < 2:
        return False, f"Name too short: '{name}'"
    
    if len(name) > 300:
        return False, f"Name too long: {len(name)} chars"
    
    # Check for encoding errors
    encoding_errors = ["ï¿½", "Ã±", "Ã³", "Ã¡", "Ã©", "Ã­"]
    for err in encoding_errors:
        if err in name:
            return False, f"Encoding error in name: '{name}'"
    
    return True, "OK"


def validate_address(address):
    """Validate address."""
    if not address or pd.isna(address):
        return True, "No address (acceptable)"
    
    address = str(address).strip()
    
    if len(address) > 500:
        return False, f"Address too long: {len(address)} chars"
    
    return True, "OK"


def validate_phone(phone):
    """Validate phone number."""
    if not phone or pd.isna(phone):
        return True, "No phone (acceptable)"
    
    phone = str(phone).strip()
    
    # Must start with +54 or have at least 8 digits
    digits = re.sub(r'[^\d]', '', phone)
    
    if len(digits) < 8:
        return False, f"Phone too short: '{phone}'"
    
    if len(digits) > 15:
        return False, f"Phone too long: '{phone}'"
    
    return True, "OK"


def validate_province(province):
    """Validate province is one of our target provinces."""
    valid_provinces = [
        "Buenos Aires",
        "Ciudad Autonoma de Buenos Aires",
        "Cordoba",
        "Mendoza",
        "Santa Fe",
    ]
    
    if not province or pd.isna(province):
        return False, "Missing province"
    
    province = str(province).strip()
    
    if province in valid_provinces:
        return True, "OK"
    
    return False, f"Province not in target list: '{province}'"


def validate_record(row):
    """Validate a complete record. Returns (is_valid, errors_list)."""
    errors = []
    
    # Name validation (required)
    valid, msg = validate_name(row.get("name"))
    if not valid:
        errors.append(f"name: {msg}")
    
    # Province validation (required)
    valid, msg = validate_province(row.get("province"))
    if not valid:
        errors.append(f"province: {msg}")
    
    # Coordinate validation (warning only, not blocking)
    valid, msg = validate_coordinates(row.get("latitude"), row.get("longitude"))
    if not valid:
        # Don't add as error - coordinates are optional for some sources
        pass
    
    # Address validation
    valid, msg = validate_address(row.get("address"))
    if not valid:
        errors.append(f"address: {msg}")
    
    # Phone validation
    valid, msg = validate_phone(row.get("phone"))
    if not valid:
        errors.append(f"phone: {msg}")
    
    return len(errors) == 0, errors


def validate_dataset(df, source_name):
    """Validate an entire dataset. Returns (valid_df, stats)."""
    print(f"[VALIDATE] {source_name}...")
    
    if df.empty:
        print(f"  Empty dataset")
        return df, {"total": 0, "valid": 0, "invalid": 0, "errors": []}
    
    valid_rows = []
    invalid_count = 0
    all_errors = []
    
    for idx, row in df.iterrows():
        is_valid, errors = validate_record(row)
        
        if is_valid:
            valid_rows.append(row)
        else:
            invalid_count += 1
            all_errors.extend([(idx, e) for e in errors])
    
    valid_df = pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame()
    
    stats = {
        "total": len(df),
        "valid": len(valid_df),
        "invalid": invalid_count,
        "errors": all_errors[:20],  # Keep first 20 errors for reporting
    }
    
    print(f"  Total: {stats['total']}")
    print(f"  Valid: {stats['valid']}")
    print(f"  Invalid: {stats['invalid']}")
    
    if all_errors:
        print(f"  Sample errors:")
        for idx, err in all_errors[:5]:
            try:
                print(f"    Row {idx}: {err}")
            except UnicodeEncodeError:
                print(f"    Row {idx}: (encoding error in error message)")
    
    return valid_df, stats


def validate_all(transformed_data):
    """Validate all transformed datasets."""
    print("\n" + "=" * 60)
    print("PHASE 3: VALIDATION")
    print("=" * 60)
    
    validated = {}
    all_stats = {}
    
    for source_name, df in transformed_data.items():
        validated_df, stats = validate_dataset(df, source_name)
        validated[source_name] = validated_df
        all_stats[source_name] = stats
    
    # Summary
    total_valid = sum(s["valid"] for s in all_stats.values())
    total_invalid = sum(s["invalid"] for s in all_stats.values())
    print(f"\n[VALIDATE] Total valid: {total_valid}, Total invalid: {total_invalid}")
    
    return validated, all_stats
