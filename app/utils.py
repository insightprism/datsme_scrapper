import logging
import shutil
from urllib.parse import urlparse
from typing import List

logger = logging.getLogger("web_scraper_agent2")


def sanitize_url(url: str) -> str:
    """Ensure the URL is trimmed and valid."""
    return url.strip()


def extract_domain(url: str) -> str:
    """Extract domain name from URL."""
    parsed = urlparse(url)
    return parsed.netloc


def filter_links(links: List[str], base_domain: str, keywords: List[str]) -> List[str]:
    """Filter internal links containing keywords."""
    filtered = []
    for link in links:
        if not link.startswith("http"):
            continue
        if base_domain not in link:
            continue
        if any(keyword.lower() in link.lower() for keyword in keywords):
            filtered.append(link)
    return list(set(filtered))


async def navigate_with_retry(page, url: str, timeout: int = 60000):
    """
    Try to navigate normally; if HTTP/2 errors, retry with full-head browser and HTTP/1.1.
    """
    try:
        await page.goto(url, timeout=timeout)
        return True
    except Exception as e:
        logger.warning(f"[Retry] Standard navigation failed for {url}: {str(e)}")
        raise e


# ✅ NEW: Smart browser launcher to support xvfb fallback
async def launch_browser_safe(browser_type, headless=True, args=None):
    """
    Launch browser safely in environments without X11 by using xvfb-run when needed.
    """
    args = args or []

    if headless:
        return await browser_type.launch(headless=True, args=args)

    if shutil.which("xvfb-run"):
        logger.info("[Launch] Using xvfb-run for full browser mode")
        return await browser_type.launch(headless=False, args=args)
    else:
        raise RuntimeError("Headless mode failed, and xvfb-run is not available.")
