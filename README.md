# DatsMe Scraper

A FastAPI microservice for fetching and extracting content from web pages. Uses Playwright (headless Chromium) for rendering JS-heavy pages, and Tesseract OCR as a visual fallback for sites that hide content from text scrapers.

Built as a reusable fetch layer for AI-driven content import. The service does the fetching; downstream callers (e.g. the DatsMe API) feed the extracted text to an LLM for restructuring into target schemas.

## Quick start

```bash
docker compose up -d --build
curl http://localhost:8000/health
```

First build downloads Chromium (~400 MB) and installs Tesseract — takes 10-15 minutes. Subsequent restarts are seconds.

## Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Health check — returns `{"status": "ok"}` |
| `GET /scrape_text?url=...` | Render page in Chromium, return clean text |
| `GET /scrape_html?url=...` | Same but returns raw HTML |
| `GET /scrape_pdf?url=...` | Render page, return text + generated PDF |
| `GET /scrape_crawl?url=...&keywords=about,team&depth=2` | Multi-page crawl, follows internal links matching keywords |
| `GET /screenshot?url=...&max_pages=1` | Returns base64 PNG screenshot |
| `GET /ocr_image` | OCR an image (POST file or GET URL) |
| `GET /ocr_pdf` | OCR a PDF (POST file or GET URL) |
| `GET /ocr_screenshot?url=...` | Screenshot a URL, then OCR the image |
| `GET /ocr_read` | Auto-route between image/PDF OCR |

## Example

```bash
curl "http://localhost:8000/scrape_text?url=https://en.wikipedia.org/wiki/Detroit"
```

Returns:
```json
{
  "url": "https://en.wikipedia.org/wiki/Detroit",
  "title": "Detroit - Wikipedia",
  "snippet": null,
  "scrape_content": "..."
}
```

## Architecture

- **`app/main.py`** — FastAPI HTTP layer. Each endpoint wraps an agent method with auto-retry on failure (headless → headed, HTTP/2 → HTTP/1.1).
- **`app/scraper_agent.py`** — Playwright-based scraping. Realistic Chrome User-Agent, anti-detection flags (`--disable-blink-features=AutomationControlled`).
- **`app/ocr_agent.py`** — Tesseract OCR for images/PDFs and screenshot fallback chain.
- **`app/screenshot_agent.py`** — Page screenshot capture via Playwright.
- **`app/utils.py`** — URL sanitization, link filtering, Xvfb-aware browser launcher.

## Deployment

The container binds to `127.0.0.1:8000` by default — only callers on the same host can reach it. To expose externally, change the port mapping in `docker-compose.yml` and add API key auth (not yet implemented).

System requirements:
- Docker
- ~2 GB disk for the image
- ~250 MB RAM idle, +200-300 MB per concurrent scrape

## Limitations

- Runs from the host's IP. Sites with strong IP-reputation blocking (LinkedIn, Facebook, Instagram) will return their login walls. For those, pair this service with paste-text or data-export upload patterns.
- One browser per request. Fine for low-volume use; would need a browser pool at high concurrency.
- No request authentication. Bind to localhost or add an API key layer before public exposure.
