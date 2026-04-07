# ChatGPT-Like AI Application with MongoDB

A full-stack ChatGPT-like application built with FastAPI, MongoDB, and AI integration (OpenAI + Local LLM).

## Features

✨ **AI Chat Interface**

- Modern ChatGPT-inspired UI
- Real-time messaging
- Conversation history
- Multiple conversations support

🗄️ **Database**

- MongoDB for persistent storage
- Conversation management
- Message history

🤖 **AI Integration**

- OpenAI API support (GPT-3.5, GPT-4)
- Local LLM support via Ollama
- Automatic fallback between AI services

📱 **Frontend**

- Responsive design
- Dark/Light UI
- Real-time updates
- Conversation sidebar

## Prerequisites

### 1. **MongoDB**

#### Option A: Local MongoDB (Recommended for development)

**Windows:**

```bash
# Download from https://www.mongodb.com/try/download/community
# Or use Chocolatey:
choco install mongodb-community

# Start MongoDB:
mongod
```

**Mac:**

```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

**Linux (Ubuntu):**

```bash
sudo apt-get install -y mongodb

# Start the service:
sudo systemctl start mongodb
```

#### Option B: MongoDB Atlas (Cloud - Free)

1. Go to https://www.mongodb.com/cloud/atlas
2. Sign up for free
3. Create a cluster
4. Get connection string
5. Add to `.env`:

```
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
```

### 2. **Local LLM (Ollama) - Optional but Recommended**

Install Ollama from https://ollama.ai

Then pull a model:

```bash
ollama pull mistral
# or
ollama pull neural-chat
```

Start Ollama:

```bash
ollama serve
```

### 3. **OpenAI API Key - Optional**

Get your API key from https://platform.openai.com/api-keys

Add to `.env`:

```
OPENAI_API_KEY=sk-your-key-here
```

## Installation

1. **Install Python dependencies:**

```bash
pip install -r requirements.txt
```

2. **Download Playwright browsers:**

```bash
playwright install chromium
```

3. **Configure `.env` file:**

```bash
# Edit .env and add your configuration
# See .env for all options
```

## Running the Application

### Terminal 1: Start MongoDB (if using local)

```bash
mongod
```

### Terminal 2: Start Ollama (if using local LLM)

```bash
ollama serve
```

### Terminal 3: Start the Chat App

```bash
python chat_app.py
```

You should see:

```
✅ Connected to MongoDB: mongodb://localhost:27017
✅ Database: chatgpt_db
INFO:     Uvicorn running on http://0.0.0.0:8000
```

4. **Open Browser:**
   Navigate to: **http://localhost:8000**

## Usage

### Basic Chat

1. Type your message in the input field
2. Press Enter or click Send
3. Wait for AI response
4. Continue conversation

### Manage Conversations

- **New Chat**: Click "+ New Chat" button
- **View History**: Click conversation in sidebar
- **Delete**: Hover over conversation and click ✕
- **Rename**: (Future feature)

## API Endpoints

### Chat

- `POST /api/chat` - Send message and get response
- `GET /api/conversations` - List all conversations
- `GET /api/conversation/{id}` - Get specific conversation
- `DELETE /api/conversation/{id}` - Delete conversation

### Health

- `GET /health` - Check API status

## Configuration

### `.env` Options

```
# MongoDB
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=chatgpt_db

# OpenAI
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-3.5-turbo

# Local LLM
OLLAMA_API_URL=http://localhost:11434
OLLAMA_MODEL=mistral

# Debug
DEBUG=True
```

## AI Service Priority

The app tries AI services in this order:

1. **OpenAI API** (if key is configured)
2. **Local LLM (Ollama)** (if available)

If OpenAI fails, it automatically falls back to Ollama.

## Database Structure

```
chatgpt_db
└── conversations
    ├── _id: ObjectId
    ├── title: String
    ├── messages: Array[
    │   ├── role: "user" | "assistant"
    │   ├── content: String
    │   └── timestamp: DateTime
    │ ]
    ├── created_at: DateTime
    ├── updated_at: DateTime
    └── user_id: String
```

## Examples

### Using with Python Client

```python
import requests

# Send a message
response = requests.post("http://localhost:8000/api/chat", json={
    "message": "Hello! How are you?",
    "model": "gpt-3.5-turbo"
})

data = response.json()
print(f"Assistant: {data['message']['content']}")
```

### Using cURL

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is Python?",
    "model": "gpt-3.5-turbo"
  }'
```

## Troubleshooting

### MongoDB Connection Failed

```
❌ Error: Failed to connect to MongoDB
```

**Solution:**

- Make sure MongoDB is running: `mongod`
- Check MONGODB_URL in .env
- Verify MongoDB is on port 27017

### No AI Response Available

```
❌ Error: No AI service configured
```

**Solution:**

- Set OPENAI_API_KEY in .env, OR
- Install and start Ollama, OR
- Check both services are running

### Ollama Not Found

```
❌ Local LLM Error: Connection refused
```

**Solution:**

- Install Ollama: https://ollama.ai
- Start Ollama: `ollama serve`
- Make sure port 11434 is available

### OpenAI Rate Limited

```
❌ OpenAI Error: Rate limit exceeded
```

**Solution:**

- Wait a moment before sending more messages
- Use local Ollama as fallback (it will automatically)
- Check your API quota at https://platform.openai.com

## Performance Tips

1. **Use Ollama for instant responses** (no API calls)
2. **Keep conversation length reasonable** (long histories slow down responses)
3. **Run MongoDB locally** for faster database operations
4. **Use gpt-3.5-turbo** instead of gpt-4 for cost and speed

## Future Enhancements

- [ ] User authentication
- [ ] Multiple users support
- [ ] Conversation renaming
- [ ] Export conversations as PDF/JSON
- [ ] Voice input/output
- [ ] Image generation
- [ ] Plugin system
- [ ] Custom system prompts

## API Response Examples

### Successful Chat Response

```json
{
  "success": true,
  "conversation_id": "507f1f77bcf86cd799439011",
  "title": "Hello! How are you?",
  "message": {
    "role": "assistant",
    "content": "I'm doing well, thank you for asking! How can I help you today?",
    "timestamp": "2024-04-06T10:30:00"
  },
  "all_messages": [...]
}
```

### Error Response

```json
{
  "detail": "Failed to connect to MongoDB: Connection refused"
}
```

## Development

### Project Structure

```
Model Practical/
├── chat_app.py          # Main FastAPI application
├── models.py            # Pydantic models
├── config.py            # Configuration
├── index.html           # Frontend
├── .env                 # Environment variables
├── requirements.txt     # Python dependencies
└── README_CHAT.md       # This file
```

### Making Changes

1. **Backend Changes**: Edit `chat_app.py` or `models.py`
2. **Frontend Changes**: Edit `index.html`
3. **Configuration**: Edit `.env`

Restart the server to apply changes.

## Support

For issues:

1. Check `.env` configuration
2. Verify MongoDB is running
3. Check server logs
4. Verify AI service is available (OpenAI or Ollama)

## License

MIT License

---

**Happy Chatting! 🚀**
