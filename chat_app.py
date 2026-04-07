"""
ChatGPT-like application with MongoDB, AI integration, and Playwright web scraping
User can send website URLs and AI will analyze them
"""

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncClient, AsyncDatabase
import motor.motor_asyncio
from bson import ObjectId
import os
from datetime import datetime
import asyncio
import re
from urllib.parse import urlparse
from playwright.async_api import async_playwright

from config import MONGODB_URL, DATABASE_NAME, OPENAI_API_KEY, OPENAI_MODEL, OLLAMA_API_URL, OLLAMA_MODEL, USE_OPENAI, USE_LOCAL_LLM
from models import Message, Conversation, ChatRequest, ChatResponse, ConversationListItem

# Initialize FastAPI
app = FastAPI(
    title="ChatGPT-Like Application",
    description="AI Chat application with MongoDB and LLM integration",
    version="1.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Connection
client: AsyncClient = None
db: AsyncDatabase = None


@app.on_event("startup")
async def startup():
    """Connect to MongoDB on startup"""
    global client, db
    client = motor.motor_asyncio.AsyncMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    print(f"✅ Connected to MongoDB: {MONGODB_URL}")
    print(f"✅ Database: {DATABASE_NAME}")


@app.on_event("shutdown")
async def shutdown():
    """Close MongoDB connection on shutdown"""
    if client:
        client.close()
        print("❌ Disconnected from MongoDB")


# ==================== AI Functions ====================

def extract_urls(text):
    """Extract URLs from text"""
    url_pattern = r'https?://[^\s]+'
    return re.findall(url_pattern, text)


async def scrape_website(url: str) -> dict:
    """Scrape website using Playwright"""
    try:
        print(f"🌐 Scraping: {url}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            # Set timeout and navigate
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Extract metadata
            title = await page.title()
            description = await page.evaluate('''() => {
                const meta = document.querySelector('meta[name="description"]');
                return meta ? meta.getAttribute('content') : '';
            }''')
            
            # Extract headings
            headings = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('h1, h2, h3'))
                    .map(h => h.innerText)
                    .slice(0, 10);
            }''')
            
            # Extract main text
            text_content = await page.locator("body").inner_text()
            # Limit to first 2000 characters
            text_content = text_content[:2000] if text_content else ""
            
            # Extract links
            links = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a[href]'))
                    .map(a => ({url: a.href, text: a.innerText}))
                    .filter(l => l.url.startsWith('http'))
                    .slice(0, 10);
            }''')
            
            await browser.close()
            
            return {
                "url": url,
                "title": title,
                "description": description,
                "headings": headings,
                "text_content": text_content,
                "links": links
            }
            
    except Exception as e:
        print(f"❌ Scraping error: {e}")
        return {
            "url": url,
            "error": str(e),
            "text_content": f"Failed to scrape website: {str(e)}"
        }


async def call_openai(messages: list) -> str:
    """Call OpenAI API"""
    try:
        import openai
        openai.api_key = OPENAI_API_KEY
        
        response = await asyncio.to_thread(
            lambda: openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ OpenAI Error: {e}")
        raise


async def call_local_llm(messages: list) -> str:
    """Call local LLM via Ollama"""
    try:
        import requests
        
        # Format messages for Ollama
        prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
        
        response = await asyncio.to_thread(
            lambda: requests.post(
                f"{OLLAMA_API_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                },
                timeout=120
            )
        )
        
        if response.status_code == 200:
            return response.json()["response"]
        else:
            raise Exception(f"Ollama error: {response.text}")
            
    except Exception as e:
        print(f"❌ Local LLM Error: {e}")
        raise


async def get_ai_response(messages: list) -> str:
    """Get response from AI with fallback"""
    if USE_OPENAI:
        try:
            return await call_openai(messages)
        except Exception as e:
            print(f"⚠️ Falling back to local LLM: {e}")
    
    if USE_LOCAL_LLM:
        try:
            return await call_local_llm(messages)
        except Exception as e:
            print(f"❌ Both AI methods failed: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to get AI response. Make sure Ollama is running or OpenAI API key is set."
            )
    
    raise HTTPException(status_code=500, detail="No AI service configured")


# ==================== API Endpoints ====================

@app.get("/")
async def root():
    """Root endpoint - serve frontend"""
    return FileResponse("index.html")


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "mongodb": "connected" if db else "disconnected",
        "openai": "configured" if USE_OPENAI else "not_configured",
        "local_llm": "available" if USE_LOCAL_LLM else "not_available"
    }


# ==================== Chat Endpoints ====================

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Send a message and get AI response. Detects URLs and scrapes them with Playwright"""
    try:
        # Get or create conversation
        if request.conversation_id:
            try:
                conv_id = ObjectId(request.conversation_id)
                conversation = await db.conversations.find_one({"_id": conv_id})
                if not conversation:
                    raise HTTPException(status_code=404, detail="Conversation not found")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid conversation ID: {e}")
        else:
            # Create new conversation with first message as title
            title = request.message[:50] if len(request.message) > 50 else request.message
            conversation = {
                "title": title,
                "messages": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "user_id": "default"
            }
            result = await db.conversations.insert_one(conversation)
            conversation["_id"] = result.inserted_id
        
        # Detect URLs in the message
        urls = extract_urls(request.message)
        user_message_content = request.message
        
        # If URLs found, scrape them
        if urls:
            print(f"🔍 Found {len(urls)} URL(s) in message")
            website_data_parts = []
            
            for url in urls[:3]:  # Limit to 3 URLs to avoid timeouts
                scraped_data = await scrape_website(url)
                
                # Format scraped data for AI context
                if "error" not in scraped_data:
                    data_summary = f"""
Website Analysis for: {scraped_data.get('url')}
Title: {scraped_data.get('title', 'N/A')}
Description: {scraped_data.get('description', 'N/A')}
Content: {scraped_data.get('text_content', 'N/A')[:500]}
"""
                    website_data_parts.append(data_summary)
                else:
                    website_data_parts.append(f"Error analyzing {url}: {scraped_data.get('error')}")
            
            # Append website data to message for AI context
            if website_data_parts:
                user_message_content = f"""
User Question: {request.message}

Website Data Retrieved:
{chr(10).join(website_data_parts)}

Please analyze this website data and answer the user's question."""
        
        # Add user message
        user_message = Message(role="user", content=request.message)
        
        # Format messages for AI (use enhanced content if URLs were present)
        messages_for_ai = [
            {"role": msg.role, "content": msg.content}
            for msg in (
                [Message(**m) if isinstance(m, dict) else m 
                 for m in conversation.get("messages", [])]
            )
        ]
        
        # Add the current message with website data context
        messages_for_ai.append({
            "role": "user",
            "content": user_message_content
        })
        
        # Get AI response
        ai_response_text = await get_ai_response(messages_for_ai)
        assistant_message = Message(role="assistant", content=ai_response_text)
        
        # Update conversation
        updated_messages = [
            {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp.isoformat()}
            for msg in (
                [Message(**m) if isinstance(m, dict) else m 
                 for m in conversation.get("messages", [])]
                + [user_message, assistant_message]
            )
        ]
        
        await db.conversations.update_one(
            {"_id": conversation["_id"]},
            {
                "$set": {
                    "messages": updated_messages,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return ChatResponse(
            success=True,
            conversation_id=str(conversation["_id"]),
            title=conversation["title"],
            message=assistant_message,
            all_messages=[Message(**m) if isinstance(m, dict) else m for m in updated_messages]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.get("/api/conversations")
async def list_conversations():
    """List all conversations"""
    try:
        conversations = await db.conversations.find(
            {"user_id": "default"}
        ).sort("updated_at", -1).to_list(50)
        
        items = []
        for conv in conversations:
            items.append(
                ConversationListItem(
                    id=str(conv["_id"]),
                    title=conv["title"],
                    created_at=conv["created_at"],
                    updated_at=conv["updated_at"],
                    message_count=len(conv.get("messages", []))
                )
            )
        
        return {"conversations": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list conversations: {str(e)}")


@app.get("/api/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a specific conversation"""
    try:
        conv_id = ObjectId(conversation_id)
        conversation = await db.conversations.find_one({"_id": conv_id})
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        messages = [
            Message(**msg) if isinstance(msg, dict) else msg
            for msg in conversation.get("messages", [])
        ]
        
        return {
            "id": str(conversation["_id"]),
            "title": conversation["title"],
            "messages": messages,
            "created_at": conversation["created_at"],
            "updated_at": conversation["updated_at"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid conversation ID: {str(e)}")


@app.delete("/api/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    try:
        conv_id = ObjectId(conversation_id)
        result = await db.conversations.delete_one({"_id": conv_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"message": "Conversation deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid conversation ID: {str(e)}")


@app.post("/api/conversation/{conversation_id}/title")
async def update_conversation_title(conversation_id: str, title: dict):
    """Update conversation title"""
    try:
        conv_id = ObjectId(conversation_id)
        result = await db.conversations.update_one(
            {"_id": conv_id},
            {"$set": {"title": title.get("title", ""), "updated_at": datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"message": "Title updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid conversation ID: {str(e)}")


@app.post("/api/conversation/new")
async def new_conversation():
    """Create a new empty conversation"""
    try:
        conversation = {
            "title": "New Conversation",
            "messages": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "user_id": "default"
        }
        result = await db.conversations.insert_one(conversation)
        
        return {
            "conversation_id": str(result.inserted_id),
            "title": "New Conversation"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
