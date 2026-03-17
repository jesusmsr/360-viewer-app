"""
Gestión de CORS dinámico.
"""
from typing import List, Set
from urllib.parse import urlparse

from app.config import Config
from app.services.peer_service import PeerService


class CORSManager:
    """Gestiona los orígenes permitidos dinámicamente."""
    
    def __init__(self):
        self._origins = set(Config.ALLOWED_ORIGINS_BASE)
    
    def get_allowed_origins(self) -> List[str]:
        """Obtener lista de orígenes permitidos."""
        origins = set(self._origins)
        
        # Añadir orígenes de peers registrados
        try:
            peers = PeerService.list_peers()
            for peer in peers:
                try:
                    parsed = urlparse(peer.url)
                    origin = f"{parsed.scheme}://{parsed.netloc}"
                    origins.add(origin)
                except:
                    pass
        except:
            pass
        
        return list(origins)
    
    def is_allowed(self, origin: str) -> bool:
        """Verificar si un origen está permitido."""
        if not origin or origin == '*':
            return True
        return origin in self.get_allowed_origins()
    
    def add_cors_headers(self, response, request_origin: str = None):
        """Añadir headers CORS si el origen está permitido."""
        if request_origin and self.is_allowed(request_origin):
            response.headers['Access-Control-Allow-Origin'] = request_origin
        
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Peer-Token, Authorization'
        return response
