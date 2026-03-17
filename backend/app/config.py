"""
Configuración centralizada de la aplicación.
"""
import os
from pathlib import Path


class Config:
    """Configuración de la aplicación."""
    
    # Directorios
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = Path(os.environ.get('DATA_DIR', '/app/data'))
    VIDEOS_DIR = os.environ.get('VIDEOS_DIR', '/videos')
    
    # Archivos
    PEERS_FILE = os.environ.get('PEERS_FILE', str(DATA_DIR / '.peers.json'))
    
    # Puertos
    WEB_PORT = int(os.environ.get('PORT', 8080))
    FEDERATION_PORT = int(os.environ.get('FEDERATION_PORT', 8081))
    
    # JWT
    JWT_SECRET = os.environ.get('JWT_SECRET', 'tu_clave_secreta_aqui_cambia_esto_en_produccion')
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRY_DAYS = 30
    VIDEO_TOKEN_EXPIRY = 3600  # 1 hora
    
    # Rate Limiting
    RATE_LIMIT_WINDOW = 60  # segundos
    RATE_LIMIT_MAX_INVITE = 5  # intentos por minuto
    RATE_LIMIT_MAX_REQUESTS = 100  # req por minuto
    
    # Seguridad
    ALLOWED_ORIGINS_BASE = [
        'http://localhost:8080',
        'http://localhost:3000',
        'https://360.jsanr.dev'
    ]
    
    # Videos
    VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
    MAX_VIDEO_SIZE_GB = 10
