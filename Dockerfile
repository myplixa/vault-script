FROM python:3.11-slim

RUN pip install --no-cache-dir requests

WORKDIR /app
COPY . /app

CMD ["python", "main.py"]