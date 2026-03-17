"""
Modelo de datos para peers.
"""
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class Peer:
    """Representa un peer conectado."""
    
    id: str
    name: str
    url: str
    token: Optional[str] = None
    status: str = 'offline'
    last_seen: Optional[str] = None
    added_at: Optional[str] = None
    
    def __post_init__(self):
        if not self.added_at:
            self.added_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Peer':
        """Crear desde diccionario."""
        return cls(**data)
    
    def get_origin(self) -> str:
        """Extraer el origin (scheme + host + port) de la URL."""
        from urllib.parse import urlparse
        parsed = urlparse(self.url)
        return f"{parsed.scheme}://{parsed.netloc}"
