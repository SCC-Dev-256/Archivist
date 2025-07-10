#!/usr/bin/env python3
"""
Test script for SCC upload functionality.
This script tests the SCC upload methods we've implemented.
"""

import os
from core.cablecast_client import CablecastAPIClient
from core.services.vod import VODService

def test_scc_upload_functionality():
    """Test the SCC upload functionality"""
    print("🧪 Testing SCC Upload Functionality")
    print("=" * 50)
    
    # Test 1: Check if test SCC file exists
    scc_file = "tests/test_caption.scc"
    if not os.path.exists(scc_file):
        print(f"❌ Test SCC file not found: {scc_file}")
        return False
    
    print(f"✅ Test SCC file found: {scc_file}")
    
    # Test 2: Initialize Cablecast client
    try:
        client = CablecastAPIClient()
        print("✅ CablecastAPIClient initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize CablecastAPIClient: {e}")
        return False
    
    # Test 3: Check if upload_scc_file method exists
    if hasattr(client, 'upload_scc_file'):
        print("✅ upload_scc_file method available")
    else:
        print("❌ upload_scc_file method not found")
        return False
    
    # Test 4: Initialize VOD service
    try:
        vod_service = VODService()
        print("✅ VODService initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize VODService: {e}")
        return False
    
    # Test 5: Check if upload_scc_caption method exists
    if hasattr(vod_service, 'upload_scc_caption'):
        print("✅ upload_scc_caption method available")
    else:
        print("❌ upload_scc_caption method not found")
        return False
    
    # Test 6: Read and validate SCC file
    try:
        with open(scc_file, 'r') as f:
            content = f.read()
            lines = content.strip().split('\n')
            
            # Check for SCC header
            if lines[0].startswith('Scenarist_SCC V1.0'):
                print("✅ SCC header found")
            else:
                print("❌ Invalid SCC header")
                return False
            
            # Count timecode lines (lines with semicolon timestamps)
            timecode_lines = [line for line in lines if ';' in line and '\t' in line]
            print(f"✅ SCC file validated: {len(timecode_lines)} caption segments found")
            
    except Exception as e:
        print(f"❌ Failed to read SCC file: {e}")
        return False
    
    # Test 7: Check backward compatibility - SRT methods should still exist
    if hasattr(client, 'upload_srt_file'):
        print("✅ Backward compatibility: upload_srt_file method still available")
    else:
        print("⚠️  Warning: upload_srt_file method not found (backward compatibility issue)")
    
    if hasattr(vod_service, 'upload_srt_caption'):
        print("✅ Backward compatibility: upload_srt_caption method still available")
    else:
        print("⚠️  Warning: upload_srt_caption method not found (backward compatibility issue)")
    
    print("\n🎯 All SCC upload functionality tests passed!")
    print("\n📋 Ready for API Key Testing:")
    print("1. Get API key from Kevin at SCCTV")
    print("2. Update .env file with correct credentials")
    print("3. Test actual upload with: curl -X POST 'http://localhost:5000/api/cablecast/vods/123/captions' -F 'caption_file=@test_caption.scc'")
    
    return True

def test_scc_conversion_pipeline():
    """Test the SCC conversion pipeline"""
    print("\n🔄 Testing SCC Conversion Pipeline")
    print("=" * 50)
    
    try:
        from core.transcription import save_scc_file
        
        # Test sample transcription segments
        test_segments = [
            {"start": 1.0, "end": 4.0, "text": "This is a test caption file for Archivist integration."},
            {"start": 4.5, "end": 8.0, "text": "It contains multiple subtitle segments with proper timing."},
            {"start": 8.5, "end": 12.0, "text": "This will be used to test the SCC upload to Cablecast VODs."}
        ]
        
        # Test SCC file generation
        output_path = "/tmp/test_generated.scc"
        save_scc_file(test_segments, output_path)
        
        if os.path.exists(output_path):
            print("✅ SCC file generation successful")
            
            # Validate generated file
            with open(output_path, 'r') as f:
                content = f.read()
                if content.startswith('Scenarist_SCC V1.0'):
                    print("✅ Generated SCC file has correct header")
                else:
                    print("❌ Generated SCC file has incorrect header")
                    return False
            
            # Clean up
            os.remove(output_path)
            
        else:
            print("❌ SCC file generation failed")
            return False
            
    except Exception as e:
        print(f"❌ SCC conversion pipeline test failed: {e}")
        return False
    
    return True

def test_scc_parsing():
    """Test SCC file parsing functionality"""
    print("\n📖 Testing SCC Parsing")
    print("=" * 50)
    
    try:
        from core.scc_summarizer import parse_scc
        
        scc_file = "tests/test_caption.scc"
        
        # Test parsing the SCC file
        parsed_segments = parse_scc(scc_file)
        
        if parsed_segments:
            print(f"✅ SCC parsing successful: {len(parsed_segments)} segments parsed")
            
            # Check first segment
            first_segment = parsed_segments[0]
            expected_keys = ['start', 'end', 'text']
            
            for key in expected_keys:
                if key in first_segment:
                    print(f"✅ Segment contains '{key}' field")
                else:
                    print(f"❌ Segment missing '{key}' field")
                    return False
            
            # Validate text content
            if first_segment['text'] and len(first_segment['text']) > 0:
                print("✅ Text content successfully extracted from SCC")
            else:
                print("❌ Failed to extract text content from SCC")
                return False
                
        else:
            print("❌ SCC parsing failed - no segments returned")
            return False
            
    except Exception as e:
        print(f"❌ SCC parsing test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = True
    
    success &= test_scc_upload_functionality()
    success &= test_scc_conversion_pipeline()
    success &= test_scc_parsing()
    
    if success:
        print("\n🎉 All SCC tests passed! System is ready for production.")
    else:
        print("\n❌ Some SCC tests failed. Please check the implementation.") 