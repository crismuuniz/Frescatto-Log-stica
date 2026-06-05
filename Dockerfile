# Usamos a imagem oficial que já contém Tesseract e Python
FROM jitesoft/tesseract-ocr:latest

# Instalar Python (já que a imagem base é só Tesseract)
RUN apt-get update && apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependências Python
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

# Usar gunicorn para rodar
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:3000"]