# app/scraper_agent.py

import base64
import logging
from playwright.async_api import async_playwright
from app.utils import sanitize_url, navigate_with_retry, filter_links, extract_domain, launch_browser_safe

logger = logging.getLogger("web_scraper_agent")

class WebScraperAgent:
    def __init__(self, wait_time_ms=4000, default_user_agent=None):
        self.wait_time_ms = wait_time_ms
        self.default_user_agent = default_user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )

    async def scrape_text(self, url: str, title: str = "", snippet: str = "", headless: bool = True, force_http1: bool = False):
        url = sanitize_url(url)
        logger.info(f"[Text] Scraping text from {url} | Headless={headless}")
        args = ["--disable-http2"] if force_http1 else []

        async with async_playwright() as p:
            try:
                browser = await launch_browser_safe(p.chromium, headless=headless, args=args)
            except Exception as e:
                logger.warning(f"[Retry] Headless mode failed for {url}. Retrying with full browser and forced HTTP/1.1...")
                args = [
                    "--disable-http2",
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-background-timer-throttling",
                    "--disable-renderer-backgrounding"
                ]
                browser = await launch_browser_safe(p.chromium, headless=False, args=args)

            context = await browser.new_context(user_agent=self.default_user_agent)
            page = await context.new_page()

            try:
                await navigate_with_retry(page, url)
                await page.wait_for_timeout(self.wait_time_ms)
                text = await page.evaluate("() => document.body.innerText")
                page_title = await page.title()

                if not text or len(text.strip()) < 50:
                    raise Exception("\U0001f6d1 Page may not have fully loaded or is too short.")

                return {
                    "url": url,
                    "title": title or page_title,
                    "snippet": snippet,
                    "scrape_content": text
                }

            finally:
                await browser.close()

    async def scrape_html(self, url: str, title: str = "", snippet: str = "", headless: bool = True, force_http1: bool = False):
        url = sanitize_url(url)
        logger.info(f"[HTML] Scraping raw HTML from {url} | Headless={headless}")
        args = ["--disable-http2"] if force_http1 else []

        async with async_playwright() as p:
            browser = await launch_browser_safe(p.chromium, headless=headless, args=args)
            context = await browser.new_context(user_agent=self.default_user_agent)
            page = await context.new_page()
            try:
                await navigate_with_retry(page, url)
                await page.wait_for_timeout(self.wait_time_ms)
                html = await page.content()
                page_title = await page.title()
                if not html or len(html.strip()) < 100:
                    raise Exception("\U0001f6d1 HTML content too short.")
                return {
                    "url": url,
                    "title": title or page_title,
                    "snippet": snippet,
                    "scrape_html": html
                }
            finally:
                await browser.close()

    async def scrape_pdf(self, url: str, title: str = "", snippet: str = "", headless: bool = True, force_http1: bool = False):
        url = sanitize_url(url)
        logger.info(f"[PDF] Scraping PDF from {url} | Headless={headless}")
        args = ["--disable-http2"] if force_http1 else []

        async with async_playwright() as p:
            browser = await launch_browser_safe(p.chromium, headless=headless, args=args)
            context = await browser.new_context(user_agent=self.default_user_agent)
            page = await context.new_page()
            try:
                await navigate_with_retry(page, url)
                await page.wait_for_timeout(self.wait_time_ms)
                body_text = await page.evaluate("() => document.body.innerText")
                page_title = await page.title()
                if not body_text or len(body_text.strip()) < 50:
                    raise Exception("\U0001f6d1 PDF content too short.")
                pdf_bytes = await page.pdf(format="A4", print_background=True)
                return {
                    "url": url,
                    "title": title or page_title,
                    "snippet": snippet,
                    "scrape_content": body_text,
                    "pdf_base64": base64.b64encode(pdf_bytes).decode("utf-8")
                }
            finally:
                await browser.close()

    async def scrape_crawl(self, url: str, keywords=None, depth=2):
        url = sanitize_url(url)
        keywords = keywords or ["about", "leadership", "team"]
        base_domain = extract_domain(url)

        logger.info(f"[Crawl] Starting crawl from {url} | Depth={depth}")
        pages_data = []
        used_urls = set()
        invalid_urls = []
        discovered_urls = set()

        queue = [(url, 0)]

        async with async_playwright() as p:
            browser = await launch_browser_safe(p.chromium, headless=True)
            context = await browser.new_context(user_agent=self.default_user_agent)

            while queue:
                target_url, current_depth = queue.pop(0)
                if target_url in used_urls or current_depth > depth:
                    continue

                logger.info(f"[Crawl] Visiting {target_url} | Depth={current_depth}")
                try:
                    page = await context.new_page()
                    await navigate_with_retry(page, target_url)
                    await page.wait_for_timeout(self.wait_time_ms)
                    text = await page.evaluate("() => document.body.innerText")
                    title = await page.title()

                    pages_data.append({
                        "url": target_url,
                        "depth": current_depth,
                        "title": title,
                        "text": text
                    })
                    used_urls.add(target_url)

                    if current_depth < depth:
                        raw_links = await page.evaluate("() => Array.from(document.querySelectorAll('a')).map(a => a.href)")
                        filtered = filter_links(raw_links, base_domain, keywords)
                        for link in filtered:
                            if link not in used_urls:
                                queue.append((link, current_depth + 1))
                                discovered_urls.add(link)

                    await page.close()

                except Exception as e:
                    logger.warning(f"[Crawl] Failed to visit {target_url}: {e}")
                    invalid_urls.append(target_url)

            await context.close()
            await browser.close()

        return {
            "request": {
                "url": url,
                "keywords": keywords,
                "depth": depth
            },
            "pages": pages_data,
            "used_urls": list(used_urls),
            "invalid_urls": invalid_urls,
            "discovered_urls": list(discovered_urls),
            "total_pages": len(pages_data),
            "status": "success"
        }
