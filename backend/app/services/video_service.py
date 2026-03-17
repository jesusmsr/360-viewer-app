"""
Servicio de gestión de videos.
"""
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from app.config import Config


class VideoService:
    """Servicio para gestionar videos."""
    
    @classmethod
    def get_base_path(cls) -> Path:
        """Obtener directorio base de videos."""
        return Path(Config.VIDEOS_DIR)
    
    @classmethod
    def validate_path(cls, relative_path: str) -> Tuple[bool, Path]:
        """
        Validar que una ruta relativa no escape del directorio base.
        
        Returns:
            (is_valid, full_path)
        """
        base_path = cls.get_base_path()
        full_path = base_path / relative_path
        
        try:
            full_path.relative_to(base_path)
            return True, full_path
        except ValueError:
            return False, full_path
    
    @classmethod
    def list_videos(cls, folder: str = '') -> List[Dict[str, Any]]:
        """Listar videos en una carpeta."""
        base_path = cls.get_base_path()
        target_path = base_path / folder
        
        try:
            target_path.relative_to(base_path)
        except ValueError:
            return []
        
        if not target_path.exists() or not target_path.is_dir():
            return []
        
        videos = []
        for item in target_path.rglob('*'):
            if item.is_file() and item.suffix.lower() in Config.VIDEO_EXTENSIONS:
                try:
                    rel_path = str(item.relative_to(base_path))
                    stat = item.stat()
                    videos.append({
                        'path': rel_path,
                        'name': item.name,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'size': stat.st_size
                    })
                except:
                    pass
        
        return sorted(videos, key=lambda x: x['modified'], reverse=True)
    
    @classmethod
    def browse_folder(cls, folder_path: str = '') -> Dict[str, Any]:
        """Navegar jerárquicamente por carpetas."""
        base_path = cls.get_base_path()
        target_path = base_path / folder_path
        
        # Validar path
        try:
            target_path.relative_to(base_path)
        except ValueError:
            return {'items': [], 'exists': False, 'error': 'Invalid path'}
        
        if not target_path.exists() or not target_path.is_dir():
            return {'items': [], 'exists': False, 'error': 'Not found'}
        
        items = []
        try:
            for item in sorted(target_path.iterdir()):
                rel_path = str(item.relative_to(base_path))
                
                if item.is_dir():
                    items.append({
                        'name': item.name,
                        'path': rel_path,
                        'type': 'folder'
                    })
                elif item.suffix.lower() in Config.VIDEO_EXTENSIONS:
                    stat = item.stat()
                    items.append({
                        'name': item.name,
                        'path': rel_path,
                        'type': 'video',
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'size': stat.st_size
                    })
        except PermissionError:
            return {'error': 'Permission denied', 'exists': False}
        
        return {
            'items': items,
            'current_path': folder_path,
            'exists': True
        }
    
    @classmethod
    def get_catalog(cls) -> Dict[str, Any]:
        """Obtener catálogo completo para compartir."""
        return {
            'videos': cls.list_videos(),
            'count': len(cls.list_videos()),
            'shared_at': datetime.now().isoformat()
        }
    
    @classmethod
    def get_video_info(cls, path: str) -> Optional[Dict[str, Any]]:
        """Obtener información de un video específico."""
        is_valid, full_path = cls.validate_path(path)
        
        if not is_valid or not full_path.exists():
            return None
        
        stat = full_path.stat()
        return {
            'path': path,
            'name': full_path.name,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
        }
    
    @classmethod
    def serve_video(cls, path: str, range_header: str = None) -> Tuple[Optional[bytes], int, int, int]:
        """
        Servir video con soporte para Range Requests.
        
        Returns:
            (data, status_code, start, total_size)
        """
        is_valid, full_path = cls.validate_path(path)
        
        if not is_valid or not full_path.exists():
            return None, 404, 0, 0
        
        file_size = full_path.stat().st_size
        
        if range_header:
            # Parse Range header
            try:
                byte_range = range_header.replace('bytes=', '').split('-')
                start = int(byte_range[0]) if byte_range[0] else 0
                end = int(byte_range[1]) if byte_range[1] else file_size - 1
                
                chunk_size = end - start + 1
                
                with open(full_path, 'rb') as f:
                    f.seek(start)
                    data = f.read(chunk_size)
                
                return data, 206, start, file_size
            except:
                pass
        
        # Sin range, servir archivo completo
        with open(full_path, 'rb') as f:
            data = f.read()
        
        return data, 200, 0, file_size
