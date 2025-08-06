#!/usr/bin/env python3
# PURPOSE: Fix corrupted JSON results from scraper
# DEPENDENCIES: json, re
# MODIFICATION NOTES: v1.0 - Initial implementation

import json
import re

def fix_results():
    """Extract valid JSON objects from corrupted results.json file."""
    
    with open('results.json', 'r') as f:
        content = f.read()
    
    # Find all JSON objects using regex
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_pattern, content)
    
    # Parse each match as JSON
    valid_items = []
    for match in matches:
        try:
            item = json.loads(match)
            valid_items.append(item)
        except json.JSONDecodeError:
            continue
    
    # Write clean JSON
    with open('clean_final_results.json', 'w') as f:
        json.dump(valid_items, f, indent=2)
    
    print(f"Extracted {len(valid_items)} valid items")
    return valid_items

if __name__ == "__main__":
    items = fix_results()
    
    # Analyze results
    cities = {}
    for item in items:
        city = item.get('city', 'Unknown')
        if city not in cities:
            cities[city] = 0
        cities[city] += 1
    
    print("\nResults by city:")
    for city, count in cities.items():
        print(f"  {city}: {count} PDFs") 