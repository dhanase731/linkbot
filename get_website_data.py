#!/usr/bin/env python3
"""
Simple test script to get website data from the API
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def get_website_data(url):
    """Get comprehensive data about a website"""
    
    payload = {
        "url": url,
        "timeout": 30
    }
    
    print(f"\n🔍 Fetching data for: {url}\n")
    
    try:
        response = requests.post(f"{BASE_URL}/website-data", json=payload, timeout=60)
        data = response.json()
        
        if data["success"]:
            print("=" * 60)
            print("📊 WEBSITE DATA")
            print("=" * 60)
            
            print(f"\n✅ Title: {data.get('title', 'N/A')}")
            print(f"✅ Description: {data.get('description', 'N/A')}")
            print(f"✅ Language: {data.get('language', 'N/A')}")
            print(f"✅ Word Count: {data.get('word_count', 0)}")
            print(f"✅ Favicon: {data.get('favicon_url', 'N/A')}")
            
            if data.get('og_title'):
                print(f"\n📱 Open Graph Data:")
                print(f"   - OG Title: {data.get('og_title')}")
                print(f"   - OG Description: {data.get('og_description')}")
                print(f"   - OG Image: {data.get('og_image')}")
                print(f"   - OG Type: {data.get('og_type')}")
            
            if data.get('headings'):
                print(f"\n📑 Headings Found:")
                for tag, headings_list in data['headings'].items():
                    if headings_list:
                        print(f"   {tag.upper()}: {', '.join(headings_list[:3])}")
                        if len(headings_list) > 3:
                            print(f"         ... and {len(headings_list) - 3} more")
            
            if data.get('images'):
                print(f"\n🖼️  Images Found: {len(data['images'])}")
                for img in data['images'][:3]:
                    print(f"   - {img[:60]}...")
                if len(data['images']) > 3:
                    print(f"   ... and {len(data['images']) - 3} more")
            
            if data.get('links'):
                print(f"\n🔗 Links Found: {len(data['links'])}")
                for link in data['links'][:5]:
                    print(f"   - [{link['text'][:30]}] {link['url'][:50]}")
                if len(data['links']) > 5:
                    print(f"   ... and {len(data['links']) - 5} more")
            
            if data.get('text_content'):
                print(f"\n📄 Content Preview:")
                print(f"   {data['text_content'][:200]}...")
            
            print("\n" + "=" * 60)
            
            # Optionally save full JSON
            with open('website_data.json', 'w') as f:
                json.dump(data, f, indent=2)
            print("✅ Full data saved to website_data.json")
            
        else:
            print(f"❌ Error: {data.get('error')}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure the API is running on http://localhost:8000")
        print("   Run 'python main.py' first!")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    # Test with different websites
    print("🌐 Website Data Extractor")
    print("Make sure the API server is running!")
    
    # Example URLs
    urls = [
        "https://example.com",
        "https://www.python.org",
    ]
    
    url = input("\nEnter website URL (or press Enter for example.com): ").strip()
    if not url:
        url = "https://example.com"
    
    if not url.startswith('http'):
        url = 'https://' + url
    
    get_website_data(url)
