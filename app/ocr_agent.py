from PIL import Image
import pytesseract
import io
import requests
import base64
from pdf2image import convert_from_bytes
from playwright.async_api import async_playwright
from app.screenshot_agent import ScreenshotAgent

class OCRAgent:
    def __init__(self):
        self.screenshot_agent = ScreenshotAgent()

    def image_to_text(self, image_bytes):
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
        return {"text": pytesseract.image_to_string(image, config='--dpi 300')}

    def image_to_data(self, image_bytes):
        image = Image.open(io.BytesIO(image_bytes))
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        words = [
            {
                "word": word,
                "conf": data["conf"][i],
                "bbox": [data["left"][i], data["top"][i], data["width"][i], data["height"][i]]
            }
            for i, word in enumerate(data["text"]) if word.strip()
        ]
        return {"text": " ".join(data["text"]), "words": words}

    def pdf_to_text(self, pdf_bytes):
        images = convert_from_bytes(pdf_bytes)
        texts = [pytesseract.image_to_string(img, config='--dpi 300') for img in images]
        return {"pages": texts}

    def fetch_url_bytes(self, url):
        return requests.get(url).content

    async def screenshot_url_to_text(self, url: str, max_pages: int = 1):
        screenshot_bytes = await self.screenshot_agent.capture(url, max_pages)
        image = Image.open(io.BytesIO(screenshot_bytes))
        image.load()
        text = pytesseract.image_to_string(image, config='--dpi 300')
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")
        return {
            "text": text,
            "screenshot_base64": screenshot_base64
        }

    def read_file(self, file_bytes: bytes, file_type: str = "image"):
        if file_type == "image":
            return self.image_to_text(file_bytes)
        elif file_type == "pdf":
            return self.pdf_to_text(file_bytes)
        else:
            raise ValueError("Unsupported file type")

    async def read_url(self, url: str, max_pages: int = 1):
        return await self.screenshot_url_to_text(url, max_pages=max_pages)
