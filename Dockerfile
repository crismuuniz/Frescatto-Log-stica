# Usando a versão slim que é mais leve
FROM python:3.9-slim

# Evitar prompts interativos durante o build
ENV DEBIAN_FRONTEND=noninteractive

# Atualizar lista de pacotes e instalar dependências essenciais
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-por \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar arquivos de requisitos primeiro para otimizar o cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o resto do código
COPY . .

EXPOSE 3000

CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:3000"]