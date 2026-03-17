# 360° Video Viewer - Todo en uno
# Backend Flask + Frontend React en un solo contenedor

# ==================== STAGE 1: Build Frontend ====================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copiar package.json e instalar dependencias
COPY frontend/package.json ./
RUN npm install

# Copiar código fuente y construir
COPY frontend/ ./
RUN npm run build

# ==================== STAGE 2: Python Backend con Frontend ====================
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias Python
RUN pip install --no-cache-dir flask flask-cors requests PyJWT

# Copiar backend
COPY backend/server.py ./

# Copiar frontend estático (build de React)
COPY --from=frontend-builder /app/frontend/dist ./static

# Crear carpetas necesarias
RUN mkdir -p /videos /app/data

# Puerto expuesto
EXPOSE 8080 8081

# Variables de entorno
ENV VIDEOS_PATH=/videos
ENV LIBRARIES_FILE=/app/data/.libraries.json
ENV FLASK_CORS=true
ENV STATIC_FOLDER=/app/static

# Puerto interno configurable (default 8080)
ENV PORT=8080
ENV FEDERATION_PORT=8081
CMD ["sh", "-c", "python3 server.py"]
