# 🚀 Unified AI Assistant with Web Scraping

**Everything in ONE single server!**

## Features in One Place

✨ **Chat Interface** - ChatGPT-like conversation
🌐 **Web Scraping** - Playwright extracts website data  
🤖 **AI Analysis** - Ollama analyzes websites, summarizes content, and provides detailed insights
💾 **Persistence** - MongoDB stores all conversations
🔗 **API** - Direct scraper and analysis API endpoints available
📝 **Paragraph Summarization** - Convert any paragraph to customized summaries (concise, detailed, bullet-points)
🔍 **Website Deep Analysis** - Get comprehensive website analysis: purpose, tech stack, integrated APIs

---

## Quick Start

### Prerequisites Setup (One-Time)

#### 1️⃣ MongoDB (already running ✅)

MongoDB is already running on your system!

#### 2️⃣ Ollama (Local AI)

Download from: https://ollama.ai

Then run:

```powershell
ollama serve
```

In another terminal, pull a model:

```powershell
ollama pull mistral
```

### Start the Unified Server

Once Ollama is running with a model, start the app:

```powershell
cd "d:\Model Practical"
python app.py
```

You should see:

```
============================================================
🚀 Starting Unified AI Assistant Server
============================================================
✨ Features:
   - ChatGPT-like Interface
   - Web Scraping with Playwright
   - Direct Scraper API (/api/scrape)
   - MongoDB Conversation Storage
   - Ollama/OpenAI Integration
============================================================
```

### Open Browser

```
http://localhost:8000
```

---

## What You Can Do

### 💬 In Chat Interface

**Example 1: Comprehensive Website Analysis**

```
User: "https://github.com"

App will:
- Scrape github.com
- Send to Ollama for deep analysis
- Return:
  * Website Purpose: What GitHub does
  * Technology Stack: The frameworks/tech it uses
  * Integrated APIs: What services are integrated
  * Target Audience: Who uses it
  * Key Features: Main offerings
```

**Example 2: Analyze a Website**

```
User: "Tell me about https://github.com"

App will:
- Scrape github.com
- Send content to Ollama
- Return: Detailed analysis of what GitHub does
```

**Example 3: Compare Websites**

```
User: "What's the difference between https://site1.com and https://site2.com?"

App will:
- Scrape both sites
- Send to Ollama
- Return: Comparison
```

**Example 4: Regular Chat**

```
User: "What is Python?"

App will:
- Send to Ollama (no scraping)
- Return: AI response
```

### 📡 Direct API Requests

**Scrape a website:**

```bash
curl -X POST http://localhost:8000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

**Get comprehensive website analysis:**

```bash
curl -X POST http://localhost:8000/api/website-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://github.com",
    "analyze_tech_stack": true,
    "analyze_apis": true,
    "analyze_purpose": true,
    "detailed": false
  }'
```

**Summarize a paragraph:**

```bash
curl -X POST http://localhost:8000/api/summarize-paragraph \
  -H "Content-Type: application/json" \
  -d '{
    "paragraph": "Your long paragraph text here...",
    "style": "concise"
  }'
```

Style options: `concise`, `detailed`, `bullet-points`, `academic`

**Get website data:**

```bash
curl -X POST http://localhost:8000/api/website-data \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

**Send chat message:**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is Python?"}'
```

---

## API Endpoints

### Chat Endpoints

- `POST /api/chat` - Send message (auto-scrapes URLs if present)
- `GET /api/conversations` - List all conversations
- `GET /api/conversation/{id}` - Get specific conversation
- `DELETE /api/conversation/{id}` - Delete conversation
- `POST /api/conversation/{id}/title` - Update title

### Scraper Endpoints

- `POST /api/scrape` - Scrape website
- `POST /api/website-data` - Get comprehensive website data

### Analysis Endpoints (NEW!)

- `POST /api/website-analysis` - Get comprehensive website analysis
  - Returns: Purpose, Tech Stack, Integrated APIs, Target Audience, Key Features
- `POST /api/summarize-paragraph` - Summarize any paragraph
  - Styles: `concise`, `detailed`, `bullet-points`, `academic`

### Status

- `GET /health` - Health check
- `GET /` - Frontend (chat interface)

---

## 🆕 NEW FEATURES

### 📝 Personalized Paragraph Summarization via Ollama

Get intelligent summaries of any paragraph in different styles!

**Styles Available:**

- `concise` - Brief, to-the-point summary
- `detailed` - Comprehensive summary with more detail
- `bullet-points` - Organized as bullet points
- `academic` - Formal, scholarly style

**Example:**

```
POST /api/summarize-paragraph
{
  "paragraph": "Your long text here...",
  "style": "concise"
}

Response:
{
  "success": true,
  "original_length": 500,
  "summary_style": "concise",
  "summary": "Concise AI-generated summary of the paragraph..."
}
```

### 🔍 Comprehensive Website Deep Analysis using Ollama

Get comprehensive insights about any website powered by Ollama AI!

**What You Get:**

1. **Website Purpose** - What the site does and problems it solves
2. **Technology Stack** - Frameworks and technologies used (React, Django, etc.)
3. **Integrated APIs** - Third-party services (payment gateways, analytics, etc.)
4. **Target Audience** - Who the site is for
5. **Key Features** - Main offerings and services

**Example:**

```
POST /api/website-analysis
{
  "url": "https://github.com",
  "analyze_tech_stack": true,
  "analyze_apis": true,
  "analyze_purpose": true,
  "detailed": false
}

Response:
{
  "success": true,
  "url": "https://github.com",
  "title": "GitHub",
  "analysis": {
    "Website Purpose": "GitHub is a...",
    "Technology Stack": "Likely built with...",
    "Integrated APIs": "GitHub integrates...",
    "Target Audience": "Developers and...",
    "Key Features": "..."
  }
}
```

### 💬 Enhanced Chat with Website Analysis

Now when you send a URL in chat, you get full analysis:

```
User: "https://github.com"

Chat returns:
📄 🌐 Website: https://github.com
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 Title: GitHub

🔍 📊 COMPREHENSIVE ANALYSIS:

1. Website Purpose:
   GitHub is a web-based version control repository hosting service...

2. Technology Stack:
   - Frontend: React, TypeScript
   - Backend: Ruby on Rails
   - Database: PostgreSQL
   - Infrastructure: AWS

3. Integrated APIs:
   - Stripe (payments)
   - Slack (notifications)
   - Google OAuth (authentication)
   - npm Registry API

4. Target Audience:
   Software developers, teams, enterprises

5. Key Features:
   - Version control with Git
   - Collaborative development
   - CI/CD pipelines
   - Issue tracking
   - Pull requests

📈 Additional Stats:
  • Total Links: 250
  • Total Images: 45
  • Word Count: 5,230
```

---

### "AI not available"

**Solution:** Make sure Ollama is running

```powershell
ollama serve
```

### "Connection refused"

**Solution:** Make sure MongoDB is running

```powershell
mongod
```

### "Ollama model not found"

**Solution:** Pull a model

```powershell
ollama pull mistral
```

### Port 8000 already in use

**Solution:** Stop the old process or use different port. Change in app.py:

```python
uvicorn.run(app, host="0.0.0.0", port=8001)  # Use 8001 instead
```

---

## File Structure

```
Model Practical/
├── app.py              ← Main unified server (run this!)
├── models.py           ← Database models
├── config.py           ← Configuration
├── index.html          ← Chat interface
├── .env                ← API keys (optional)
├── requirements.txt    ← Python packages
└── README_UNIFIED.md   ← This file
```

---

## How It Works

1. **User sends message in chat**

   ```
   "Check out https://example.com"
   ```

2. **App detects URL**

   ```
   URL found: https://example.com
   ```

3. **Playwright scrapes the website**

   ```
   Title: Example Domain
   Content: Example Domain description...
   ```

4. **AI analyzes with context**

   ```
   Ollama receives: "Here's website data, analyze it..."
   ```

5. **Response appears in chat**

   ```
   "Example.com is a domain used for examples..."
   ```

6. **Everything saved to MongoDB**
   ```
   Conversation stored with full history
   ```

---

## Performance Tips

- Chat responses faster with **Ollama** (local) than **OpenAI** (API calls)
- Website scraping takes 2-5 seconds per site
- Keep conversation history reasonable (don't add 1000+ messages)

---

## Production Considerations

- Add authentication for production
- Rate limit API endpoints
- Use reverse proxy (nginx)
- Run behind HTTPS
- Add request logging
- Monitor MongoDB storage

---

**Ready to go!** 🎉

Start the server and open http://localhost:8000 in your browser!
