"""
Servicio de gestión de invitaciones.
Las invites son de un solo uso y NO persistentes (solo en memoria).
"""
import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.config import Config
from app.models.invite import Invite


class InviteService:
    """Servicio para gestionar invitaciones de un solo uso."""
    
    # Almacenamiento en memoria (no persistente)
    _active_invites: Dict[str, Invite] = {}
    _used_invites: set = set()  # Códigos ya usados (para prevenir reutilización)
    
    @classmethod
    def create_invite(cls, name: str = 'Invitado') -> Invite:
        """Crear una nueva invitación (solo en memoria, no persistente)."""
        invite = Invite.generate(name)
        cls._active_invites[invite.code] = invite
        return invite
    
    @classmethod
    def get_invite(cls, code: str) -> Optional[Invite]:
        """Obtener una invitación por código."""
        # Normalizar código
        code = code.upper().replace(' ', '-').replace('_', '-')
        
        # Verificar si ya fue usada
        if code in cls._used_invites:
            return None
        
        invite = cls._active_invites.get(code)
        
        # Verificar expiración
        if invite and invite.is_expired():
            del cls._active_invites[code]
            return None
        
        return invite
    
    @classmethod
    def use_invite(cls, code: str, peer_name: str) -> Optional[Invite]:
        """Marcar una invitación como usada y eliminarla."""
        code = code.upper().replace(' ', '-').replace('_', '-')
        
        invite = cls._active_invites.get(code)
        
        if not invite:
            return None
        
        if not invite.can_use():
            del cls._active_invites[code]
            return None
        
        # Marcar como usada
        invite.mark_used(peer_name)
        
        # Mover a usadas y eliminar de activas
        cls._used_invites.add(code)
        del cls._active_invites[code]
        
        return invite
    
    @classmethod
    def list_active_invites(cls) -> List[Invite]:
        """Listar solo invites activas (no usadas, no expiradas)."""
        now = datetime.now()
        active = []
        expired_codes = []
        
        for code, invite in cls._active_invites.items():
            if invite.used or invite.is_expired():
                expired_codes.append(code)
            else:
                active.append(invite)
        
        # Limpiar expiradas
        for code in expired_codes:
            del cls._active_invites[code]
        
        return active
    
    @classmethod
    def delete_invite(cls, code: str) -> bool:
        """Eliminar una invitación activa."""
        code = code.upper().replace(' ', '-').replace('_', '-')
        if code in cls._active_invites:
            del cls._active_invites[code]
            return True
        return False
