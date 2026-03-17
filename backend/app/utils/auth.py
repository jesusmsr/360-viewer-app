"""
Utilidades de autenticación JWT.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
import jwt

from app.config import Config


def generate_jwt(peer_id: str, peer_name: str, permissions: list = None) -> str:
    """Generar token JWT de acceso para un peer."""
    return jwt.encode({
        'peer_id': peer_id,
        'peer_name': peer_name,
        'permissions': permissions or ['read_catalog'],
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(days=Config.JWT_EXPIRY_DAYS),
        'type': 'peer_access'
    }, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)


def verify_jwt(token: str) -> Union[Dict[str, Any], Dict[str, str]]:
    """Verificar token JWT y retornar payload o error."""
    try:
        return jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return {'error': 'Token expirado'}
    except jwt.InvalidTokenError:
        return {'error': 'Token inválido'}


def generate_video_token(video_path: str, peer_id: str) -> str:
    """Generar token JWT para acceso a un video específico."""
    return jwt.encode({
        'video_path': video_path,
        'peer_id': peer_id,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(seconds=Config.VIDEO_TOKEN_EXPIRY),
        'type': 'video_access'
    }, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)


def verify_video_token(token: str) -> Union[Dict[str, Any], Dict[str, str]]:
    """Verificar token de video."""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
        if payload.get('type') != 'video_access':
            return {'error': 'Tipo de token incorrecto'}
        return payload
    except jwt.ExpiredSignatureError:
        return {'error': 'Token de video expirado'}
    except jwt.InvalidTokenError:
        return {'error': 'Token de video inválido'}


def require_auth_header(request) -> Optional[Dict]:
    """Extraer y validar token de header X-Peer-Token."""
    token = request.headers.get('X-Peer-Token')
    if not token:
        return None
    
    payload = verify_jwt(token)
    if 'error' in payload:
        return None
    
    return payload
