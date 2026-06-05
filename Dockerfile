# Usamos uma imagem que já tem muitas dependências pré-instaladas
FROM nikolaik/python-nodejs:python3.9-nodejs18

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Comando para rodar
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:3000"]