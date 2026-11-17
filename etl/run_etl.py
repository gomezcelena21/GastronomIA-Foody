"""
Gastro IA ETL - Main Pipeline
Orchestrates the complete ETL process.
"""

import sys
import os
from datetime import datetime

# Add modules to path
sys.path.insert(0, os.path.dirname(__file__))

from modules.extract import extract_all
from modules.transform import transform_all
from modules.validate import validate_all
from modules.dedup import deduplicate_all
from modules.load import load_all


def run_etl():
    """Execute the complete ETL pipeline."""
    print("=" * 60)
    print("GASTRO IA - ETL PIPELINE")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    start_time = datetime.now()
    
    # Phase 1: Extraction
    extracted_data = extract_all()
    
    # Phase 2: Transformation
    transformed_data = transform_all(extracted_data)
    
    # Phase 3: Validation
    validated_data, validation_stats = validate_all(transformed_data)
    
    # Phase 4: Deduplication
    deduped_data, duplicates_removed = deduplicate_all(validated_data)
    
    # Phase 5: Load
    loaded_count = load_all(deduped_data)
    
    # Final summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 60)
    print("ETL PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Duration: {duration:.1f} seconds")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Finished: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    return {
        "duration_seconds": duration,
        "extracted": {k: len(v) for k, v in extracted_data.items()},
        "validated": validation_stats,
        "duplicates_removed": duplicates_removed,
        "loaded": loaded_count,
    }


if __name__ == "__main__":
    result = run_etl()
    print("\nFinal result:")
    for key, value in result.items():
        print(f"  {key}: {value}")
