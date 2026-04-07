from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Dict, Optional, List
from playwright.async_api import async_playwright
import asyncio

app = FastAPI(
    title="Playwright Scraper API",
    description="Scrape any website using real browser (Playwright)",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScrapeRequest(BaseModel):
    url: str
    timeout: int = 30
    wait_for_selector: Optional[str] = None
    extract_full_text: bool = True
    extract_links: bool = False
    custom_selectors: Optional[Dict[str, str]] = None

class ScrapeResponse(BaseModel):
    success: bool
    url: str
    title: str
    html: Optional[str] = None
    full_text: Optional[str] = None
    data: Dict[str, str] = {}
    links: List[str] = []
    error: Optional[str] = None


class WebsiteDataResponse(BaseModel):
    success: bool
    url: str
    status_code: Optional[int] = None
    title: str
    description: str
    language: Optional[str] = None
    canonical_url: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    og_type: Optional[str] = None
    og_url: Optional[str] = None
    favicon_url: Optional[str] = None
    headings: Dict[str, List[str]] = {}
    images: List[str] = []
    links: List[Dict[str, str]] = []
    text_content: Optional[str] = None
    word_count: int = 0
    error: Optional[str] = None


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape(request: ScrapeRequest):
    """
    Scrape a website and extract data using Playwright.
    
    - **url**: Website URL to scrape
    - **timeout**: Request timeout in seconds (default: 30)
    - **wait_for_selector**: CSS selector to wait for before scraping
    - **extract_full_text**: Extract all visible text from page
    - **extract_links**: Extract all links from the page
    - **custom_selectors**: Dict of {name: css_selector} for custom data extraction
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # Navigate to the URL
            await page.goto(
                request.url, 
                wait_until="networkidle",
                timeout=request.timeout * 1000
            )

            # Wait for specific element if requested
            if request.wait_for_selector:
                try:
                    await page.wait_for_selector(request.wait_for_selector, timeout=10000)
                except:
                    pass

            title = await page.title()
            html = await page.content()

            response = ScrapeResponse(
                success=True,
                url=request.url,
                title=title,
                html=html
            )

            # Extract full visible text
            if request.extract_full_text:
                response.full_text = await page.locator("body").inner_text()

            # Extract custom selectors
            if request.custom_selectors:
                for key, selector in request.custom_selectors.items():
                    try:
                        element = page.locator(selector).first
                        if await element.count() > 0:
                            response.data[key] = await element.inner_text()
                        else:
                            response.data[key] = None
                    except Exception as e:
                        response.data[key] = None

            # Extract links
            if request.extract_links:
                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll("a[href]"))
                        .map(a => a.href)
                        .filter(h => h.startsWith("http"));
                }''')
                response.links = list(dict.fromkeys(links))[:100]

            await browser.close()
            return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Playwright Scraper API"}


@app.post("/website-data")
async def get_website_data(request: ScrapeRequest):
    """
    Get comprehensive data and metadata about a website.
    
    Returns:
    - Title, description, meta tags
    - Open Graph data (for social media)
    - Headings structure (h1, h2, h3, etc.)
    - All images and links
    - Text content and word count
    - Favicon URL
    - And more...
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # Navigate to the URL
            await page.goto(
                request.url, 
                wait_until="networkidle",
                timeout=request.timeout * 1000
            )

            # Wait for specific element if requested
            if request.wait_for_selector:
                try:
                    await page.wait_for_selector(request.wait_for_selector, timeout=10000)
                except:
                    pass

            # Extract basic metadata
            title = await page.title()
            
            # Extract meta tags and Open Graph data
            description = await page.evaluate('''() => {
                const meta = document.querySelector('meta[name="description"]');
                return meta ? meta.getAttribute('content') : '';
            }''')
            
            og_title = await page.evaluate('''() => {
                const meta = document.querySelector('meta[property="og:title"]');
                return meta ? meta.getAttribute('content') : '';
            }''')
            
            og_description = await page.evaluate('''() => {
                const meta = document.querySelector('meta[property="og:description"]');
                return meta ? meta.getAttribute('content') : '';
            }''')
            
            og_image = await page.evaluate('''() => {
                const meta = document.querySelector('meta[property="og:image"]');
                return meta ? meta.getAttribute('content') : '';
            }''')
            
            og_type = await page.evaluate('''() => {
                const meta = document.querySelector('meta[property="og:type"]');
                return meta ? meta.getAttribute('content') : '';
            }''')
            
            og_url = await page.evaluate('''() => {
                const meta = document.querySelector('meta[property="og:url"]');
                return meta ? meta.getAttribute('content') : '';
            }''')
            
            language = await page.evaluate('''() => {
                const html = document.documentElement;
                return html.getAttribute('lang') || '';
            }''')
            
            canonical_url = await page.evaluate('''() => {
                const link = document.querySelector('link[rel="canonical"]');
                return link ? link.getAttribute('href') : '';
            }''')
            
            favicon_url = await page.evaluate('''() => {
                const link = document.querySelector('link[rel="icon"]') || document.querySelector('link[rel="shortcut icon"]');
                return link ? link.getAttribute('href') : '/favicon.ico';
            }''')
            
            # Extract headings
            headings_data = await page.evaluate('''() => {
                const headings = {h1: [], h2: [], h3: [], h4: [], h5: [], h6: []};
                ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].forEach(tag => {
                    document.querySelectorAll(tag).forEach(h => {
                        if (h.innerText.trim()) {
                            headings[tag].push(h.innerText.trim());
                        }
                    });
                });
                return headings;
            }''')
            
            # Extract images
            images = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('img'))
                    .map(img => img.src)
                    .filter(src => src && src.startsWith('http'))
                    .slice(0, 50);
            }''')
            
            # Extract links with text
            links_data = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a[href]'))
                    .map(a => ({
                        url: a.href,
                        text: a.innerText.trim() || a.textContent.trim() || 'Link'
                    }))
                    .filter(l => l.url.startsWith('http'))
                    .slice(0, 100);
            }''')
            
            # Remove duplicates from links
            unique_links = []
            seen_urls = set()
            for link in links_data:
                if link['url'] not in seen_urls:
                    unique_links.append(link)
                    seen_urls.add(link['url'])
            
            # Extract text content
            text_content = await page.locator("body").inner_text()
            word_count = len(text_content.split()) if text_content else 0
            
            response = WebsiteDataResponse(
                success=True,
                url=request.url,
                title=title,
                description=description,
                language=language if language else None,
                canonical_url=canonical_url if canonical_url else None,
                og_title=og_title if og_title else None,
                og_description=og_description if og_description else None,
                og_image=og_image if og_image else None,
                og_type=og_type if og_type else None,
                og_url=og_url if og_url else None,
                favicon_url=favicon_url,
                headings=headings_data,
                images=list(dict.fromkeys(images)),  # Remove duplicates
                links=unique_links,
                text_content=text_content[:1000],  # First 1000 chars
                word_count=word_count
            )

            await browser.close()
            return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract website data: {str(e)}")


@app.get("/")
async def root():
    """Welcome endpoint"""
    return {
        "message": "Welcome to Playwright Scraper API",
        "docs": "/docs",
        "endpoints": {
            "website_data": "/website-data (POST) - Get comprehensive data about a website",
            "scrape": "/scrape (POST) - Scrape and extract custom data",
            "health": "/health (GET) - Health check"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
