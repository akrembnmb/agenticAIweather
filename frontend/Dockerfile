FROM python:3.12-slim

LABEL maintainer="Akrem Benmbarek"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8050

CMD ["python", "app/app.py"]