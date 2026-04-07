"""
Configuration for the ChatGPT-like application
"""

import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "chatgpt_db")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# Local LLM (Ollama)
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

# App Config
USE_OPENAI = bool(OPENAI_API_KEY)
USE_LOCAL_LLM = True  # Always try local LLM as fallback

DEBUG = os.getenv("DEBUG", "True") == "True"
