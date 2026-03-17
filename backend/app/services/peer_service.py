"""
Servicio de gestión de peers.
"""
import json
import os
import secrets
import threading
from typing import Dict, List, Optional
from pathlib import Path

from app.config import Config
from app.models.peer import Peer


class PeerService:
    """Servicio para gestionar peers."""
    
    _cache: Dict[str, Peer] = {}
    _lock = threading.Lock()
    
    @classmethod
    def _load_from_file(cls) -> Dict[str, Peer]:
        """Cargar peers desde archivo."""
        peers = {}
        if os.path.exists(Config.PEERS_FILE):
            try:
                with open(Config.PEERS_FILE, 'r') as f:
                    data = json.load(f)
                    for peer_id, peer_data in data.items():
                        peers[peer_id] = Peer.from_dict(peer_data)
            except (json.JSONDecodeError, KeyError):
                peers = {}
        return peers
    
    @classmethod
    def _save_to_file(cls, peers: Dict[str, Peer]):
        """Guardar peers a archivo."""
        os.makedirs(os.path.dirname(Config.PEERS_FILE), exist_ok=True)
        data = {pid: peer.to_dict() for pid, peer in peers.items()}
        with open(Config.PEERS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def list_peers(cls) -> List[Peer]:
        """Listar todos los peers."""
        with cls._lock:
            cls._cache = cls._load_from_file()
            return list(cls._cache.values())
    
    @classmethod
    def get_peer(cls, peer_id: str) -> Optional[Peer]:
        """Obtener un peer por ID."""
        with cls._lock:
            cls._cache = cls._load_from_file()
            return cls._cache.get(peer_id)
    
    @classmethod
    def add_peer(cls, peer: Peer) -> Peer:
        """Añadir un nuevo peer."""
        with cls._lock:
            peers = cls._load_from_file()
            peers[peer.id] = peer
            cls._save_to_file(peers)
            cls._cache = peers
            return peer
    
    @classmethod
    def update_peer(cls, peer_id: str, **updates) -> Optional[Peer]:
        """Actualizar un peer existente."""
        with cls._lock:
            peers = cls._load_from_file()
            if peer_id not in peers:
                return None
            
            peer = peers[peer_id]
            for key, value in updates.items():
                if hasattr(peer, key):
                    setattr(peer, key, value)
            
            cls._save_to_file(peers)
            cls._cache = peers
            return peer
    
    @classmethod
    def delete_peer(cls, peer_id: str) -> bool:
        """Eliminar un peer."""
        with cls._lock:
            peers = cls._load_from_file()
            if peer_id not in peers:
                return False
            
            del peers[peer_id]
            cls._save_to_file(peers)
            cls._cache = peers
            return True
    
    @classmethod
    def generate_id(cls) -> str:
        """Generar un ID único para peer."""
        return 'peer_' + secrets.token_hex(8)
