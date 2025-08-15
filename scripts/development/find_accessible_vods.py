#!/usr/bin/env python3
"""
Find Accessible VODs
Search for VODs that have accessible video files
"""

import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def find_accessible_vods():
    """Find VODs with accessible video files"""
    print("🔍 Searching for accessible VODs...")
    
    try:
        from core.cablecast_client import CablecastAPIClient
        client = CablecastAPIClient()
        
        # Get recent VODs
        vods = client.get_recent_vods(limit=50)
        print(f"Found {len(vods)} recent VODs")
        
        accessible_vods = []
        
        for i, vod in enumerate(vods):
            vod_id = vod.get('id')
            if not vod_id:
                continue
                
            print(f"Checking VOD {vod_id} ({i+1}/{len(vods)})...")
            
            # Try to get direct URL
            direct_url = client.get_vod_direct_url(vod_id)
            
            if direct_url:
                # Get show details for title
                show_id = vod.get('show')
                title = "Unknown"
                
                if show_id:
                    show = client.get_show(show_id)
                    if show and 'show' in show:
                        title = show['show'].get('title', 'Unknown')
                
                accessible_vods.append({
                    'vod_id': vod_id,
                    'title': title,
                    'direct_url': direct_url,
                    'show_id': show_id
                })
                
                print(f"✅ VOD {vod_id}: {title}")
                
                # Stop after finding 3 accessible VODs
                if len(accessible_vods) >= 3:
                    break
            else:
                print(f"❌ VOD {vod_id}: No direct URL")
        
        print(f"\n📊 Found {len(accessible_vods)} accessible VODs:")
        for vod in accessible_vods:
            print(f"   - VOD {vod['vod_id']}: {vod['title']}")
            print(f"     URL: {vod['direct_url']}")
        
        return accessible_vods
        
    except Exception as e:
        print(f"❌ Error finding accessible VODs: {e}")
        return []

if __name__ == "__main__":
    accessible_vods = find_accessible_vods()
    
    if accessible_vods:
        print(f"\n🎉 Success! Found {len(accessible_vods)} accessible VODs for testing.")
        print("You can use any of these VOD IDs in your tests.")
    else:
        print("\n⚠️  No accessible VODs found. This might indicate:")
        print("   - VODs are archived or not publicly accessible")
        print("   - Different API endpoints are needed")
        print("   - Authentication issues")
        print("   - VODs are stored in a different format") 