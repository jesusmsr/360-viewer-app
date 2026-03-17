"""
Servicio de gestión de invitaciones.
"""
import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.config import Config
from app.models.invite import Invite


class InviteService:
    """Servicio para gestionar invitaciones."""
    
    @classmethod
    def _get_invites_file(cls) -> str:
        """Obtener ruta del archivo de invitaciones."""
        return Config.PEERS_FILE.replace('.json', '.invitations.json')
    
    @classmethod
    def list_invites(cls) -> List[Invite]:
        """Listar todas las invitaciones."""
        invites = []
        file_path = cls._get_invites_file()
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    for invite_data in data:
                        invites.append(Invite.from_dict(invite_data))
            except (json.JSONDecodeError, KeyError):
                pass
        
        return invites
    
    @classmethod
    def get_invite(cls, code: str) -> Optional[Invite]:
        """Obtener una invitación por código."""
        invites = cls.list_invites()
        for invite in invites:
            if invite.code == code:
                return invite
        return None
    
    @classmethod
    def create_invite(cls, name: str = 'Invitado') -> Invite:
        """Crear una nueva invitación."""
        invite = Invite.generate(name)
        invites = cls.list_invites()
        invites.append(invite)
        cls._save_invites(invites)
        return invite
    
    @classmethod
    def use_invite(cls, code: str, peer_name: str) -> Optional[Invite]:
        """Marcar una invitación como usada."""
        invites = cls.list_invites()
        
        for invite in invites:
            if invite.code == code:
                if not invite.can_use():
                    return None
                
                invite.mark_used(peer_name)
                cls._save_invites(invites)
                return invite
        
        return None
    
    @classmethod
    def delete_invite(cls, code: str) -> bool:
        """Eliminar una invitación."""
        invites = cls.list_invites()
        original_count = len(invites)
        invites = [i for i in invites if i.code != code]
        
        if len(invites) < original_count:
            cls._save_invites(invites)
            return True
        return False
    
    @classmethod
    def cleanup_expired(cls) -> int:
        """Eliminar invitaciones expiradas. Retorna cantidad eliminada."""
        invites = cls.list_invites()
        original_count = len(invites)
        invites = [i for i in invites if not i.is_expired()]
        
        removed = original_count - len(invites)
        if removed > 0:
            cls._save_invites(invites)
        
        return removed
    
    @classmethod
    def _save_invites(cls, invites: List[Invite]):
        """Guardar invitaciones a archivo."""
        os.makedirs(os.path.dirname(Config.PEERS_FILE), exist_ok=True)
        data = [invite.to_dict() for invite in invites]
        
        with open(cls._get_invites_file(), 'w') as f:
            json.dump(data, f, indent=2)
