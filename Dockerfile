FROM python:3.9-slim

# Definir variáveis de ambiente para evitar interrupções
ENV DEBIAN_FRONTEND=noninteractive

# Atualização mais robusta
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Comando para rodar
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:3000"]