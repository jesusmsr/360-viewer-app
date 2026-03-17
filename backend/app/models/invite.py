"""
Modelo de datos para invitaciones.
"""
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import secrets


@dataclass
class Invite:
    """Representa una invitación para unirse a la federación."""
    
    code: str
    name: str
    created_at: str
    expires_at: str
    used: bool = False
    used_by: Optional[str] = None
    used_at: Optional[str] = None
    permissions: List[str] = field(default_factory=lambda: ['read_catalog'])
    
    @classmethod
    def generate(cls, name: str = 'Invitado', expiry_days: int = 7) -> 'Invite':
        """Generar una nueva invitación."""
        # 16 caracteres alfanuméricos
        chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        code = ''.join(secrets.choice(chars) for _ in range(16))
        
        created = datetime.now()
        expires = created + timedelta(days=expiry_days)
        
        return cls(
            code=code,
            name=name,
            created_at=created.isoformat(),
            expires_at=expires.isoformat(),
            permissions=['read_catalog']
        )
    
    def is_expired(self) -> bool:
        """Verificar si la invitación expiró."""
        return datetime.now() > datetime.fromisoformat(self.expires_at)
    
    def can_use(self) -> bool:
        """Verificar si se puede usar."""
        return not self.used and not self.is_expired()
    
    def mark_used(self, peer_name: str):
        """Marcar como usada."""
        self.used = True
        self.used_by = peer_name
        self.used_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Invite':
        """Crear desde diccionario."""
        return cls(**data)
