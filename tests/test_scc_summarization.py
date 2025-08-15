#!/usr/bin/env python3
"""
Comprehensive SCC Summarization Test
This script tests the complete SCC summarization pipeline using local models.
"""

import os
import tempfile
import json
from core.scc_summarizer import summarize_scc, parse_scc
from core.transcription import save_scc_file

def test_scc_summarization_pipeline():
    """Test the complete SCC summarization pipeline"""
    print("🧪 Testing SCC Summarization Pipeline")
    print("=" * 50)
    
    # Test 1: Create a sample SCC file
    test_segments = [
        {"start": 0.0, "end": 5.0, "text": "Welcome to the city council meeting of January 15th, 2024."},
        {"start": 5.5, "end": 10.0, "text": "Today we will discuss the new budget proposal for infrastructure improvements."},
        {"start": 10.5, "end": 15.0, "text": "The proposed budget includes road repairs, park maintenance, and library upgrades."},
        {"start": 15.5, "end": 20.0, "text": "We need to allocate funds for emergency services and public safety."},
        {"start": 20.5, "end": 25.0, "text": "The mayor will now present the detailed budget breakdown."},
        {"start": 25.5, "end": 30.0, "text": "Our priority is ensuring sustainable growth while maintaining fiscal responsibility."},
        {"start": 30.5, "end": 35.0, "text": "The infrastructure committee has reviewed all proposals thoroughly."},
        {"start": 35.5, "end": 40.0, "text": "We expect to begin implementation by the end of the fiscal year."},
        {"start": 40.5, "end": 45.0, "text": "Thank you for your attention. We will now open the floor for questions."}
    ]
    
    # Create temporary SCC file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.scc', delete=False) as f:
        temp_scc_path = f.name
    
    try:
        # Generate SCC file
        save_scc_file(test_segments, temp_scc_path)
        
        if not os.path.exists(temp_scc_path):
            print("❌ Failed to create test SCC file")
            return False
        
        print("✅ Created test SCC file")
        
        # Test 2: Parse the SCC file
        parsed_segments = parse_scc(temp_scc_path)
        
        if not parsed_segments:
            print("❌ Failed to parse SCC file")
            return False
        
        print(f"✅ Successfully parsed {len(parsed_segments)} segments")
        
        # Test 3: Verify parsing results
        if len(parsed_segments) != len(test_segments):
            print(f"❌ Segment count mismatch: expected {len(test_segments)}, got {len(parsed_segments)}")
            return False
        
        # Check that text was extracted correctly
        for i, segment in enumerate(parsed_segments):
            if not segment.get('text'):
                print(f"❌ Empty text in segment {i}")
                return False
        
        print("✅ SCC parsing validation passed")
        
        # Test 4: Generate summary
        print("\n🔄 Testing Summarization...")
        summary_path = summarize_scc(temp_scc_path)
        
        if not summary_path:
            print("❌ Summary generation failed")
            return False
        
        if not os.path.exists(summary_path):
            print("❌ Summary file was not created")
            return False
        
        print("✅ Summary file generated successfully")
        
        # Test 5: Validate summary content
        try:
            with open(summary_path, 'r') as f:
                summary_data = json.load(f)
            
            if 'summary' not in summary_data:
                print("❌ Summary data missing 'summary' key")
                return False
            
            summary_items = summary_data['summary']
            
            if not isinstance(summary_items, list):
                print("❌ Summary should be a list")
                return False
            
            if len(summary_items) == 0:
                print("❌ Summary is empty")
                return False
            
            # Check summary item structure
            for item in summary_items:
                required_keys = ['speaker', 'start', 'text']
                for key in required_keys:
                    if key not in item:
                        print(f"❌ Summary item missing '{key}' key")
                        return False
            
            print(f"✅ Summary validation passed: {len(summary_items)} summary items")
            
            # Print sample summary for verification
            print("\n📋 Sample Summary Content:")
            for i, item in enumerate(summary_items[:2]):  # Show first 2 items
                print(f"  {i+1}. [{item['start']}] {item['text'][:100]}...")
                
        except json.JSONDecodeError:
            print("❌ Invalid JSON in summary file")
            return False
        
        print("\n🎉 All SCC summarization tests passed!")
        return True
        
    finally:
        # Clean up temporary files
        if os.path.exists(temp_scc_path):
            os.unlink(temp_scc_path)
        if summary_path and os.path.exists(summary_path):
            os.unlink(summary_path)

def test_scc_error_handling():
    """Test SCC error handling"""
    print("\n🔍 Testing SCC Error Handling")
    print("=" * 50)
    
    # Test 1: Non-existent file
    result = summarize_scc("nonexistent.scc")
    if result is not None:
        print("❌ Should return None for non-existent file")
        return False
    print("✅ Correctly handles non-existent file")
    
    # Test 2: Empty file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.scc', delete=False) as f:
        empty_scc_path = f.name
    
    try:
        result = summarize_scc(empty_scc_path)
        if result is not None:
            print("❌ Should return None for empty file")
            return False
        print("✅ Correctly handles empty file")
        
    finally:
        if os.path.exists(empty_scc_path):
            os.unlink(empty_scc_path)
    
    # Test 3: Invalid SCC format
    with tempfile.NamedTemporaryFile(mode='w', suffix='.scc', delete=False) as f:
        f.write("Invalid SCC content\nNot a real SCC file\n")
        invalid_scc_path = f.name
    
    try:
        result = summarize_scc(invalid_scc_path)
        if result is not None:
            print("❌ Should return None for invalid SCC format")
            return False
        print("✅ Correctly handles invalid SCC format")
        
    finally:
        if os.path.exists(invalid_scc_path):
            os.unlink(invalid_scc_path)
    
    print("✅ Error handling tests passed")
    return True

def test_backward_compatibility():
    """Test backward compatibility with SRT function names"""
    print("\n🔄 Testing Backward Compatibility")
    print("=" * 50)
    
    try:
        from core.scc_summarizer import summarize_srt
        print("✅ summarize_srt function available")
        
        # Test that it redirects correctly
        result = summarize_srt("nonexistent.scc")
        if result is not None:
            print("❌ Should return None for non-existent file")
            return False
        print("✅ summarize_srt correctly redirects to summarize_scc")
        
    except ImportError:
        print("❌ summarize_srt function not available")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starting Comprehensive SCC Summarization Tests")
    print("=" * 60)
    
    success = True
    
    success &= test_scc_summarization_pipeline()
    success &= test_scc_error_handling()
    success &= test_backward_compatibility()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All SCC summarization tests passed! System is ready for production.")
        exit(0)
    else:
        print("❌ Some SCC summarization tests failed. Please check the implementation.")
        exit(1) 