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

# Copiar backend completo (estructura modular)
COPY backend/ ./

# Copiar frontend estático (build de React)
COPY --from=frontend-builder /app/frontend/dist ./static

# Crear carpetas necesarias
RUN mkdir -p /videos /app/data && chmod 777 /app/data

# Puerto expuesto
EXPOSE 8080 8081

# Variables de entorno
ENV VIDEOS_DIR=/videos
ENV PEERS_FILE=/app/data/.peers.json
ENV DATA_DIR=/app/data

# Puerto interno configurable (default 8080)
ENV PORT=8080
ENV FEDERATION_PORT=8081
CMD ["python3", "server.py"]
