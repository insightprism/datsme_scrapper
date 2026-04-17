# Use official Python base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory
WORKDIR /app

# Install system dependencies for Playwright + OCR + PDF/image tools + full X11 support
RUN apt-get update && apt-get install -y \
    wget curl gnupg ca-certificates \
    xvfb x11-utils xauth x11-apps \
    fonts-liberation libnss3 libxss1 libasound2 \
    libatk-bridge2.0-0 libgtk-3-0 libx11-xcb1 libxcomposite1 libxdamage1 \
    libxrandr2 libgbm1 libpango-1.0-0 libatk1.0-0 libcups2 \
    libdrm2 libxshmfence1 libnss3-tools libxtst6 \
    tesseract-ocr libtesseract-dev \
    ghostscript poppler-utils imagemagick \
    tesseract-ocr-eng tesseract-ocr-fra tesseract-ocr-deu tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install Python dependencies and Playwright with dependencies
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt \
 && python -m playwright install --with-deps

# Expose port
EXPOSE 8000

# NOTE: CMD is overridden by docker-compose for Xvfb support
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
