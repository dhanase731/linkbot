"""
Chat + Web Scraper Application with Ollama AI
- MongoDB for conversation storage
- Playwright for web scraping
- Ollama llama2 for AI responses
- Chat interface with MongoDB persistence
- Direct scraper API
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import motor.motor_asyncio
from bson import ObjectId
from datetime import datetime
import asyncio
import re
import requests
from urllib.parse import urlparse
from playwright.async_api import async_playwright

from models import Message, ConversationListItem, ChatRequest, ChatResponse, ScrapeRequest, ParagraphSummarizationRequest, WebsiteAnalysisRequest

# MongoDB config
MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "chatgpt_db"

# Ollama config
OLLAMA_ENDPOINT = "http://localhost:11434"
OLLAMA_MODEL = "llama2"
OLLAMA_TIMEOUT = 300  # 5 minutes - llama2 can be slow on first response

# Initialize FastAPI
app = FastAPI(
    title="Chat + Web Scraper",
    description="Chat interface with Playwright web scraping (No AI)",
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
client = None
db = None


@app.on_event("startup")
async def startup():
    """Connect to MongoDB on startup (optional)"""
    global client, db
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
        await client.server_info()
        db = client[DATABASE_NAME]
        print(f"\n[OK] Connected to MongoDB: {MONGODB_URL}")
        print(f"[OK] Database: {DATABASE_NAME}")
    except Exception as e:
        print(f"[WARN] MongoDB not available: {type(e).__name__}")
        print(f"[WARN] Running without conversation persistence")
        db = None


@app.on_event("shutdown")
async def shutdown():
    """Close MongoDB connection on shutdown"""
    if client:
        client.close()


def get_comprehensive_website_analysis(website_data: dict) -> str:
    """Use Ollama to provide comprehensive website analysis"""
    try:
        title = website_data.get('title', 'Unknown')
        description = website_data.get('description', '')
        content = website_data.get('text_content', '')
        url = website_data.get('url', '')
        
        analysis_prompt = f"""Analyze this website and provide a detailed assessment:

WEBSITE INFORMATION:
- URL: {url}
- Title: {title}
- Description: {description}
- Content Preview: {content[:800]}

Please answer these questions about the website:

0. **Summary**: Give a clear summary in exactly 10 numbered points.
    - Format strictly as 1) ... through 10) ...
    - Keep each point concise and readable.
    - Cover what the site is, who it is for, what it offers, and why it is useful.
    - Do not repeat the Website Purpose section.
    - Do not repeat the Key Features section.

1. **Website Purpose**: What is the main use and purpose of this website? What problems does it solve?
    - Write this section in exactly 4 lines.
    - Keep the tone natural and humanized.
    - Do not use bullets for this section.

2. **Technology Stack**: Based on the URL, description, and content, what technologies/frameworks do you think this website was built with? (e.g., React, Django, Node.js, PHP, etc.)

3. **Integrated APIs**: What third-party APIs or services might be integrated with this website? (e.g., payment gateways, social media, analytics, etc.)

4. **Target Audience**: Who is the primary target audience for this website?

5. **Key Features**: What are the main features or services offered?

Provide concise, accurate answers based on the information provided."""

        analysis = call_ollama(analysis_prompt, "")
        
        # If Ollama returns a fallback message, use the structured fallback analysis instead
        if "offline response" in analysis.lower() or "currently unavailable" in analysis.lower():
            analysis = generate_fallback_website_analysis(url, title, content)

        # Enforce formatting and uniqueness constraints
        analysis = enforce_unique_humanized_summary(analysis, title=title, url=url)
        analysis = enforce_website_purpose_four_lines(analysis)
        
        return analysis
        
    except Exception as e:
        print(f"[ERROR] Website analysis error: {e}")
        url = website_data.get('url', 'unknown')
        title = website_data.get('title', '')
        content = website_data.get('text_content', '')
        return generate_fallback_website_analysis(url, title, content)


def summarize_paragraph_personalized(paragraph: str, style: str = "concise") -> str:
    """Use Ollama to provide personalized paragraph summarization"""
    try:
        summary_prompt = f"""Please summarize this paragraph in a {style} way:

PARAGRAPH:
{paragraph}

SUMMARIZED:"""

        summary = call_ollama(summary_prompt, "")
        return summary
        
    except Exception as e:
        print(f"[ERROR] Paragraph summarization error: {e}")
        return "Unable to summarize paragraph at this time."


# ==================== Utilities ====================

def extract_urls(text):
    """Extract URLs from text"""
    url_pattern = r'https?://[^\s]+'
    return re.findall(url_pattern, text)

def format_humanized_purpose_four_lines(raw_text: str) -> str:
    """Convert purpose text into exactly 4 human-readable lines without boilerplate fillers."""
    text = re.sub(r"\s+", " ", (raw_text or "").strip())
    if not text:
        text = "This website provides online information or services for its intended users."

    # Split by sentence-like boundaries first
    parts = [p.strip() for p in re.split(r'(?<=[.!?])\s+', text) if p.strip()]
    if not parts:
        parts = [text]

    # Ensure we have enough pieces by chunking long sentences
    while len(parts) < 4:
        longest_idx = max(range(len(parts)), key=lambda i: len(parts[i]))
        seg = parts[longest_idx]
        words = seg.split()
        if len(words) < 8:
            parts.append(seg)
            continue
        mid = len(words) // 2
        left = " ".join(words[:mid]).strip()
        right = " ".join(words[mid:]).strip()
        parts[longest_idx] = left
        parts.insert(longest_idx + 1, right)

    # Keep exactly 4 lines
    if len(parts) > 4:
        parts = parts[:3] + [" ".join(parts[3:]).strip()]

    return "\n".join(parts[:4])

def enforce_website_purpose_four_lines(analysis_text: str) -> str:
    """Force the Website Purpose section in analysis text to exactly 4 lines."""
    if not analysis_text:
        return analysis_text

    pattern = re.compile(
        r'(1\.\s*\*\*Website Purpose\*\*:\s*)([\s\S]*?)(\n\s*2\.\s*\*\*Technology Stack\*\*:)',
        re.IGNORECASE
    )
    match = pattern.search(analysis_text)
    if not match:
        return analysis_text

    prefix, purpose_body, suffix = match.group(1), match.group(2), match.group(3)
    purpose_formatted = format_humanized_purpose_four_lines(purpose_body)
    return analysis_text[:match.start()] + prefix + purpose_formatted + suffix + analysis_text[match.end():]


def enforce_unique_humanized_summary(analysis_text: str, title: str = "", url: str = "") -> str:
    """Ensure summary is unique, website-specific, humanized, and does not reuse purpose/key-features text."""
    if not analysis_text:
        return analysis_text

    s_match = re.search(
        r'(0\.\s*\*\*Summary\*\*:\s*)([\s\S]*?)(\n\s*1\.\s*\*\*Website Purpose\*\*:)',
        analysis_text,
        re.IGNORECASE
    )
    p_match = re.search(
        r'1\.\s*\*\*Website Purpose\*\*:\s*([\s\S]*?)(?=\n\s*2\.\s*\*\*Technology Stack\*\*:)',
        analysis_text,
        re.IGNORECASE
    )
    f_match = re.search(
        r'5\.\s*\*\*Key Features\*\*:\s*([\s\S]*?)$',
        analysis_text,
        re.IGNORECASE
    )

    if not s_match:
        return analysis_text

    purpose_text = (p_match.group(1).strip() if p_match else "")
    features_text = (f_match.group(1).strip() if f_match else "")

    audience_match = re.search(
        r'4\.\s*\*\*Target Audience\*\*:\s*([\s\S]*?)(?=\n\s*5\.\s*\*\*Key Features\*\*:|$)',
        analysis_text,
        re.IGNORECASE
    )
    tech_match = re.search(
        r'2\.\s*\*\*Technology Stack\*\*:\s*([\s\S]*?)(?=\n\s*3\.\s*\*\*Integrated APIs\*\*:|$)',
        analysis_text,
        re.IGNORECASE
    )
    api_match = re.search(
        r'3\.\s*\*\*Integrated APIs\*\*:\s*([\s\S]*?)(?=\n\s*4\.\s*\*\*Target Audience\*\*:|$)',
        analysis_text,
        re.IGNORECASE
    )

    audience_text = re.sub(r'\s+', ' ', (audience_match.group(1).strip() if audience_match else 'general users')).strip().rstrip('. ')
    tech_text = re.sub(r'\s+', ' ', (tech_match.group(1).strip() if tech_match else 'modern web technologies')).strip()
    api_text = re.sub(r'\s+', ' ', (api_match.group(1).strip() if api_match else 'standard service integrations')).strip()
    purpose_short = re.sub(r'\s+', ' ', (p_match.group(1).strip() if p_match else 'online services')).strip()

    # Website identity hints
    site_name = (title or "").strip()
    if site_name:
        site_name = re.split(r'[\-|·|:|\|]', site_name)[0].strip()
    if not site_name:
        try:
            site_name = (urlparse(url).hostname or "this website").replace("www.", "")
        except Exception:
            site_name = "this website"

    def short(txt: str, limit: int = 120) -> str:
        txt = re.sub(r'\s+', ' ', txt).strip()
        if len(txt) <= limit:
            return txt
        return txt[:limit].rsplit(' ', 1)[0] + '...'

    # Build a deterministic, humanized and unique 10-point summary.
    core_lines = [
        f"1) {site_name} appears to be a focused platform built around {short(purpose_short, 110)}.",
        f"2) The site experience feels practical and tailored to users like {short(audience_text, 100)}.",
        "3) Its layout suggests users are expected to discover information quickly and act with minimal friction.",
        "4) The messaging style is direct and product-oriented rather than purely informational.",
        f"5) The technical footprint points to a modern architecture ({short(tech_text, 125)}).",
        f"6) Integration signals suggest ecosystem connectivity ({short(api_text, 120)}).",
        f"7) {site_name} seems designed for repeat engagement instead of one-time browsing.",
        "8) The overall flow indicates emphasis on reliability, usability, and clear user outcomes.",
        "9) The platform appears mature enough to support both individual and team-based usage scenarios.",
        f"10) In short, {site_name} looks purposeful, user-centric, and aligned to real-world needs."
    ]

    # Safety guard: avoid accidental phrase reuse from purpose/features.
    lowered_purpose = purpose_text.lower()
    lowered_features = features_text.lower()
    normalized = []
    for i, line in enumerate(core_lines, 1):
        l = line.lower()
        if (lowered_purpose and l in lowered_purpose) or (lowered_features and l in lowered_features):
            line = f"{i}) This point summarizes the experience in a user-friendly way without repeating section text."
        normalized.append(re.sub(r'^\s*\d+\)\s*', f"{i}) ", line))

    new_summary = "\n".join(normalized)
    return analysis_text[:s_match.start()] + s_match.group(1) + new_summary + s_match.group(3) + analysis_text[s_match.end():]

def assess_url_risk(url: str, title: str = "", description: str = "", content: str = "") -> dict:
    """Assess URL risk with simple heuristics and return level/reasons."""
    reasons = []
    score = 0

    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        scheme = (parsed.scheme or "").lower()
    except Exception:
        return {
            "level": "likely unsafe",
            "confidence": "medium",
            "reasons": ["URL format could not be reliably parsed."],
        }

    # Reserved demonstration domains (IANA): example.com / .org / .net
    if hostname in {"example.com", "www.example.com", "example.org", "www.example.org", "example.net", "www.example.net"}:
        return {
            "level": "likely unsafe",
            "confidence": "medium",
            "reasons": [
                "This is a reserved demonstration domain and is not an official real-world service.",
                "It is safe for documentation/testing, but should not be used for login or payments.",
            ],
        }

    # Known trusted domains
    trusted_domains = {
        "chatgpt.com", "www.chatgpt.com", "openai.com", "www.openai.com",
        "github.com", "www.github.com", "google.com", "www.google.com",
        "wikipedia.org", "www.wikipedia.org", "microsoft.com", "www.microsoft.com"
    }
    if hostname in trusted_domains:
        return {
            "level": "likely safe",
            "confidence": "high",
            "reasons": [
                "The domain matches a widely recognized official website.",
                "No high-risk phishing indicators were detected in the URL structure.",
            ],
        }

    # 1) HTTPS check
    if scheme != "https":
        score += 1
        reasons.append("The link is not using HTTPS.")

    # 2) IP-address based URLs
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", hostname):
        score += 3
        reasons.append("The link uses a raw IP address instead of a normal domain name.")

    # 3) Very long or complex hostname
    if len(hostname) > 40 or hostname.count("-") >= 3:
        score += 1
        reasons.append("The domain name looks unusually long or complex.")

    # 4) Suspicious phishing keywords in URL path/query
    suspicious_terms = [
        "login", "verify", "update", "secure", "account", "wallet",
        "otp", "bank", "signin", "reset", "unlock", "confirm"
    ]
    lower_url = url.lower()
    term_hits = [term for term in suspicious_terms if term in lower_url]
    if len(term_hits) >= 3:
        score += 3
        reasons.append("The URL contains many high-risk keywords often seen in phishing pages.")
    elif len(term_hits) >= 1:
        score += 1
        reasons.append("The URL contains sensitive-action keywords (for example: login/verify/reset).")

    # 5) Common typo-squatting patterns
    typosquat_patterns = ["paypa1", "g00gle", "micr0soft", "faceb00k", "amaz0n", "goog1e"]
    if any(p in hostname for p in typosquat_patterns):
        score += 3
        reasons.append("The domain appears to mimic a known brand using look-alike spelling.")

    # 6) Soft content signal
    text_blob = f"{title} {description} {content[:1000]}".lower()
    content_terms = ["enter otp", "verify account", "urgent action", "password expired", "suspended"]
    if any(t in text_blob for t in content_terms):
        score += 1
        reasons.append("Page text includes urgent credential-related language.")

    # Risk mapping
    if score >= 6:
        level = "fraudulent/phishing"
        confidence = "high"
    elif score >= 3:
        level = "likely unsafe"
        confidence = "medium"
    else:
        level = "suspicious"
        confidence = "low"

    if not reasons:
        reasons.append("No strong phishing indicators were detected automatically, but caution is still recommended.")

    return {"level": level, "confidence": confidence, "reasons": reasons}


def build_humble_safety_message(risk: dict) -> str:
    """Create a humble, user-friendly safety advisory."""
    level = risk.get("level", "suspicious")
    confidence = risk.get("confidence", "low")
    reasons = risk.get("reasons", [])[:3]

    if level == "likely safe":
        intro = "This link looks legitimate based on current checks, but it is always good to stay cautious online."
    elif confidence == "high":
        intro = "I want to respectfully flag this link as potentially fraudulent/phishing based on multiple warning signs."
    elif confidence == "medium":
        intro = "I might be mistaken, but this link looks likely unsafe based on a few warning signs."
    else:
        intro = "I may not be fully certain, but this link appears suspicious and deserves caution."

    reason_lines = "\n".join([f"- {r}" for r in reasons])

    return f"""Link Safety:
- Risk Level: {level}
- Confidence: {confidence}

{intro}
Please avoid entering personal, password, OTP, or payment details on this link.
When possible, visit the official website directly instead of opening unknown links.

Why this was flagged:
{reason_lines}
"""


def call_ollama(prompt: str, context: str = "") -> str:
    """Call Ollama API with llama2 model (synchronous)"""
    try:
        print(f"[INFO] Calling Ollama ({OLLAMA_MODEL}) at {OLLAMA_ENDPOINT}...")
        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        
        # First, check if Ollama is reachable
        try:
            health_check = requests.get(f"{OLLAMA_ENDPOINT}/api/tags", timeout=5)
            if health_check.status_code != 200:
                print(f"[WARN] Ollama health check failed: {health_check.status_code}")
                return generate_fallback_response(prompt, context)
        except:
            print("[WARN] Ollama is not reachable, using fallback response")
            return generate_fallback_response(prompt, context)
        
        response = requests.post(
            f"{OLLAMA_ENDPOINT}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False,
                "temperature": 0.7
            },
            timeout=OLLAMA_TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result.get("response", "I couldn't generate a response")
            print(f"[OK] Ollama responded: {ai_response[:100]}...")
            return ai_response
        else:
            print(f"[ERROR] Ollama error: {response.status_code} {response.text}")
            return generate_fallback_response(prompt, context)
    except requests.exceptions.Timeout:
        print(f"[ERROR] Ollama timeout after {OLLAMA_TIMEOUT}s")
        return "The AI service is processing your request slowly. Using offline mode: " + generate_fallback_response(prompt, context)
    except requests.exceptions.ConnectionError as e:
        print(f"[ERROR] Cannot connect to Ollama: {e}")
        print("[INFO] Ollama may have crashed. Restart it by running: ollama serve")
        return generate_fallback_response(prompt, context)
    except Exception as e:
        print(f"[ERROR] Ollama error: {type(e).__name__}: {e}")
        return generate_fallback_response(prompt, context)


def generate_fallback_website_analysis(url: str, title: str = "", content: str = "") -> str:
    """Generate a structured fallback analysis when Ollama is unavailable"""
    # Use heuristics to make educated guesses based on URL and content
    domain = url.split('/')[2].lower() if len(url.split('/')) > 2 else ''
    
    # Website Purpose analysis based on URL patterns
    if domain in {'example.com', 'www.example.com', 'example.org', 'www.example.org', 'example.net', 'www.example.net'}:
        purpose = "This is a reserved example domain maintained for documentation and testing. It is not intended to represent a real production business website."
    elif 'chatgpt.com' in domain or 'openai.com' in domain:
        purpose = "ChatGPT is an AI assistant platform by OpenAI that helps users generate text, solve problems, write code, summarize content, and interact conversationally with large language models."
    elif 'github' in domain:
        purpose = "GitHub is a web-based Git repository hosting service that provides distributed version control and collaboration features for software development projects."
    elif 'stackoverflow' in domain:
        purpose = "Stack Overflow is a question and answer website for programmers to learn, share knowledge, and solve coding problems."
    elif 'google' in domain:
        purpose = "Google is a search engine and technology company providing search, email, cloud services, and various other digital tools."
    elif 'facebook' in domain or 'meta' in domain:
        purpose = "Facebook is a social media platform designed for connecting people and sharing content, news, and messaging."
    elif 'twitter' in domain or 'x.com' in domain:
        purpose = "Twitter (formerly) is a microblogging and social networking platform for sharing short messages and real-time updates."
    elif 'amazon' in domain:
        purpose = "Amazon is an e-commerce and cloud services platform selling products online and providing AWS services."
    elif 'linkedin' in domain:
        purpose = "LinkedIn is a professional networking platform focused on career development, job searching, and business connections."
    elif 'youtube' in domain:
        purpose = "YouTube is a video sharing and streaming platform where users can upload, watch, share, and comment on videos."
    elif 'wikipedia' in domain:
        purpose = "Wikipedia is a free online encyclopedia providing reliable information on various topics, editable by users."
    else:
        purpose = f"Based on the domain '{domain}', this website provides services or information in its respective industry vertical."

    # Humanized 4-line purpose text generated from source purpose (no boilerplate fillers)
    purpose = format_humanized_purpose_four_lines(purpose)
    
    # Technology Stack - educated guesses
    if domain in {'example.com', 'www.example.com', 'example.org', 'www.example.org', 'example.net', 'www.example.net'}:
        tech_stack = "This page is generally a static demonstration page. No reliable production technology stack should be inferred from it."
    elif 'chatgpt.com' in domain or 'openai.com' in domain:
        tech_stack = "Likely built with a modern React/Next.js frontend, Python-based backend services, large-scale inference infrastructure for LLMs, vector retrieval systems, and cloud-native orchestration."
    elif 'github' in domain:
        tech_stack = "GitHub likely uses Ruby on Rails for backend, React/TypeScript for frontend, PostgreSQL for databases, with Kubernetes for container orchestration and GraphQL for APIs."
    elif 'google' in domain:
        tech_stack = "Google uses custom C++ backend infrastructure, JavaScript/TypeScript frontend, BigTable/Spanner databases, and proprietary distributed computing systems."
    elif 'facebook' in domain or 'meta' in domain:
        tech_stack = "Meta uses PHP-derived Hack language, React (their framework) for frontend, custom MySQL-based databases, and C++ for performance-critical systems."
    elif 'amazon' in domain:
        tech_stack = "Amazon uses Java, Node.js and Python for various services, JavaScript for frontend, DynamoDB and S3 for storage, running on AWS infrastructure."
    else:
        tech_stack = "Modern stack likely includes JavaScript/TypeScript, Python or Node.js backend, React/Vue frontend, with cloud hosting and databases like PostgreSQL or MongoDB."
    
    # Integrated APIs - common patterns
    if domain in {'example.com', 'www.example.com', 'example.org', 'www.example.org', 'example.net', 'www.example.net'}:
        apis = "No known production third-party integrations are implied. This domain is primarily for examples and tutorials."
    elif 'chatgpt.com' in domain or 'openai.com' in domain:
        apis = "Likely integrates OpenAI model APIs, authentication/identity services, billing/payment services, moderation/safety systems, analytics, and optional tool integration endpoints."
    elif 'github' in domain:
        apis = "GitHub REST API v3, GraphQL API, OAuth 2.0, Stripe for payments, Google Analytics, Slack integrations, and CI/CD webhook integrations."
    elif 'google' in domain:
        apis = "Google Maps API, Gmail API, Google Drive API, Google Analytics, YouTube API, Google Cloud APIs, and OAuth authentication."
    elif 'amazon' in domain:
        apis = "AWS APIs (S3, EC2, Lambda, DynamoDB), Payment processing, Analytics services, AWS SDK integrations, and third-party seller integrations."
    else:
        apis = "Likely includes REST APIs, OAuth authentication, payment gateways (Stripe/PayPal), analytics services, and CDN integrations."
    
    # Target Audience
    if domain in {'example.com', 'www.example.com', 'example.org', 'www.example.org', 'example.net', 'www.example.net'}:
        audience = "Developers, students, and documentation readers using sample links in tutorials or technical examples."
    elif 'chatgpt.com' in domain or 'openai.com' in domain:
        audience = "General users, professionals, developers, students, researchers, and teams that need AI assistance for writing, coding, analysis, learning, and productivity tasks."
    elif 'github' in domain:
        audience = "Software developers, open-source contributors, development teams, enterprises, and organizations managing code repositories."
    elif 'stackoverflow' in domain:
        audience = "Programmers, software developers, students learning to code, and technical professionals seeking solutions."
    elif 'facebook' in domain or 'meta' in domain:
        audience = "General public, all ages, businesses for marketing, content creators, and individuals sharing personal content."
    elif 'linkedin' in domain:
        audience = "Professionals, job seekers, recruiters, business executives, and companies for B2B marketing and recruitment."
    else:
        audience = "The target audience varies based on the website's purpose - could be consumers, professionals, businesses, or general public."
    
    # Key Features
    if domain in {'example.com', 'www.example.com', 'example.org', 'www.example.org', 'example.net', 'www.example.net'}:
        features = "Provides a neutral placeholder page for documentation, demos, and testing URL handling safely."
    elif 'chatgpt.com' in domain or 'openai.com' in domain:
        features = "Conversational AI chat, writing assistance, coding help, reasoning support, summarization, multilingual interaction, file/image-aware workflows (where available), and productivity-focused AI tools."
    elif 'github' in domain:
        features = "Version control with Git, code repositories, pull requests, code reviews, issue tracking, project management, GitHub Actions for CI/CD, Wiki, Gists, and collaboration tools."
    elif 'google' in domain:
        features = "Web search with advanced filtering, Gmail webmail, Google Drive cloud storage, Google Docs collaboration, Google Maps, and various productivity tools."
    elif 'facebook' in domain or 'meta' in domain:
        features = "Profile pages, friend connections, News Feed, messaging, photo/video sharing, groups, marketplace, and advertising platform."
    elif 'amazon' in domain:
        features = "Product search and purchase, shopping cart, payment processing, reviews and ratings, recommendations, Prime membership, and seller marketplace."
    else:
        features = "The platform provides web-based services including user accounts, content management, search functionality, and community interaction features."
    
    # Build an exact 10-point summary for fallback mode (unique from purpose/features)
    summary_lines = [
        f"1) {title if title else domain} is a web platform with a clear product focus.",
        "2) The homepage communicates a clear identity and intent in a simple way.",
        f"3) Primary users: {audience}",
        "4) It delivers practical value through a browser-based experience.",
        "5) Navigation and structure suggest a guided and user-friendly journey.",
        f"6) Likely technical foundation: {tech_stack}",
        f"7) Possible integrations: {apis}",
        "8) The site appears designed for reliability and frequent user interaction.",
        "9) Its structure suggests a balance of usability, scale, and maintainability.",
        "10) Overall, it serves as a focused platform that solves real user needs efficiently."
    ]
    summary = "\n".join(summary_lines)

    # Format as structured analysis
    structured_analysis = f"""0. **Summary**: {summary}

1. **Website Purpose**: {purpose}

2. **Technology Stack**: {tech_stack}

3. **Integrated APIs**: {apis}

4. **Target Audience**: {audience}

5. **Key Features**: {features}"""
    
    print(f"[INFO] Using fallback analysis for {domain}")
    return structured_analysis


def generate_fallback_response(prompt: str, context: str = "") -> str:
    """Generate a fallback response when Ollama is unavailable"""
    # Simple echo-based response
    if context:
        return f"I analyzed the content you shared. You asked: '{prompt}'. The content contains useful information that can help with your query."
    else:
        return f"I received your message: '{prompt}'. This is an offline response since the AI service is currently unavailable. Please try refreshing once Ollama is running."


# ==================== Web Scraping ====================

async def scrape_website_data(url: str) -> dict:
    """Scrape website using Playwright with fallback to requests"""
    try:
        print(f"[INFO] Scraping: {url}")
        
        # First, attempt with Playwright (for JavaScript-heavy sites)
        print(f"  Trying Playwright...")
        playwright_result = await try_playwright_scrape(url)
        if playwright_result and playwright_result.get("success"):
            return playwright_result
        
        # If Playwright fails, fallback to requests library
        print(f"  [WARN] Playwright failed, trying requests library...")
        requests_result = await asyncio.to_thread(try_requests_scrape, url)
        if requests_result and requests_result.get("success"):
            print(f"  [OK] Requests scraper succeeded")
            return requests_result
        
        # Both failed
        error = playwright_result.get("error", "Unknown error") if playwright_result else "All scrapers failed"
        return {
            "success": False,
            "url": url,
            "error": error
        }
            
    except Exception as e:
        print(f"[ERROR] Scraping error: {e}")
        return {
            "success": False,
            "url": url,
            "error": str(e)
        }


async def try_playwright_scrape(url: str) -> dict:
    """Try scraping with Playwright"""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            # Use domcontentloaded instead of networkidle - faster and more reliable
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            except:
                # If that fails, try with commit state (even faster)
                print(f"    [WARN] Fallback to 'commit' wait state")
                await page.goto(url, wait_until="commit", timeout=10000)
            
            # Extract metadata
            title = await page.title()
            
            description = await page.evaluate('''() => {
                const meta = document.querySelector('meta[name="description"]');
                return meta ? meta.getAttribute('content') : '';
            }''')
            
            # Extract headings
            headings = await page.evaluate('''() => {
                const h = {h1: [], h2: [], h3: []};
                document.querySelectorAll('h1').forEach(e => {
                    if(e.innerText.trim()) h.h1.push(e.innerText.trim());
                });
                document.querySelectorAll('h2').forEach(e => {
                    if(e.innerText.trim()) h.h2.push(e.innerText.trim());
                });
                document.querySelectorAll('h3').forEach(e => {
                    if(e.innerText.trim()) h.h3.push(e.innerText.trim());
                });
                return h;
            }''')
            
            # Extract images
            images = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('img[src]'))
                    .map(img => ({src: img.src, alt: img.alt}))
                    .filter(img => img.src && img.src.startsWith('http'))
                    .slice(0, 10);
            }''')
            
            # Extract links
            links = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a[href]'))
                    .map(a => ({url: a.href, text: a.innerText.trim() || a.textContent.trim()}))
                    .filter(l => l.url.startsWith('http') && l.text)
                    .slice(0, 20);
            }''')
            
            # Extract text content
            text_content = await page.locator("body").inner_text()
            text_preview = text_content[:1000] if text_content else ""
            
            await browser.close()
            
            return {
                "success": True,
                "url": url,
                "title": title,
                "description": description,
                "headings": headings,
                "images": images,
                "links": links,
                "text_content": text_preview,
                "word_count": len(text_content.split()) if text_content else 0
            }
            
    except Exception as e:
        print(f"    [ERROR] Playwright error: {type(e).__name__}: {str(e)[:100]}")
        return {
            "success": False,
            "url": url,
            "error": str(e)
        }


def try_requests_scrape(url: str) -> dict:
    """Fallback scraper using requests library (better for bot detection)"""
    try:
        import time
        import random
        from html.parser import HTMLParser
        
        # Headers to look like a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.google.com/',
            'Cache-Control': 'no-cache'
        }
        
        # Retry logic with exponential backoff
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # Add random delay to seem more human-like
                delay = random.uniform(0.5, 2.0) if attempt > 0 else 0
                if delay > 0:
                    print(f"    [RETRY] {attempt + 1}/{max_retries}, waiting {delay:.1f}s...")
                    time.sleep(delay)
                
                response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
                response.raise_for_status()
                break  # Success
                
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt == max_retries - 1:
                    raise  # Last attempt failed
                continue  # Retry
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title = soup.title.string if soup.title else ""
        
        # Extract description
        description = ""
        desc_meta = soup.find('meta', attrs={'name': 'description'})
        if desc_meta:
            description = desc_meta.get('content', '')
        
        # Extract headings
        headings = {
            'h1': [h.get_text().strip() for h in soup.find_all('h1')[:5]],
            'h2': [h.get_text().strip() for h in soup.find_all('h2')[:5]],
            'h3': [h.get_text().strip() for h in soup.find_all('h3')[:5]]
        }
        
        # Extract images
        images = []
        for img in soup.find_all('img', limit=10):
            src = img.get('src', '')
            if src and (src.startswith('http') or src.startswith('/')):
                if not src.startswith('http'):
                    from urllib.parse import urljoin
                    src = urljoin(url, src)
                images.append({'src': src, 'alt': img.get('alt', '')})
        
        # Extract links
        links = []
        for a in soup.find_all('a', href=True, limit=20):
            href = a.get('href', '')
            if href.startswith('http'):
                text = a.get_text().strip()
                if text:
                    links.append({'url': href, 'text': text})
        
        # Extract text content
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text_content = ' '.join(chunk for chunk in chunks if chunk)
        text_preview = text_content[:1000]
        
        print(f"    [OK] Requests scraper succeeded for {url}")
        return {
            "success": True,
            "url": url,
            "title": title,
            "description": description,
            "headings": headings,
            "images": images,
            "links": links,
            "text_content": text_preview,
            "word_count": len(text_content.split())
        }
        
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)[:100]}"
        
        # Check if it's a connection error (site is actively blocking)
        if any(x in str(e).lower() for x in ['connection reset', 'connection refused', 'connection aborted']):
            error_msg = f"Site is blocking automated access: {error_msg}"
            print(f"    [WARN] {error_msg}")
        else:
            print(f"    [ERROR] Requests scraper error: {error_msg}")
        
        return {
            "success": False,
            "url": url,
            "error": error_msg
        }


# ==================== Endpoints ====================

@app.get("/")
async def root():
    """Root endpoint - serve frontend"""
    return FileResponse("index.html")


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "service": "Chat + Web Scraper",
        "features": ["chat", "web-scraping", "mongodb"],
        "mongodb": "connected" if db is not None else "disconnected"
    }


# ==================== Scraper API ====================

@app.post("/api/scrape")
async def scrape(request: ScrapeRequest):
    """Scrape a website"""
    result = await scrape_website_data(request.url)
    return result


@app.post("/api/website-data")
async def website_data(request: ScrapeRequest):
    """Get comprehensive website data"""
    result = await scrape_website_data(request.url)
    return result


@app.post("/api/summarize-paragraph")
async def summarize_paragraph(request: ParagraphSummarizationRequest):
    """Summarize a paragraph using Ollama with personalized style"""
    try:
        print(f"📝 Summarizing paragraph with style: {request.style}")
        summary = await asyncio.to_thread(summarize_paragraph_personalized, request.paragraph, request.style)
        
        return {
            "success": True,
            "original_length": len(request.paragraph),
            "summary_style": request.style,
            "summary": summary
        }
    except Exception as e:
        print(f"[ERROR] Summarization error: {e}")
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")


@app.post("/api/website-analysis")
async def analyze_website(request: WebsiteAnalysisRequest):
    """Get comprehensive website analysis using Ollama"""
    try:
        print(f"[INFO] Analyzing website: {request.url}")
        
        # First scrape the website
        scrape_result = await scrape_website_data(request.url)
        
        if not scrape_result.get("success"):
            return {
                "success": False,
                "url": request.url,
                "error": scrape_result.get("error", "Failed to scrape website")
            }
        
        # Get comprehensive analysis from Ollama
        analysis = await asyncio.to_thread(get_comprehensive_website_analysis, scrape_result)
        
        return {
            "success": True,
            "url": request.url,
            "title": scrape_result.get("title"),
            "description": scrape_result.get("description"),
            "analysis": analysis,
            "website_title": scrape_result.get("title"),
            "word_count": scrape_result.get("word_count")
        }
    except Exception as e:
        print(f"[ERROR] Website analysis error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Website analysis failed: {str(e)}")


# ==================== Chat Endpoints ====================

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat endpoint with web scraping"""
    try:
        conversation_id = None
        
        # Get or create conversation (only if DB is available)
        if db is not None:
            if request.conversation_id:
                try:
                    conv_id = ObjectId(request.conversation_id)
                    conversation = await db.conversations.find_one({"_id": conv_id})
                    if not conversation:
                        raise HTTPException(status_code=404, detail="Conversation not found")
                    conversation_id = str(conv_id)
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Invalid conversation ID: {e}")
            else:
                # Create new conversation
                title = request.message[:50] if len(request.message) > 50 else request.message
                conversation = {
                    "title": title,
                    "messages": [],
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "user_id": "default"
                }
                result = await db.conversations.insert_one(conversation)
                conversation_id = str(result.inserted_id)
        
        # Add user message
        user_message = Message(role="user", content=request.message)
        
        # Detect URLs in message
        urls = extract_urls(request.message)
        assistant_response = None
        
        # If URLs found, scrape them and analyze with Ollama
        if urls:
            print(f"[INFO] Found {len(urls)} URL(s)")

            response_text = ""
            for url in urls[:3]:  # Limit to 3 URLs
                result = await scrape_website_data(url)

                if result["success"]:
                    # Get comprehensive analysis from Ollama
                    print(f"[INFO] Analyzing {url} with Ollama...")
                    analysis = await asyncio.to_thread(get_comprehensive_website_analysis, result)
                    risk = assess_url_risk(
                        url=result.get('url', url),
                        title=result.get('title', ''),
                        description=result.get('description', ''),
                        content=result.get('text_content', '')
                    )
                    safety_note = build_humble_safety_message(risk)

                    response_text += f"""
Website: {result['url']}
Title: {result['title']}

{safety_note}

{analysis}

Additional Stats:
- Total Links: {len(result['links'])}
- Total Images: {len(result['images'])}
- Word Count: {result['word_count']}
"""
                else:
                    error_msg = result.get('error', 'Unknown error')

                    # Check if it's a blocking issue
                    if 'blocking' in error_msg.lower() or 'connection' in error_msg.lower():
                        response_text += f"""Cannot scrape {result['url']}
Reason: Site is blocking automated access

Try these sites instead:
- https://example.com
- https://en.wikipedia.org
- https://github.com
- https://python.org
"""
                    else:
                        response_text += f"Failed to scrape {result['url']}: {error_msg}\n"
            
            assistant_response = Message(role="assistant", content=response_text)
        else:
            # No URLs - use Ollama for regular chat response
            ai_response = await asyncio.to_thread(call_ollama, request.message, "")
            assistant_response = Message(role="assistant", content=ai_response)
        
        # Update conversation in DB (only if DB is available)
        if db is not None and conversation_id is not None:
            updated_messages = [
                {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp.isoformat()}
                for msg in [user_message, assistant_response]
            ]
            
            # Add to existing messages
            existing_messages = conversation.get("messages", [])
            existing_messages.extend(updated_messages)
            
            await db.conversations.update_one(
                {"_id": conversation["_id"]},
                {
                    "$set": {
                        "messages": existing_messages,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        
        # Get all messages for response
        all_messages = []
        if db is not None and conversation_id is not None:
            for m in existing_messages:
                try:
                    if isinstance(m, dict):
                        all_messages.append({
                            "role": m.get("role", "user"),
                            "content": m.get("content", ""),
                            "timestamp": m.get("timestamp", datetime.utcnow().isoformat())
                        })
                    else:
                        all_messages.append({
                            "role": m.role,
                            "content": m.content,
                            "timestamp": m.timestamp.isoformat() if hasattr(m, 'timestamp') else datetime.utcnow().isoformat()
                        })
                except Exception as e:
                    print(f"[ERROR] Error processing message: {e}")
                    continue
        
        return {
            "success": True,
            "conversation_id": conversation_id or "no-db-session",
            "title": conversation.get("title", "Chat") if db is not None and conversation_id is not None else "Chat (No Persistence)",
            "message": {
                "role": assistant_response.role,
                "content": assistant_response.content,
                "timestamp": assistant_response.timestamp.isoformat()
            },
            "all_messages": all_messages
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Chat endpoint error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.get("/api/conversations")
async def list_conversations():
    """List all conversations"""
    try:
        if db is None:
            return {"conversations": []}
        
        conversations = await db.conversations.find(
            {"user_id": "default"}
        ).sort("updated_at", -1).to_list(50)
        
        items = []
        for conv in conversations:
            try:
                item = {
                    "id": str(conv["_id"]),
                    "title": conv.get("title", "Untitled"),
                    "created_at": conv.get("created_at", datetime.utcnow()).isoformat() if isinstance(conv.get("created_at"), datetime) else conv.get("created_at"),
                    "updated_at": conv.get("updated_at", datetime.utcnow()).isoformat() if isinstance(conv.get("updated_at"), datetime) else conv.get("updated_at"),
                    "message_count": len(conv.get("messages", []))
                }
                items.append(item)
            except Exception as e:
                print(f"[ERROR] Error formatting conversation: {e}")
                continue
        
        return {"conversations": items}
    except Exception as e:
        print(f"[ERROR] Error in list_conversations: {e}")
        return {"conversations": []}


@app.get("/api/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a specific conversation"""
    try:
        if db is None:
            return {"conversation_id": conversation_id, "messages": [], "note": "Database not connected"}
        
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
        if db is None:
            raise HTTPException(status_code=500, detail="Database not connected")
        
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
        if db is None:
            raise HTTPException(status_code=500, detail="Database not connected")
        
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
        if db is None:
            import uuid
            conversation_id = str(uuid.uuid4())
            return {
                "conversation_id": conversation_id,
                "title": "New Conversation (No Persistence)"
            }
        
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
    print("\n" + "="*60)
    print("[SERVER] Chat + Web Scraper + Ollama Server")
    print("="*60)
    print("Features:")
    print("   - AI Chat with Ollama llama2")
    print("   - Playwright Web Scraping Integration")
    print("   - MongoDB Conversation Storage")
    print("   - Direct Scraper API (/api/scrape)")
    print(f"   - Ollama Endpoint: {OLLAMA_ENDPOINT}")
    print("="*60)
    print("Open: http://localhost:8001")
    print("Endpoints: /api/chat, /api/scrape, /api/conversations\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)

