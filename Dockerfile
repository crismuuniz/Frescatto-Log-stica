FROM python:3.9-slim

# Instalar Tesseract, OpenCV (headless) e bibliotecas de sistema necessárias
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:3000"]