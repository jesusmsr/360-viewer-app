"""
Rutas de la Web UI (puerto 8080).
Acceso local/desarrollo.
"""
from pathlib import Path
from datetime import datetime

from flask import Blueprint, send_from_directory, jsonify, request, abort

from app.config import Config
from app.models.peer import Peer
from app.services.peer_service import PeerService
from app.services.invite_service import InviteService
from app.services.video_service import VideoService

# Blueprint
web_bp = Blueprint('web', __name__)

# Directorio de archivos estáticos
STATIC_DIR = Path(__file__).parent.parent.parent / 'static'


@web_bp.route('/')
def index():
    """Página principal."""
    return send_from_directory(STATIC_DIR, 'index.html')


@web_bp.route('/<path:filename>')
def static_files(filename):
    """Archivos estáticos."""
    return send_from_directory(STATIC_DIR, filename)


# ============================================
# API Local - Gestión de peers e invitaciones
# ============================================

@web_bp.route('/api/peers', methods=['GET'])
def list_peers():
    """Listar peers registrados localmente como objeto (id -> peer)."""
    peers = PeerService.list_peers()
    # Devolver como objeto para facilitar acceso por ID en el frontend
    peers_dict = {peer.id: peer.to_dict() for peer in peers}
    return jsonify(peers_dict)


@web_bp.route('/api/peers', methods=['POST'])
def add_peer():
    """Añadir un peer."""
    data = request.json
    
    peer = Peer(
        id=data.get('id') or PeerService.generate_id(),
        name=data['name'],
        url=data['url'],
        token=data.get('token'),
        status='online'
    )
    
    PeerService.add_peer(peer)
    return jsonify(peer.to_dict()), 201


@web_bp.route('/api/peers/<peer_id>', methods=['DELETE'])
def remove_peer(peer_id):
    """Eliminar un peer."""
    success = PeerService.delete_peer(peer_id)
    if not success:
        return jsonify({'error': 'Peer no encontrado'}), 404
    return jsonify({'success': True})


@web_bp.route('/api/peers/<peer_id>/sync', methods=['POST'])
def sync_peer(peer_id):
    """Sincronizar catálogo con un peer."""
    peer = PeerService.get_peer(peer_id)
    if not peer:
        return jsonify({'error': 'Peer no encontrado'}), 404
    
    # Actualizar status
    PeerService.update_peer(peer_id, status='syncing')
    
    try:
        import requests
        headers = {}
        if peer.token:
            headers['X-Peer-Token'] = peer.token
        
        response = requests.get(
            f"{peer.url}/api/federation/catalog",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            PeerService.update_peer(peer_id, status='online', last_seen=datetime.now().isoformat())
            return jsonify({'success': True, 'catalog': response.json()})
        else:
            PeerService.update_peer(peer_id, status='error')
            return jsonify({'error': f'Error del peer: {response.status_code}'}), 502
    
    except Exception as e:
        PeerService.update_peer(peer_id, status='offline')
        return jsonify({'error': str(e)}), 502


@web_bp.route('/api/peers/<peer_id>/video-url', methods=['POST'])
def get_peer_video_url(peer_id):
    """Obtener URL firmada para ver un video de un peer."""
    from app.utils.auth import generate_video_token
    from datetime import datetime
    
    peer = PeerService.get_peer(peer_id)
    if not peer:
        return jsonify({'error': 'Peer no encontrado'}), 404
    
    data = request.json
    video_path = data.get('video_path')
    
    if not video_path:
        return jsonify({'error': 'video_path requerido'}), 400
    
    # Construir URL base
    base_url = peer.url
    if not base_url.startswith('http'):
        base_url = 'http://' + base_url
    
    # Solo añadir puerto si NO es HTTPS
    if not base_url.startswith('https://'):
        base_url = base_url.rstrip('/') + ':8081'
    
    # Solicitar token al peer remoto
    try:
        import requests
        headers = {'Content-Type': 'application/json'}
        if peer.token:
            headers['X-Peer-Token'] = peer.token
        
        token_response = requests.post(
            f"{base_url}/api/federation/video-token",
            json={'video_path': video_path},
            headers=headers,
            timeout=5
        )
        
        if token_response.status_code == 200:
            token_data = token_response.json()
            # Asegurar que base_url no termine con / para evitar doble slash
            video_url = f"{base_url.rstrip('/')}/videos/{video_path}?token={token_data['token']}"
            return jsonify({
                'url': video_url,
                'token': token_data['token'],
                'expires_in': token_data.get('expires_in', 3600)
            })
        else:
            return jsonify({'error': 'No se pudo obtener token del peer'}), 502
    
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@web_bp.route('/api/peers/<peer_id>/browse')
def browse_peer(peer_id):
    """Navegar carpetas de un peer."""
    peer = PeerService.get_peer(peer_id)
    if not peer:
        return jsonify({'error': 'Peer no encontrado'}), 404
    
    path = request.args.get('path', '')
    
    try:
        import requests
        headers = {}
        if peer.token:
            headers['X-Peer-Token'] = peer.token
        
        response = requests.get(
            f"{peer.url}/api/federation/browse",
            params={'path': path},
            headers=headers,
            timeout=10
        )
        
        return jsonify(response.json()), response.status_code
    
    except Exception as e:
        return jsonify({'error': str(e)}), 502


# ============================================
# Videos locales
# ============================================

@web_bp.route('/api/videos')
def list_local_videos():
    """Listar videos locales."""
    videos = VideoService.list_videos()
    return jsonify(videos)


@web_bp.route('/api/videos/<path:filename>')
def serve_local_video(filename):
    """Servir video local (sin auth, acceso directo)."""
    is_valid, full_path = VideoService.validate_path(filename)
    
    if not is_valid or not full_path.exists():
        abort(404)
    
    return send_from_directory(Config.VIDEOS_DIR, filename)


# ============================================
# Invitaciones (efímeras - no se listan)
# ============================================

@web_bp.route('/api/invites', methods=['POST'])
def create_my_invite():
    """Crear nueva invitación efímera."""
    data = request.json or {}
    name = data.get('name', 'Invitado')
    
    invite = InviteService.create_invite(name)
    return jsonify(invite.to_dict()), 201





# ============================================
# Librerías locales
# ============================================

@web_bp.route('/api/libraries', methods=['GET'])
def list_libraries():
    """Listar librerías locales."""
    # Por ahora, devolvemos carpetas en VIDEOS_DIR
    from app.config import Config
    base_path = Path(Config.VIDEOS_DIR)
    
    libraries = []
    if base_path.exists():
        for item in sorted(base_path.iterdir()):
            if item.is_dir():
                libraries.append({
                    'id': str(item.relative_to(base_path)),
                    'name': item.name,
                    'path': str(item.relative_to(base_path)),
                    'type': 'local'
                })
    
    return jsonify(libraries)


@web_bp.route('/api/browse')
def browse_local():
    """Navegar carpetas locales (jerárquico)."""
    from app.config import Config
    base_path = Path(Config.VIDEOS_DIR)
    path = request.args.get('path', '')
    
    # Construir ruta completa de forma segura
    target_path = base_path / path if path else base_path
    target_path = target_path.resolve()
    
    # Seguridad: verificar que está dentro de VIDEOS_DIR
    try:
        target_path.relative_to(base_path.resolve())
    except ValueError:
        return jsonify({'error': 'Ruta no permitida'}), 403
    
    if not target_path.exists():
        return jsonify({'error': 'Ruta no encontrada'}), 404
    
    items = []
    
    if target_path.is_dir():
        for item in sorted(target_path.iterdir()):
            rel_path = str(item.relative_to(base_path)) if path else item.name
            
            if item.is_dir():
                items.append({
                    'type': 'folder',
                    'name': item.name,
                    'path': rel_path,
                    'modified': datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                })
            elif item.suffix.lower() in ['.mp4', '.webm', '.mov', '.mkv', '.avi']:
                items.append({
                    'type': 'video',
                    'name': item.name,
                    'path': rel_path,
                    'size': item.stat().st_size,
                    'modified': datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                })
    
    # Construir breadcrumbs
    breadcrumbs = [{'name': '📁 Raíz', 'path': ''}]
    if path:
        parts = path.split('/')
        current = ''
        for part in parts:
            current = f"{current}/{part}" if current else part
            breadcrumbs.append({'name': part, 'path': current})
    
    return jsonify({
        'items': items,
        'breadcrumbs': breadcrumbs,
        'path': path
    })
