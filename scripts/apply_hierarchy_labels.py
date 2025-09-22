#!/usr/bin/env python
"""Script to help apply hierarchy labels to semantic models based on naming patterns."""

import yaml
import re
from pathlib import Path
from typing import Dict, Any, Optional

# Mapping rules based on common naming patterns
DIMENSION_PATTERNS = {
    # Booking patterns
    r'.*status.*': {'category': 'booking', 'subcategory': 'booking_status'},
    r'.*reservation.*': {'category': 'booking', 'subcategory': 'booking_status'},
    r'.*booking.*': {'category': 'booking', 'subcategory': 'booking_details'},
    
    # Facility patterns
    r'facility_id|facility_.*': {'category': 'facility', 'subcategory': 'facility_details'},
    r'.*parking.*type.*': {'category': 'facility', 'subcategory': 'facility_type'},
    
    # Temporal patterns
    r'.*created.*': {'category': 'temporal', 'subcategory': 'booking_time'},
    r'.*start.*': {'category': 'temporal', 'subcategory': 'parking_time'},
    r'.*end.*': {'category': 'temporal', 'subcategory': 'parking_time'},
    r'.*duration.*': {'category': 'temporal', 'subcategory': 'duration'},
    r'.*lead_time.*': {'category': 'temporal', 'subcategory': 'duration'},
    
    # Renter patterns
    r'.*renter.*|.*customer.*|.*user.*': {'category': 'renter', 'subcategory': 'renter_profile'},
    
    # Pricing patterns
    r'.*price.*|.*cost.*|.*rate.*': {'category': 'pricing', 'subcategory': 'rate_type'},
    r'.*payment.*': {'category': 'pricing', 'subcategory': 'payment_method'},
    
    # Platform patterns
    r'.*device.*': {'category': 'platform', 'subcategory': 'device_type'},
    r'.*browser.*': {'category': 'platform', 'subcategory': 'os_browser'},
    r'.*app.*': {'category': 'platform', 'subcategory': 'app_version'},
    
    # Geographic patterns
    r'.*city.*|.*market.*': {'category': 'geographic', 'subcategory': 'city_market'},
    r'.*neighborhood.*': {'category': 'geographic', 'subcategory': 'neighborhood'},
}

MEASURE_PATTERNS = {
    # Revenue patterns
    r'.*revenue.*': {'category': 'revenue', 'subcategory': 'net_revenue'},
    r'.*checkout.*amount.*': {'category': 'revenue', 'subcategory': 'booking_revenue'},
    r'.*operator.*remit.*': {'category': 'revenue', 'subcategory': 'operator_remit'},
    r'.*credit.*': {'category': 'revenue', 'subcategory': 'credit_usage'},
    r'.*fee.*': {'category': 'revenue', 'subcategory': 'service_fees'},
    
    # Volume patterns
    r'.*count.*': {'category': 'volume', 'subcategory': 'booking_count'},
    r'.*number.*': {'category': 'volume', 'subcategory': 'booking_count'},
    
    # Operational patterns
    r'.*duration.*': {'category': 'operational', 'subcategory': 'parking_duration'},
    r'.*lead_time.*': {'category': 'operational', 'subcategory': 'lead_time'},
    r'.*processing.*': {'category': 'operational', 'subcategory': 'processing_time'},
    
    # Conversion patterns
    r'.*conversion.*': {'category': 'conversion', 'subcategory': 'search_to_book'},
    r'.*rate.*': {'category': 'conversion', 'subcategory': 'repeat_rate'},
    
    # Utilization patterns
    r'.*occupancy.*': {'category': 'utilization', 'subcategory': 'occupancy_rate'},
    r'.*capacity.*': {'category': 'utilization', 'subcategory': 'capacity_usage'},
}

def infer_entity_from_model_name(model_name: str) -> str:
    """Infer entity from semantic model name."""
    if 'rental' in model_name or 'order' in model_name:
        return 'rental'
    elif 'user' in model_name or 'renter' in model_name or 'customer' in model_name:
        return 'renter'
    elif 'facility' in model_name or 'parking' in model_name or 'spot' in model_name:
        return 'facility'
    elif 'device' in model_name or 'session' in model_name:
        return 'session'
    elif 'search' in model_name:
        return 'search'
    else:
        return model_name.replace('_', ' ').lower()

def suggest_hierarchy(field_name: str, field_type: str, patterns: Dict) -> Optional[Dict[str, str]]:
    """Suggest hierarchy based on field name patterns."""
    field_lower = field_name.lower()
    
    for pattern, hierarchy in patterns.items():
        if re.match(pattern, field_lower):
            return hierarchy
    
    return None

def add_hierarchy_to_field(field: Dict[str, Any], entity: str, field_type: str) -> Dict[str, Any]:
    """Add hierarchy metadata to a field if not already present."""
    if 'config' in field and 'meta' in field.get('config', {}) and 'hierarchy' in field['config']['meta']:
        # Already has hierarchy, skip
        return field
    
    # Determine patterns to use
    patterns = DIMENSION_PATTERNS if field_type == 'dimension' else MEASURE_PATTERNS
    
    # Suggest hierarchy based on field name
    suggested = suggest_hierarchy(field['name'], field_type, patterns)
    
    if suggested:
        # Initialize config structure if needed
        if 'config' not in field:
            field['config'] = {}
        if 'meta' not in field['config']:
            field['config']['meta'] = {}
        
        # Add hierarchy
        hierarchy = {'entity': entity}
        hierarchy.update(suggested)
        field['config']['meta']['hierarchy'] = hierarchy
        
        print(f"  Added hierarchy to {field_type} '{field['name']}': "
              f"entity={entity}, category={suggested['category']}, subcategory={suggested['subcategory']}")
    
    return field

def process_semantic_model(file_path: Path, dry_run: bool = False) -> None:
    """Process a semantic model file to add hierarchy labels."""
    print(f"\nProcessing {file_path.name}...")
    
    with open(file_path, 'r') as f:
        data = yaml.safe_load(f)
    
    if not data or 'semantic_models' not in data:
        print(f"  Skipping - no semantic models found")
        return
    
    modified = False
    
    for model in data['semantic_models']:
        model_name = model.get('name', '')
        entity = infer_entity_from_model_name(model_name)
        print(f"  Model: {model_name} (entity: {entity})")
        
        # Process dimensions
        if 'dimensions' in model:
            for dim in model['dimensions']:
                original = str(dim)
                updated = add_hierarchy_to_field(dim, entity, 'dimension')
                if str(updated) != original:
                    modified = True
        
        # Process measures
        if 'measures' in model:
            for measure in model['measures']:
                original = str(measure)
                updated = add_hierarchy_to_field(measure, entity, 'measure')
                if str(updated) != original:
                    modified = True
    
    if modified and not dry_run:
        # Write back the updated file
        with open(file_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, width=120)
        print(f"  ✓ Updated {file_path.name}")
    elif modified:
        print(f"  Would update {file_path.name} (dry run)")
    else:
        print(f"  No changes needed")

def main():
    """Main function to process all semantic model files."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Apply hierarchy labels to semantic models')
    parser.add_argument('--dir', '-d', default='semantic_models', 
                       help='Directory containing semantic model files')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be changed without modifying files')
    parser.add_argument('--file', '-f', help='Process only a specific file')
    
    args = parser.parse_args()
    
    if args.file:
        # Process single file
        file_path = Path(args.file)
        if file_path.exists():
            process_semantic_model(file_path, args.dry_run)
        else:
            print(f"File not found: {args.file}")
    else:
        # Process all files in directory
        semantic_dir = Path(args.dir)
        if not semantic_dir.exists():
            print(f"Directory not found: {args.dir}")
            return
        
        yaml_files = list(semantic_dir.glob("*.yml")) + list(semantic_dir.glob("*.yaml"))
        
        if not yaml_files:
            print(f"No YAML files found in {args.dir}")
            return
        
        print(f"Found {len(yaml_files)} semantic model files")
        
        for file_path in yaml_files:
            # Skip the one that already has hierarchy
            if 'with_hierarchy' in file_path.name:
                print(f"\nSkipping {file_path.name} (already has hierarchy)")
                continue
            process_semantic_model(file_path, args.dry_run)
        
        if not args.dry_run:
            print("\n✓ Hierarchy labels applied. Run the generator to create updated LookML:")
            print(f"  python -m dbt_to_lookml generate -i {args.dir} -o build/lookml/")

if __name__ == "__main__":
    main()