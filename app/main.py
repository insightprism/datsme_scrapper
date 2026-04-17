from fastapi import FastAPI, Query, UploadFile, File, Request
from fastapi.responses import JSONResponse
from typing import Optional, List
import traceback
import logging
import base64

from app.scraper_agent import WebScraperAgent
from app.ocr_agent import OCRAgent
from app.screenshot_agent import ScreenshotAgent
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="web_scraping_agent", version="3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://react.insightprism.com",
        "https://streamlit.insightprism.com",
        "http://localhost:5173"  # for local React dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("web_scraper_agent")
agent = WebScraperAgent()
ocr_agent = OCRAgent()
screenshot_agent = ScreenshotAgent()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/scrape_text")
async def scrape_text(url: str, title: Optional[str] = None, snippet: Optional[str] = None):
    try:
        result = await agent.scrape_text(url, headless=True, snippet=snippet)
        if title: result["title"] = title
        return result
    except Exception as e:
        if "ERR_HTTP2_PROTOCOL_ERROR" in str(e) or "content too short" in str(e):
            try:
                result = await agent.scrape_text(url, headless=False, force_http1=True, snippet=snippet)
                if title: result["title"] = title
                return result
            except Exception as retry_error:
                traceback.print_exc()
                return JSONResponse(status_code=500, content={"error": str(retry_error)})
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/scrape_html")
async def scrape_html(url: str, title: Optional[str] = None, snippet: Optional[str] = None):
    try:
        result = await agent.scrape_html(url, headless=True)
        if title: result["title"] = title
        if snippet: result["snippet"] = snippet
        return result
    except Exception as e:
        if "ERR_HTTP2_PROTOCOL_ERROR" in str(e) or "content too short" in str(e):
            try:
                result = await agent.scrape_html(url, headless=False, force_http1=True)
                if title: result["title"] = title
                if snippet: result["snippet"] = snippet
                return result
            except Exception as retry_error:
                traceback.print_exc()
                return JSONResponse(status_code=500, content={"error": str(retry_error)})
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/scrape_pdf")
async def scrape_pdf(url: str, title: Optional[str] = None, snippet: Optional[str] = None):
    try:
        result = await agent.scrape_pdf(url, headless=True)
        if title: result["title"] = title
        if snippet: result["snippet"] = snippet
        return result
    except Exception as e:
        if "ERR_HTTP2_PROTOCOL_ERROR" in str(e) or "content too short" in str(e):
            try:
                result = await agent.scrape_pdf(url, headless=False, force_http1=True)
                if title: result["title"] = title
                if snippet: result["snippet"] = snippet
                return result
            except Exception as retry_error:
                traceback.print_exc()
                return JSONResponse(status_code=500, content={"error": str(retry_error)})
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/scrape_crawl")
async def scrape_crawl(url: str, keywords: Optional[List[str]] = Query(default=["about", "leadership", "team"]), depth: int = Query(default=2, ge=1, le=5)):
    try:
        return await agent.scrape_crawl(url, keywords=keywords, depth=depth)
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.api_route("/ocr_image", methods=["GET", "POST"])
async def ocr_image(request: Request, file: UploadFile = File(None), url: str = None):
    try:
        if request.method == "POST" and file:
            content = await file.read()
            return ocr_agent.image_to_text(content)
        elif request.method == "GET" and url:
            content = ocr_agent.fetch_url_bytes(url)
            return ocr_agent.image_to_text(content)
        return JSONResponse(status_code=400, content={"error": "Missing image file or URL."})
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.api_route("/ocr_pdf", methods=["GET", "POST"])
async def ocr_pdf(request: Request, file: UploadFile = File(None), url: str = None):
    try:
        if request.method == "POST" and file:
            content = await file.read()
            return ocr_agent.pdf_to_text(content)
        elif request.method == "GET" and url:
            content = ocr_agent.fetch_url_bytes(url)
            return ocr_agent.pdf_to_text(content)
        return JSONResponse(status_code=400, content={"error": "Missing PDF file or URL."})
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.api_route("/ocr_read", methods=["GET", "POST"])
async def ocr_read(request: Request, url: str = None, file: UploadFile = File(None)):
    try:
        if request.method == "POST" and file:
            contents = await file.read()
            if file.filename.lower().endswith(".pdf"):
                return ocr_agent.read_file(contents, file_type="pdf")
            else:
                return ocr_agent.read_file(contents, file_type="image")
        elif request.method == "GET" and url:
            return await ocr_agent.read_url(url)
        return JSONResponse(status_code=400, content={"error": "Provide a file or a URL"})
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/screenshot")
async def screenshot(url: str, max_pages: int = 1):
    try:
        image_bytes = await screenshot_agent.capture(url, max_pages)
        return {
            "screenshot_base64": base64.b64encode(image_bytes).decode("utf-8")
        }
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/ocr_screenshot")
async def ocr_screenshot(url: str, max_pages: int = 1):
    try:
        return await ocr_agent.screenshot_url_to_text(url, max_pages=max_pages)
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
