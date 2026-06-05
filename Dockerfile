FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install flask gunicorn pandas
COPY . .
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:3000"]