# Playwright Web Scraper API

A FastAPI-based web scraping service using Playwright for dynamic website content extraction.

## Features

- ✅ Real browser automation with Playwright (Chromium)
- ✅ Extract full page HTML
- ✅ Extract visible text content
- ✅ Extract links from pages
- ✅ Custom CSS selector targeting
- ✅ Wait for dynamic content to load
- ✅ CORS enabled for frontend integration
- ✅ Interactive API documentation (Swagger UI)

## Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

## Running the Server

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`
API Documentation: `http://localhost:8000/docs`

## API Endpoints

### POST /scrape

Main scraping endpoint. Returns extracted webpage data.

**Request Body:**

```json
{
  "url": "https://example.com",
  "timeout": 30,
  "wait_for_selector": null,
  "extract_full_text": true,
  "extract_links": false,
  "custom_selectors": {
    "title": "h1",
    "price": ".product-price"
  }
}
```

**Response:**

```json
{
  "success": true,
  "url": "https://example.com",
  "title": "Example Domain",
  "html": "...",
  "full_text": "...",
  "data": {
    "title": "Example Domain"
  },
  "links": ["https://www.iana.org/domains/example"],
  "error": null
}
```

### GET /health

Health check endpoint.

### GET /

Welcome/info endpoint.

## Usage Examples

### Example 1: Simple Text Extraction

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "extract_full_text": true
  }'
```

### Example 2: Extract Specific Elements

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://news.ycombinator.com",
    "custom_selectors": {
      "top_story": ".titleline > a",
      "score": ".score"
    },
    "extract_links": true
  }'
```

### Example 3: Wait for Dynamic Content

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "wait_for_selector": ".dynamic-content",
    "extract_full_text": true
  }'
```

## Python Client Example

```python
import requests

url = "http://localhost:8000/scrape"

payload = {
    "url": "https://example.com",
    "extract_full_text": True,
    "custom_selectors": {
        "heading": "h1",
        "paragraph": "p"
    }
}

response = requests.post(url, json=payload)
data = response.json()

print(f"Title: {data['title']}")
print(f"Text: {data['full_text'][:200]}")
print(f"Extracted: {data['data']}")
```

## Parameter Reference

| Parameter           | Type   | Default  | Description                                   |
| ------------------- | ------ | -------- | --------------------------------------------- |
| `url`               | string | required | Website URL to scrape                         |
| `timeout`           | int    | 30       | Request timeout in seconds                    |
| `wait_for_selector` | string | null     | CSS selector to wait for before scraping      |
| `extract_full_text` | bool   | true     | Extract all visible text from page            |
| `extract_links`     | bool   | false    | Extract all links from the page               |
| `custom_selectors`  | object | {}       | Custom CSS selectors to extract specific data |

## Notes

- The API uses headless Chromium for automation
- Requests have a default 30-second timeout
- Up to 100 links are extracted per page
- Custom selectors return first matching element only
- CORS is enabled for all origins (change in production)

## Performance Tips

1. Set `extract_full_text` to `false` if you don't need it
2. Use specific `custom_selectors` instead of extracting full HTML
3. Set appropriate `timeout` values based on target sites
4. Use `wait_for_selector` only when necessary

## Production Considerations

- Add authentication/API keys
- Implement rate limiting
- Add request logging
- Use browser pooling for concurrent requests
- Run behind a reverse proxy (nginx)
- Consider containerization (Docker)

## Troubleshooting

**"Playwright chromium not found"**

```bash
playwright install chromium
```

**Timeout errors**

- Increase the `timeout` parameter
- Check if the target website is blocking automation
- Use a proxy or rotate user agents

**Elements not found**

- Use browser DevTools to find correct selectors
- Check if content loads dynamically (may need `wait_for_selector`)
