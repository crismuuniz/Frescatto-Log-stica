# Usar a versão completa do Python 3.9 para evitar pacotes do sistema em falta
FROM python:3.9-buster

ENV DEBIAN_FRONTEND=noninteractive

# Atualização forçada e instalação de dependências essenciais
# O uso de 'buster' (versão estável do Debian) costuma ser muito mais robusto no Render
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

# Usar Gunicorn como servidor
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:3000"]