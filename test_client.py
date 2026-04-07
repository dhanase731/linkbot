import requests
import json

# Base URL of the API
BASE_URL = "http://localhost:8000"

def test_scraper():
    """Test the scraper API with different examples"""
    
    print("🚀 Testing Playwright Scraper API\n")
    
    # Test 1: Health check
    print("1️⃣  Health Check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✅ Status: {response.json()}\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return
    
    # Test 2: Basic scraping
    print("2️⃣  Basic Scraping (Example.com)...")
    payload = {
        "url": "https://example.com",
        "extract_full_text": True,
        "timeout": 30
    }
    
    try:
        response = requests.post(f"{BASE_URL}/scrape", json=payload)
        data = response.json()
        
        if data["success"]:
            print(f"✅ Title: {data['title']}")
            print(f"✅ Text Preview: {data['full_text'][:100]}...\n")
        else:
            print(f"❌ Error: {data['error']}\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")
    
    # Test 3: Custom selectors
    print("3️⃣  Custom Selectors (Extract Specific Elements)...")
    payload = {
        "url": "https://example.com",
        "custom_selectors": {
            "main_heading": "h1",
            "paragraph": "p"
        },
        "timeout": 30
    }
    
    try:
        response = requests.post(f"{BASE_URL}/scrape", json=payload)
        data = response.json()
        
        if data["success"]:
            print(f"✅ Extracted Data: {json.dumps(data['data'], indent=2)}\n")
        else:
            print(f"❌ Error: {data['error']}\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")
    
    # Test 4: Extract links
    print("4️⃣  Extract Links...")
    payload = {
        "url": "https://example.com",
        "extract_links": True,
        "timeout": 30
    }
    
    try:
        response = requests.post(f"{BASE_URL}/scrape", json=payload)
        data = response.json()
        
        if data["success"]:
            print(f"✅ Found {len(data['links'])} links")
            if data['links']:
                print(f"   Sample: {data['links'][0]}\n")
        else:
            print(f"❌ Error: {data['error']}\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")

if __name__ == "__main__":
    print("Make sure the API is running on http://localhost:8000")
    print("Run 'python main.py' in another terminal\n")
    input("Press Enter to start tests...")
    test_scraper()
