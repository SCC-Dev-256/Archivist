#!/usr/bin/env python3
"""
Demonstration script for the Title Normalizer CLI Tool.

This script shows how the title normalization works with sample data
without requiring a live Cablecast API connection.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chronologic_order import TitleNormalizer


def demo_title_normalization():
    """Demonstrate title normalization with sample data."""
    
    print("=" * 60)
    print("Title Normalizer CLI Tool - Demonstration")
    print("=" * 60)
    
    # Initialize the normalizer
    normalizer = TitleNormalizer()
    
    # Sample titles to test
    sample_titles = [
        "Grant City Council (6/3/25)",
        "Board Meeting (12/25/24)",
        "Special Event (1/1/30)",
        "2025-06-03 - Already Normalized",
        "No Date Pattern",
        "Meeting (13/1/25)",  # Invalid month
        "Event (12/32/25)",   # Invalid day
        "Show (2/29/24)",     # Leap year
        "Meeting (3/15/29)",  # Year boundary
        "Event (3/15/30)",    # Year boundary
    ]
    
    print("\nTesting Title Normalization:")
    print("-" * 40)
    
    for i, title in enumerate(sample_titles, 1):
        print(f"\n{i}. Input: {title}")
        
        # Check if already normalized
        if normalizer.is_already_normalized(title):
            print(f"   Status: Already normalized")
            continue
        
        # Extract date components
        date_components = normalizer.extract_date_from_title(title)
        if date_components:
            month, day, year = date_components
            print(f"   Date: {year:04d}-{month:02d}-{day:02d}")
        
        # Normalize title
        normalized = normalizer.normalize_title(title)
        if normalized:
            print(f"   Output: {normalized}")
        else:
            print(f"   Status: Skipped (no valid date pattern)")
    
    print("\n" + "=" * 60)
    print("Normalization Rules:")
    print("=" * 60)
    print("• Pattern: (M/D/YY) → YYYY-MM-DD - Title")
    print("• Years 00-29 → 2000-2029")
    print("• Years 30-99 → 1930-1999")
    print("• Invalid dates are skipped")
    print("• Already normalized titles are skipped")
    print("• Titles without date patterns are skipped")
    
    print("\n" + "=" * 60)
    print("CLI Usage Examples:")
    print("=" * 60)
    print("# Test connection")
    print("python core/chronologic_order.py --token YOUR_TOKEN --test-connection")
    print()
    print("# Preview changes (dry-run)")
    print("python core/chronologic_order.py --token YOUR_TOKEN --dry-run")
    print()
    print("# Apply changes")
    print("python core/chronologic_order.py --token YOUR_TOKEN")
    print()
    print("# Export results to CSV")
    print("python core/chronologic_order.py --token YOUR_TOKEN --export-csv results.csv")
    print()
    print("# Process specific project")
    print("python core/chronologic_order.py --token YOUR_TOKEN --project-id 123 --dry-run")


if __name__ == "__main__":
    demo_title_normalization() 