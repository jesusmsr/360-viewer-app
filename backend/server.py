#!/usr/bin/env python3
"""
Servidor para 360° Video Viewer - DUAL PORT
Puerto 8080: Web UI (localhost only)
Puerto 8081: Federación P2P (protegida por invites JWT)
"""
from flask import Flask, send_from_directory, jsonify, request, send_file, abort
from flask_cors import CORS, cross_origin
import os
from pathlib import Path
import json
from datetime import datetime, timedelta
import hashlib
import secrets
import threading
import time
import requests

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    print("⚠️ PyJWT no instalado")

# ============================================
# CONFIGURACIÓN
# ============================================
VIDEOS_BASE_DIR = os.environ.get('VIDEOS_PATH', '/videos')
LIBRARIES_FILE = os.environ.get('LIBRARIES_FILE', '/app/.libraries.json')
STATIC_FOLDER = os.environ.get('STATIC_FOLDER', '/app/static')
PEERS_FILE = os.environ.get('PEERS_FILE', '/app/.peers.json')
FEDERATION_SYNC_INTERVAL = int(os.environ.get('FEDERATION_SYNC_INTERVAL', '300'))

WEB_PORT = int(os.environ.get('PORT', '8080'))
FEDERATION_PORT = int(os.environ.get('FEDERATION_PORT', '8081'))

JWT_SECRET = os.environ.get('JWT_SECRET', secrets.token_hex(32))
JWT_ALGORITHM = 'HS256'
VIDEO_TOKEN_EXPIRY = int(os.environ.get('VIDEO_TOKEN_EXPIRY', '3600'))

# Ya no usamos ALLOWED_PEERS_FILE - los peers se autentican con JWT
# ALLOWED_PEERS_FILE = os.environ.get('ALLOWED_PEERS_FILE', '/app/.allowed_peers.json')

peers_cache = {}
peers_lock = threading.Lock()

# ============================================
# FUNCIONES UTILIDAD
# ============================================
def load_peers():
    if os.path.exists(PEERS_FILE):
        with open(PEERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_peers(peers):
    os.makedirs(os.path.dirname(PEERS_FILE), exist_ok=True)
    with open(PEERS_FILE, 'w') as f:
        json.dump(peers, f, indent=2)

def generate_video_token(video_path, peer_id='local', expiry_seconds=VIDEO_TOKEN_EXPIRY):
    if not JWT_AVAILABLE:
        return None
    payload = {
        'video_path': video_path,
        'peer_id': peer_id,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(seconds=expiry_seconds),
        'jti': secrets.token_hex(16)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_video_token(token):
    if not JWT_AVAILABLE:
        return None
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return {'error': 'Token expirado'}
    except jwt.InvalidTokenError:
        return {'error': 'Token inválido'}

def verify_peer_token(token):
    """Verifica un JWT de peer. Devuelve el payload si es válido, None si no."""
    if not JWT_AVAILABLE:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        # Verificar que sea un token de tipo 'peer_access'
        if payload.get('type') != 'peer_access':
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_catalog_for_sharing():
    base_path = Path(VIDEOS_BASE_DIR)
    if not base_path.exists():
        return {'items': [], 'total_size': 0}
    items = []
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
    total_size = 0
    try:
        for file_path in base_path.rglob('*'):
            if file_path.suffix.lower() in video_extensions:
                stat = file_path.stat()
                relative_path = str(file_path.relative_to(base_path))
                items.append({
                    'name': file_path.name,
                    'path': relative_path,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
                total_size += stat.st_size
    except Exception as e:
        print(f"Error escaneando catálogo: {e}")
    return {'items': items, 'total_videos': len(items), 'total_size': total_size, 'server_time': datetime.now().isoformat()}

def sync_peer(peer_id, peer_config):
    try:
        url = f"{peer_config['url']}/api/federation/catalog"
        headers = {
            'X-Peer-Token': peer_config.get('token', ''),
            'X-Peer-Id': peer_config.get('my_id', 'unknown')
        }
        response = requests.get(url, headers=headers, timeout=10)
        with peers_lock:
            if response.status_code == 200:
                peers_cache[peer_id] = {
                    'catalog': response.json(),
                    'last_sync': datetime.now().isoformat(),
                    'status': 'online',
                    'config': peer_config
                }
            else:
                peers_cache[peer_id] = {
                    'catalog': {},
                    'last_sync': datetime.now().isoformat(),
                    'status': f'error_{response.status_code}',
                    'config': peer_config
                }
        return response.status_code == 200
    except Exception as e:
        with peers_lock:
            peers_cache[peer_id] = {
                'catalog': {},
                'last_sync': datetime.now().isoformat(),
                'status': 'offline',
                'error': str(e),
                'config': peer_config
            }
        return False

def federation_sync_worker():
    while True:
        try:
            peers = load_peers()
            for peer_id, peer_config in peers.items():
                if peer_config.get('enabled', True):
                    sync_peer(peer_id, peer_config)
            time.sleep(FEDERATION_SYNC_INTERVAL)
        except Exception as e:
            print(f"Error en sync worker: {e}")
            time.sleep(60)

# ============================================
# APP WEB (Puerto 8080) - Todo excepto federación externa
# ============================================
web_app = Flask('web')
if os.environ.get('FLASK_CORS'):
    CORS(web_app, resources={r"/api/*": {"origins": "*"}, r"/videos/*": {"origins": "*"}})

# API de bibliotecas
@web_app.route('/api/libraries', methods=['GET'])
def get_libraries():
    if os.path.exists(LIBRARIES_FILE):
        with open(LIBRARIES_FILE, 'r') as f:
            return jsonify(json.load(f))
    return jsonify({})

@web_app.route('/api/libraries', methods=['POST'])
def create_library():
    data = request.json
    library_id = data.get('id', str(datetime.now().timestamp()))
    libraries = {}
    if os.path.exists(LIBRARIES_FILE):
        with open(LIBRARIES_FILE, 'r') as f:
            libraries = json.load(f)
    libraries[library_id] = {
        'id': library_id,
        'name': data.get('name', 'Nueva Biblioteca'),
        'path': data.get('path', ''),
        'description': data.get('description', ''),
        'created': datetime.now().isoformat()
    }
    os.makedirs(os.path.dirname(LIBRARIES_FILE), exist_ok=True)
    with open(LIBRARIES_FILE, 'w') as f:
        json.dump(libraries, f, indent=2)
    return jsonify(libraries[library_id]), 201

@web_app.route('/api/scan', methods=['POST'])
def scan_videos():
    videos = []
    base_path = Path(VIDEOS_BASE_DIR)
    if not base_path.exists():
        return jsonify({'videos': [], 'count': 0})
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
    for file_path in base_path.rglob('*'):
        if file_path.suffix.lower() in video_extensions:
            relative_path = file_path.relative_to(base_path)
            videos.append({
                'id': str(file_path.stat().st_mtime) + str(file_path),
                'name': file_path.name,
                'path': str(relative_path),
                'size': file_path.stat().st_size,
                'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            })
    videos.sort(key=lambda x: x['modified'], reverse=True)
    return jsonify({'videos': videos, 'count': len(videos)})

@web_app.route('/api/browse', methods=['GET', 'OPTIONS'])
@cross_origin(origins="*", supports_credentials=True)
def browse():
    folder_path = request.args.get('path', '')
    full_path = Path(VIDEOS_BASE_DIR) / folder_path
    try:
        full_path.relative_to(Path(VIDEOS_BASE_DIR))
    except ValueError:
        return jsonify({'items': [], 'exists': False})
    if not full_path.exists() or not full_path.is_dir():
        return jsonify({'items': [], 'exists': False})
    items = []
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
    try:
        for item in sorted(full_path.iterdir()):
            if item.is_dir():
                items.append({'name': item.name, 'path': str(item.relative_to(Path(VIDEOS_BASE_DIR))), 'type': 'folder'})
            elif item.suffix.lower() in video_extensions:
                items.append({
                    'name': item.name,
                    'path': str(item.relative_to(Path(VIDEOS_BASE_DIR))),
                    'type': 'video',
                    'modified': datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                    'size': item.stat().st_size
                })
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    return jsonify({'items': items, 'current_path': folder_path, 'exists': True})

@web_app.route('/videos/<path:filename>')
@cross_origin(origins="*")
def serve_video(filename):
    video_path = Path(VIDEOS_BASE_DIR) / filename
    try:
        video_path.relative_to(Path(VIDEOS_BASE_DIR))
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 403
    if not video_path.exists():
        return jsonify({'error': 'Video not found'}), 404
    token = request.args.get('token')
    if token:
        if not JWT_AVAILABLE:
            return jsonify({'error': 'JWT no disponible'}), 501
        payload = verify_video_token(token)
        if isinstance(payload, dict) and 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        if payload.get('video_path') != filename:
            return jsonify({'error': 'Token no válido para este video'}), 403
    return send_file(str(video_path), mimetype='video/mp4')

@web_app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'port': 'web'})

# APIs de gestión de peers (solo local)
@web_app.route('/api/peers', methods=['GET'])
def list_peers():
    peers = load_peers()
    safe_peers = {}
    for peer_id, config in peers.items():
        with peers_lock:
            cache_info = peers_cache.get(peer_id, {})
        safe_peers[peer_id] = {
            'id': peer_id,
            'name': config.get('name', peer_id),
            'url': config.get('url'),
            'enabled': config.get('enabled', True),
            'status': cache_info.get('status', 'unknown'),
            'last_sync': cache_info.get('last_sync'),
            'video_count': cache_info.get('catalog', {}).get('total_videos', 0)
        }
    return jsonify(safe_peers)

@web_app.route('/api/peers', methods=['POST'])
def add_peer():
    data = request.json
    peer_id = data.get('id') or secrets.token_hex(8)
    peer_url = data.get('url', '').rstrip('/')
    peer_name = data.get('name', 'Amigo')
    peer_token = data.get('token')
    if not peer_url:
        return jsonify({'error': 'URL requerida'}), 400
    if not peer_url.startswith(('http://', 'https://')):
        peer_url = f"http://{peer_url}"
    peers = load_peers()
    if peer_id in peers:
        return jsonify({'error': 'Peer ya existe'}), 409
    peers[peer_id] = {
        'id': peer_id,
        'name': peer_name,
        'url': peer_url,
        'token': peer_token,
        'enabled': True,
        'created': datetime.now().isoformat()
    }
    save_peers(peers)
    sync_peer(peer_id, peers[peer_id])
    return jsonify({'success': True, 'peer': {'id': peer_id, 'name': peer_name}}), 201

@web_app.route('/api/peers/<peer_id>', methods=['DELETE'])
def remove_peer(peer_id):
    peers = load_peers()
    if peer_id not in peers:
        return jsonify({'error': 'Peer no encontrado'}), 404
    
    # Eliminar de peers.json
    removed_peer = peers.pop(peer_id)
    save_peers(peers)
    
    # Eliminar del cache en memoria
    with peers_lock:
        if peer_id in peers_cache:
            del peers_cache[peer_id]
    
    return jsonify({'success': True, 'message': f"Peer '{removed_peer.get('name', peer_id)}' eliminado"})

@web_app.route('/api/peers/<peer_id>/enable', methods=['POST'])
def enable_peer(peer_id):
    peers = load_peers()
    if peer_id not in peers:
        return jsonify({'error': 'Peer no encontrado'}), 404
    
    data = request.json or {}
    peers[peer_id]['enabled'] = data.get('enabled', True)
    save_peers(peers)
    
    return jsonify({'success': True, 'enabled': peers[peer_id]['enabled']})

@web_app.route('/api/peers/<peer_id>/video-url', methods=['POST'])
def get_peer_video_url(peer_id):
    """Solicita un token de video a un peer remoto."""
    peers = load_peers()
    if peer_id not in peers:
        return jsonify({'error': 'Peer no encontrado'}), 404
    
    peer = peers[peer_id]
    data = request.json or {}
    video_path = data.get('video_path')
    
    if not video_path:
        return jsonify({'error': 'video_path requerido'}), 400
    
    try:
        # Construir URL del peer - usar tal cual si es HTTPS
        # (Cloudflare/proxy maneja el puerto internamente)
        peer_url = peer.get('url', '').rstrip('/')
        if ':8080' in peer_url:
            peer_url = peer_url.replace(':8080', ':8081')
        elif not ':8081' in peer_url and not peer_url.startswith('https://'):
            # Solo añadir :8081 si no es HTTPS (para HTTP directo)
            peer_url = peer_url + ':8081'
        
        # Llamar al endpoint de video-token del peer
        token_url = f"{peer_url}/api/federation/video-token"
        headers = {
            'X-Peer-Token': peer.get('token', ''),
            'Content-Type': 'application/json'
        }
        
        response = requests.post(token_url, 
                                headers=headers,
                                json={'video_path': video_path},
                                timeout=10)
        
        if response.status_code != 200:
            return jsonify({'error': f'Error del peer: {response.text}'}), response.status_code
        
        token_data = response.json()
        
        # Construir URL final del video con token
        video_url = f"{peer_url}/videos/{video_path}?token={token_data.get('token')}"
        
        return jsonify({
            'url': video_url,
            'token': token_data.get('token'),
            'expires_in': token_data.get('expires_in', 3600)
        })
        
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'No se pudo conectar con el peer'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/peers/<peer_id>/browse', methods=['GET'])
def browse_peer(peer_id):
    """Browse jerárquico en un peer remoto."""
    peers = load_peers()
    if peer_id not in peers:
        return jsonify({'error': 'Peer no encontrado'}), 404
    
    peer = peers[peer_id]
    path = request.args.get('path', '')
    
    try:
        # Construir URL del peer
        peer_url = peer.get('url', '').rstrip('/')
        if ':8080' in peer_url:
            peer_url = peer_url.replace(':8080', ':8081')
        elif not ':8081' in peer_url and not peer_url.startswith('https://'):
            peer_url = peer_url + ':8081'
        
        # Llamar al endpoint de browse del peer
        browse_url = f"{peer_url}/api/federation/browse"
        headers = {'X-Peer-Token': peer.get('token', '')}
        
        response = requests.get(browse_url, 
                               headers=headers,
                               params={'path': path},
                               timeout=10)
        
        if response.status_code != 200:
            return jsonify({'error': f'Error del peer: {response.text}'}), response.status_code
        
        return jsonify(response.json())
        
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'No se pudo conectar con el peer'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/federation/unified')
def federation_unified():
    local_catalog = get_catalog_for_sharing()
    peer_catalogs = []
    with peers_lock:
        for peer_id, cache in peers_cache.items():
            if cache.get('status') == 'online':
                peer_catalogs.append({
                    'peer_id': peer_id,
                    'peer_name': cache['config'].get('name', peer_id),
                    'items': cache['catalog'].get('items', []),
                    'total_videos': cache['catalog'].get('total_videos', 0)
                })
    return jsonify({
        'local': local_catalog,
        'peers': peer_catalogs,
        'total_unified_videos': local_catalog.get('total_videos', 0) + sum(p.get('total_videos', 0) for p in peer_catalogs)
    })

# Frontend React
@web_app.route('/')
def index():
    if os.path.exists(os.path.join(STATIC_FOLDER, 'index.html')):
        return send_from_directory(STATIC_FOLDER, 'index.html')
    return jsonify({'status': '360° Viewer Web', 'static_folder': STATIC_FOLDER})

@web_app.route('/<path:path>')
def serve_static(path):
    if path.startswith('api/') or path.startswith('videos/'):
        return jsonify({'error': 'Not found'}), 404
    file_path = os.path.join(STATIC_FOLDER, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return send_from_directory(STATIC_FOLDER, path)
    if os.path.exists(os.path.join(STATIC_FOLDER, 'index.html')):
        return send_from_directory(STATIC_FOLDER, 'index.html')
    return jsonify({'error': 'Not found'}), 404

# ============================================
# APP FEDERACIÓN (Puerto 8081) - Solo peers con invite JWT
# ============================================
fed_app = Flask('federation')
CORS(fed_app, resources={r"/*": {"origins": "*"}})

def require_auth():
    """Verifica JWT firmado. NO consulta archivos."""
    peer_token = request.headers.get('X-Peer-Token')
    
    if not peer_token:
        return jsonify({'error': 'X-Peer-Token header requerido'}), 401
    
    # Verificar JWT firmado por nosotros
    payload = verify_peer_token(peer_token)
    if not payload:
        return jsonify({'error': 'Token no válido o expirado'}), 401
    
    # Guardar info del peer en el contexto de la request para usar después
    request.peer_payload = payload
    return None  # Autorizado

# Endpoint público (solo para canjear invites)
@fed_app.route('/api/federation/join', methods=['POST'])
# Endpoint público (para unirse con invite) - SOLO devuelve token, NO guarda nada
@fed_app.route("/api/federation/join", methods=["POST"])
def join_with_invite():
    """
    Endpoint para que un cliente SE UNA a este servidor.
    El cliente debe llamar a este endpoint en el servidor al que quiere unirse.
    Devuelve el token JWT. El cliente debe guardar el peer localmente.
    """
    data = request.json
    peer_url = data.get("url", "").rstrip("/")
    invite_code = data.get("invite_code", "").upper().replace(" ", "-")
    my_name = data.get("my_name", "Amigo")
    
    if not peer_url:
        return jsonify({"error": "URL requerida"}), 400
    if not peer_url.startswith(("http://", "https://")):
        peer_url = f"http://{peer_url}"
    if not invite_code:
        return jsonify({"error": "Código requerido"}), 400
    
    # El cliente genera su propio ID
    my_peer_id = data.get("my_id") or secrets.token_hex(8)
    
    try:
        # Llamar a verify-invite en el SERVIDOR (peer_url) para obtener token
        verify_url = f"{peer_url}/api/federation/verify-invite"
        response = requests.post(verify_url, json={
            "invite_code": invite_code,
            "peer_name": my_name,
            "peer_id": my_peer_id
        }, timeout=10)
        
        if response.status_code != 200:
            return jsonify({"error": response.json().get("error", "Código inválido")}), 400
        
        invite_data = response.json()
        
        # Solo devolver los datos al cliente - NO guardar nada en el servidor
        return jsonify({
            "success": True,
            "peer_id": invite_data.get("server_id", "unknown"),
            "peer_name": invite_data.get("peer_name") or invite_data.get("server_name", "Servidor"),
            "token": invite_data.get("access_token"),
            "your_id": invite_data.get("your_id"),
            "message": f"Token obtenido para {invite_data.get('peer_name', 'Servidor')}"
        })
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "No se pudo conectar con el servidor"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# Endpoint público (para verificar invites)
@fed_app.route('/api/federation/verify-invite', methods=['POST'])
def verify_invite():
    """Verifica un invite y devuelve un JWT firmado. NO guarda el peer."""
    data = request.json
    invite_code = data.get('invite_code', '').upper().replace(' ', '-')
    peer_name = data.get('peer_name', 'Invitado')
    peer_id = data.get('peer_id')  # ID que el peer se asigna a sí mismo
    
    if not peer_id:
        peer_id = secrets.token_hex(8)  # Generar uno si no viene
    
    invitations_file = PEERS_FILE.replace('.json', '.invitations.json')
    if not os.path.exists(invitations_file):
        return jsonify({'error': 'No hay invitaciones'}), 404
    
    with open(invitations_file, 'r') as f:
        invitations = json.load(f)
    
    if invite_code not in invitations:
        return jsonify({'error': 'Código inválido'}), 400
    
    invitation = invitations[invite_code]
    if datetime.now() > datetime.fromisoformat(invitation['expires']):
        return jsonify({'error': 'Expirado'}), 400
    if invitation.get('used'):
        return jsonify({'error': 'Ya usado'}), 400
    
    # Marcar como usado
    invitation['used'] = True
    invitation['used_by'] = peer_name
    invitation['used_at'] = datetime.now().isoformat()
    
    with open(invitations_file, 'w') as f:
        json.dump(invitations, f, indent=2)
    
    # Generar JWT firmado para este peer (NO guardamos nada)
    access_token = jwt.encode({
        'peer_id': peer_id,
        'peer_name': peer_name,
        'invite_code': invite_code,
        'permissions': invitation.get('permissions', ['read_catalog']),
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(days=30),  # Token válido por 30 días
        'type': 'peer_access'
    }, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    # Devolver también nuestro propio ID y nombre
    my_peers = load_peers()
    my_id = list(my_peers.keys())[0] if my_peers else 'server_' + secrets.token_hex(4)
    
    return jsonify({
        'success': True,
        'access_token': access_token,  # JWT firmado
        'peer_name': invitation.get('name', 'Biblioteca'),
        'your_id': peer_id,
        'server_id': my_id,  # ID del servidor (NAS)
        'server_name': 'Mi NAS'  # Nombre del servidor
    })

# Endpoints PROTEGIDOS (requieren token válido)
@fed_app.route('/api/federation/catalog')
def federation_catalog():
    auth_error = require_auth()
    if auth_error:
        return auth_error
    catalog = get_catalog_for_sharing()
    catalog['shared_by'] = {'id': 'me', 'name': 'Mi Biblioteca'}
    return jsonify(catalog)

@fed_app.route('/api/federation/browse')
def federation_browse():
    """Browse jerárquico de carpetas y videos."""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    folder_path = request.args.get('path', '')
    full_path = Path(VIDEOS_BASE_DIR) / folder_path
    
    try:
        full_path.relative_to(Path(VIDEOS_BASE_DIR))
    except ValueError:
        return jsonify({'items': [], 'exists': False, 'error': 'Invalid path'})
    
    if not full_path.exists() or not full_path.is_dir():
        return jsonify({'items': [], 'exists': False, 'error': 'Not found'})
    
    items = []
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
    
    try:
        for item in sorted(full_path.iterdir()):
            relative_path = str(item.relative_to(Path(VIDEOS_BASE_DIR)))
            if item.is_dir():
                items.append({
                    'name': item.name,
                    'path': relative_path,
                    'type': 'folder'
                })
            elif item.suffix.lower() in video_extensions:
                stat = item.stat()
                items.append({
                    'name': item.name,
                    'path': relative_path,
                    'type': 'video',
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'size': stat.st_size
                })
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    
    return jsonify({
        'items': items,
        'current_path': folder_path,
        'exists': True
    })

@fed_app.route('/api/federation/video-token', methods=['POST'])
def request_video_token():
    if not JWT_AVAILABLE:
        return jsonify({'error': 'JWT no disponible'}), 501
    
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    data = request.json
    video_path = data.get('video_path')
    peer_id = request.peer_payload.get('peer_id', 'unknown')
    
    if not video_path:
        return jsonify({'error': 'video_path requerido'}), 400
    
    full_path = Path(VIDEOS_BASE_DIR) / video_path
    try:
        full_path.relative_to(Path(VIDEOS_BASE_DIR))
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 403
    
    if not full_path.exists():
        return jsonify({'error': 'Video no encontrado'}), 404
    
    token = generate_video_token(video_path, peer_id)
    return jsonify({
        'token': token,
        'expires_in': VIDEO_TOKEN_EXPIRY
    })

@fed_app.route('/videos/<path:filename>')
@cross_origin(origins="*")
def serve_video_federation(filename):
    """Servir videos con validación de token en el puerto de federación."""
    video_path = Path(VIDEOS_BASE_DIR) / filename
    try:
        video_path.relative_to(Path(VIDEOS_BASE_DIR))
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 403
    if not video_path.exists():
        return jsonify({'error': 'Video not found'}), 404
    token = request.args.get('token')
    if token:
        if not JWT_AVAILABLE:
            return jsonify({'error': 'JWT no disponible'}), 501
        payload = verify_video_token(token)
        if isinstance(payload, dict) and 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        if payload.get('video_path') != filename:
            return jsonify({'error': 'Token no válido para este video'}), 403
    return send_file(str(video_path), mimetype='video/mp4')

@web_app.route('/api/federation/invite', methods=['POST'])
def create_invitation():
    data = request.json
    def generate_invite_code():
        parts = [''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(3)) for _ in range(3)]
        return '-'.join(parts)
    
    invite_code = generate_invite_code()
    invitation = {
        'code': invite_code,
        'name': data.get('name', 'Invitado'),
        'permissions': data.get('permissions', ['read_catalog']),
        'created': datetime.now().isoformat(),
        'expires': (datetime.now() + timedelta(days=7)).isoformat(),
        'used': False
    }
    
    invitations_file = PEERS_FILE.replace('.json', '.invitations.json')
    invitations = {}
    if os.path.exists(invitations_file):
        with open(invitations_file, 'r') as f:
            invitations = json.load(f)
    invitations[invite_code] = invitation
    os.makedirs(os.path.dirname(invitations_file), exist_ok=True)
    with open(invitations_file, 'w') as f:
        json.dump(invitations, f, indent=2)
    
    return jsonify({
        'success': True,
        'invite_code': invite_code,
        'expires': invitation['expires']
    })

@web_app.route('/api/federation/health')
def federation_health():
    return jsonify({'status': 'ok', 'port': 'federation', 'protected': True})

# ============================================
# INICIAR SERVIDORES
# ============================================
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--videos', help='Directorio de videos')
    args = parser.parse_args()
    
    if args.videos:
        VIDEOS_BASE_DIR = args.videos
    
    print(f"📁 Videos: {VIDEOS_BASE_DIR}")
    print(f"🌐 Puerto Web (UI): {WEB_PORT}")
    print(f"🔐 Puerto Federación: {FEDERATION_PORT}")
    
    # Iniciar worker de sincronización
    sync_thread = threading.Thread(target=federation_sync_worker, daemon=True)
    sync_thread.start()
    print("🤝 Worker de federación iniciado")
    
    # Iniciar ambos servidores en threads separados
    def run_web():
        web_app.run(host='0.0.0.0', port=WEB_PORT, debug=False, threaded=True)
    
    def run_federation():
        fed_app.run(host='0.0.0.0', port=FEDERATION_PORT, debug=False, threaded=True)
    
    web_thread = threading.Thread(target=run_web, daemon=True)
    fed_thread = threading.Thread(target=run_federation, daemon=True)
    
    web_thread.start()
    fed_thread.start()
    
    print(f"✅ Servidor Web en http://0.0.0.0:{WEB_PORT}")
    print(f"✅ Servidor Federación en http://0.0.0.0:{FEDERATION_PORT}")
    print("Press CTRL+C para salir")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Servidor detenido")
