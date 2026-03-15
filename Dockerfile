FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias
RUN pip install --no-cache-dir flask

# Copiar archivos de la aplicación
COPY app/ ./

# Crear directorio para videos (se montará como volumen)
RUN mkdir -p /videos

# Puerto expuesto
EXPOSE 8080

# Variables de entorno
ENV VIDEOS_PATH=/videos
ENV LIBRARIES_FILE=/app/.libraries.json

# Comando de inicio
CMD ["python3", "server.py", "--host", "0.0.0.0", "--port", "8080"]
