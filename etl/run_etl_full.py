import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from modules.extract import extract_all
from modules.transform import transform_all
from modules.validate import validate_all
from modules.dedup import deduplicate_all
from modules.load import load_all

# Step 1: Extract
print("Step 1: Extract...")
extracted = extract_all()
print("Extraction complete")

# Step 2: Transform
print("\nStep 2: Transform...")
transformed = transform_all(extracted)
print("Transformation complete")

# Step 3: Validate
print("\nStep 3: Validate...")
validated, stats = validate_all(transformed)
print("Validation complete")

# Step 4: Deduplicate
print("\nStep 4: Deduplicate...")
deduped, removed = deduplicate_all(validated)
print("Deduplication complete")

# Step 5: Load
print("\nStep 5: Load...")
loaded = load_all(deduped)
print("Load complete")

# Summary
print("\n" + "=" * 60)
print("FINAL SUMMARY")
print("=" * 60)
for k, v in stats.items():
    print(f"  {k}: {v['valid']}/{v['total']} valid")
print(f"\nDuplicates removed: {removed}")
print(f"Records loaded: {loaded}")
