#!/usr/bin/env python3
"""
Quick start script for the unified AI assistant
Check prerequisites and start the app
"""

import os
import subprocess
import sys
import time

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def check_mongdb():
    """Check if MongoDB is running"""
    print_header("Checking MongoDB")
    
    try:
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
        client.server_info()
        print("✅ MongoDB is running on localhost:27017")
        return True
    except Exception as e:
        print(f"❌ MongoDB not running: {e}")
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
        'requests'
    ]
    
    all_good = True
    for package in required:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - missing")
            all_good = False
    
    return all_good

def check_ollama():
    """Check if Ollama is running"""
    print_header("Checking Ollama (Local AI)")
    
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get("models", [])
            if models:
                print("✅ Ollama is running")
                print(f"   Models available: {', '.join([m['name'] for m in models[:2]])}")
                return True
            else:
                print("⚠️  Ollama running but no models installed")
                print("   Run: ollama pull mistral")
                return False
    except Exception as e:
        print(f"❌ Ollama not running: {e}")
        print("   Instructions:")
        print("   1. Download: https://ollama.ai")
        print("   2. Run: ollama serve (in new terminal)")
        return False

def main():
    print("\n" + "="*60)
    print("  🚀 Unified AI Assistant - Startup Check")
    print("="*60)
    
    checks = {
        "MongoDB": check_mongdb(),
        "Python Packages": check_packages(),
        "Ollama": check_ollama()
    }
    
    print_header("Summary")
    
    for check, result in checks.items():
        icon = "✅" if result else "❌"
        print(f"{icon} {check}")
    
    if not checks["Ollama"]:
        print("\n⚠️ IMPORTANT: Start Ollama first!")
        print("   1. Install from: https://ollama.ai")
        print("   2. Run: ollama serve")
        print("   3. In another terminal: ollama pull mistral")
        print("   4. Come back here and we'll start the app\n")
        return 1
    
    if all(checks.values()):
        print("\n✅ All systems ready!")
        print("   Starting unified AI assistant server...\n")
        
        try:
            subprocess.run([sys.executable, "app.py"], cwd=os.path.dirname(os.path.abspath(__file__)))
        except KeyboardInterrupt:
            print("\n\n👋 Server stopped by user")
            return 0
        except Exception as e:
            print(f"\n❌ Error starting server: {e}")
            return 1
    else:
        print("\n❌ Fix the issues above before starting")
        return 1

if __name__ == "__main__":
    sys.exit(main())
