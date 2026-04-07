#!/usr/bin/env python3
"""
Quick start script for the ChatGPT-like application
Set up and verify all dependencies are ready
"""

import os
import subprocess
import sys
import time

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def check_mongodb():
    """Check if MongoDB is running"""
    print_header("Checking MongoDB")
    
    try:
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
        client.server_info()
        print("✅ MongoDB is running on localhost:27017")
        return True
    except Exception as e:
        print(f"❌ MongoDB not found: {e}")
        print("\n📖 To fix, follow one of these options:\n")
        print("Windows:")
        print("  1. Install: choco install mongodb-community")
        print("  2. Start: mongod\n")
        print("Mac:")
        print("  1. Install: brew install mongodb-community")
        print("  2. Start:  brew services start mongodb-community\n")
        print("Linux:")
        print("  1. Install: sudo apt-get install mongodb")
        print("  2. Start:   sudo systemctl start mongodb\n")
        print("Or use MongoDB Atlas (Cloud): https://www.mongodb.com/cloud/atlas\n")
        return False

def check_ollama():
    """Check if Ollama is running"""
    print_header("Checking Ollama (Local LLM)")
    
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print("✅ Ollama is running on localhost:11434")
            models = response.json().get("models", [])
            if models:
                print(f"   Available models: {', '.join([m['name'] for m in models[:3]])}")
            return True
    except Exception as e:
        print(f"⚠️  Ollama not found: {e}")
        print("\n📖 To enable local LLM:\n")
        print("1. Install Ollama: https://ollama.ai")
        print("2. Run: ollama serve")
        print("3. In another terminal, pull a model:")
        print("   - ollama pull mistral")
        print("   - ollama pull neural-chat")
        print("\n⚠️  Without Ollama, you MUST set OPENAI_API_KEY in .env\n")
        return False

def check_openai():
    """Check if OpenAI key is set"""
    print_header("Checking OpenAI Configuration")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    
    if api_key and api_key.startswith("sk-"):
        print(f"✅ OpenAI API key found: {api_key[:20]}...")
        return True
    else:
        print("⚠️  No OpenAI API key configured")
        print("\n📖 To use OpenAI:\n")
        print("1. Get your API key: https://platform.openai.com/api-keys")
        print("2. Add to .env:")
        print('   OPENAI_API_KEY=sk-your-key-here\n')
        return False

def check_packages():
    """Check if all Python packages are installed"""
    print_header("Checking Python Packages")
    
    required = [
        'fastapi',
        'uvicorn',
        'pydantic',
        'pymongo',
        'motor',
        'openai',
        'requests'
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print(f"\nInstall with:")
        print(f"  pip install {' '.join(missing)}\n")
        return False
    
    return True

def main():
    print("\n" + "="*60)
    print("  🚀 ChatGPT-Like Application - Startup Check")
    print("="*60 + "\n")
    
    results = {
        "MongoDB": check_mongodb(),
        "Python Packages": check_packages(),
        "OpenAI or Ollama": check_ollama() or check_openai()
    }
    
    print_header("Startup Summary")
    
    for service, status in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {service}")
    
    if all(results.values()):
        print("\n✅ All systems ready! You can now run:")
        print("   python chat_app.py")
        print("\nThen open: http://localhost:8000")
        return 0
    else:
        print("\n❌ Some services are not ready")
        print("   Please set up the missing components above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
