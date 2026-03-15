FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir flask flask-cors

COPY server.py ./

RUN mkdir -p /videos /app/data

EXPOSE 8080

ENV VIDEOS_PATH=/videos
ENV LIBRARIES_FILE=/app/data/.libraries.json
ENV FLASK_CORS=true

CMD ["python3", "server.py", "--host", "0.0.0.0", "--port", "8080"]
