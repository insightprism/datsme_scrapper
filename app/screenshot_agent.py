from playwright.async_api import async_playwright

class ScreenshotAgent:
    async def capture(self, url: str, max_pages: int = 1) -> bytes:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url, timeout=30000, wait_until="networkidle")

            viewport_height = await page.evaluate("() => window.innerHeight")
            capture_height = viewport_height * max_pages

            await page.set_viewport_size({"width": 1280, "height": capture_height})
            screenshot_bytes = await page.screenshot(full_page=False)
            await browser.close()

        return screenshot_bytes
