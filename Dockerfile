FROM python:3.9-slim

WORKDIR /app

# Instalar dependências de sistema (opcional, mas recomendado para OCR)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1-mesa-glx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar antes de copiar o resto do código
# Isso garante que o pip rode com sucesso
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o resto da aplicação
COPY . .

# Comando de inicialização
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:3000"]