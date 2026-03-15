#!/bin/bash
# Script de despliegue para TrueNAS Scale
# Uso: ./deploy-truenas.sh /mnt/pool/videos-360 [puerto]

VIDEO_PATH=${1:-"/mnt/tu-pool/videos-360"}
PORT=${2:-"8080"}
DATA_PATH=${3:-"/mnt/tu-pool/app-data/360-viewer"}

echo "🎥 360° Video Viewer - Despliegue"
echo "================================="
echo "📁 Videos: $VIDEO_PATH"
echo "💾 Datos: $DATA_PATH"
echo "🌐 Puerto: $PORT"
echo ""

# Verificar que existen los directorios
if [ ! -d "$VIDEO_PATH" ]; then
    echo "❌ Error: El directorio de videos no existe: $VIDEO_PATH"
    echo "Uso: $0 /mnt/pool/videos-360 [puerto] [/mnt/pool/app-data]"
    exit 1
fi

# Crear directorio de datos si no existe
mkdir -p "$DATA_PATH"

# Detener contenedor existente si existe
docker stop 360-viewer 2>/dev/null
docker rm 360-viewer 2>/dev/null

# Construir imagen
echo "🔨 Construyendo imagen Docker..."
docker build -t 360-viewer:latest .

# Ejecutar
echo "🚀 Iniciando contenedor..."
docker run -d \
    --name 360-viewer \
    --restart unless-stopped \
    -p "$PORT:8080" \
    -v "$VIDEO_PATH:/videos:ro" \
    -v "$DATA_PATH:/app/data" \
    -e VIDEOS_PATH=/videos \
    -e LIBRARIES_FILE=/app/data/.libraries.json \
    360-viewer:latest

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ ¡Listo!"
    echo "🌐 Accede en: http://$(hostname -I | awk '{print $1}'):$PORT"
    echo "📊 Logs: docker logs -f 360-viewer"
    echo ""
    echo "💡 Primeros pasos:"
    echo "   1. Abre la URL en tu navegador"
    echo "   2. Haz clic en 'Añadir biblioteca'"
    echo "   3. Explora tus videos 360°"
else
    echo ""
    echo "❌ Error en el despliegue"
    exit 1
fi
