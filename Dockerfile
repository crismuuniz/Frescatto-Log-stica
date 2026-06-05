FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install flask gunicorn pandas
# Instala as bibliotecas listadas no requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:3000"]