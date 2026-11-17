"""
Gastro IA ETL - Deduplication Module (Fast Version)
Simple deduplication using name grouping.
"""

import pandas as pd


def deduplicate_single_source(df, source_name):
    """Fast deduplication: remove exact name duplicates within same source."""
    print(f"  [DEDUP] {source_name}...")
    
    if df.empty:
        return df, 0
    
    initial_count = len(df)
    
    # Remove exact name duplicates (keep first occurrence)
    df = df.drop_duplicates(subset=["name"], keep="first").reset_index(drop=True)
    
    removed = initial_count - len(df)
    print(f"    Removed {removed} duplicates")
    return df, removed


def deduplicate_cross_source(all_data):
    """Simple cross-source dedup: remove OSM records that match BA Data by name in CABA."""
    print("[DEDUP] Cross-source deduplication...")
    
    ba_key = "ba_data"
    osm_key = "osm_caba"
    
    if ba_key not in all_data or osm_key not in all_data:
        print("  Skipping: missing data")
        return all_data, 0
    
    ba_df = all_data[ba_key]
    osm_df = all_data[osm_key]
    
    if ba_df.empty or osm_df.empty:
        print("  Skipping: empty")
        return all_data, 0
    
    # Get BA Data names (normalized)
    ba_names = set()
    for name in ba_df["name"]:
        if pd.notna(name) and str(name).strip():
            ba_names.add(str(name).strip().lower())
    
    # Remove OSM records that match BA Data names
    initial_count = len(osm_df)
    osm_df = osm_df[~osm_df["name"].str.lower().isin(ba_names)].reset_index(drop=True)
    removed = initial_count - len(osm_df)
    
    all_data[osm_key] = osm_df
    print(f"  Cross-source duplicates removed: {removed}")
    
    return all_data, removed


def deduplicate_all(validated_data):
    """Run deduplication pipeline."""
    print("\n" + "=" * 60)
    print("PHASE 4: DEDUPLICATION")
    print("=" * 60)
    
    deduped = {}
    total_removed = 0
    
    for source_name, df in validated_data.items():
        deduped_df, removed = deduplicate_single_source(df, source_name)
        deduped[source_name] = deduped_df
        total_removed += removed
    
    deduped, cross_removed = deduplicate_cross_source(deduped)
    total_removed += cross_removed
    
    total_remaining = sum(len(df) for df in deduped.values())
    print(f"\n[DEDUP] Total duplicates removed: {total_removed}")
    print(f"[DEDUP] Total records remaining: {total_remaining}")
    
    return deduped, total_removed
