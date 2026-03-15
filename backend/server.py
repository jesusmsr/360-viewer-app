#!/usr/bin/env python3
"""
Servidor para 360° Video Viewer
Sistema de bibliotecas con navegación de carpetas
"""
from flask import Flask, send_from_directory, jsonify, request, send_file
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

# Fase 2: JWT para tokens de video seguros
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    print("⚠️ PyJWT no instalado. Instálalo con: pip install PyJWT")

app = Flask(__name__)

# Habilitar CORS si está configurado
if os.environ.get('FLASK_CORS'):
    CORS(app, resources={
        r"/api/*": {"origins": "*"},
        r"/videos/*": {"origins": "*"}
    })

# Configuración
VIDEOS_BASE_DIR = os.environ.get('VIDEOS_PATH', '/videos')
LIBRARIES_FILE = os.environ.get('LIBRARIES_FILE', '/app/.libraries.json')
STATIC_FOLDER = os.environ.get('STATIC_FOLDER', '/app/static')
PEERS_FILE = os.environ.get('PEERS_FILE', '/app/.peers.json')
FEDERATION_SYNC_INTERVAL = int(os.environ.get('FEDERATION_SYNC_INTERVAL', '300'))  # 5 minutos

# Configuración JWT para Fase 2
JWT_SECRET = os.environ.get('JWT_SECRET', secrets.token_hex(32))
JWT_ALGORITHM = 'HS256'
VIDEO_TOKEN_EXPIRY = int(os.environ.get('VIDEO_TOKEN_EXPIRY', '3600'))  # 1 hora por defecto
ALLOWED_PEERS_FILE = os.environ.get('ALLOWED_PEERS_FILE', '/app/.allowed_peers.json')  # Peers que pueden pedir tokens

# Datos en memoria
peers_cache = {}  # {peer_id: {catalog, last_sync, status}}
peers_lock = threading.Lock()


def load_peers():
    """Carga la configuración de peers desde disco"""
    if os.path.exists(PEERS_FILE):
        with open(PEERS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_peers(peers):
    """Guarda la configuración de peers a disco"""
    os.makedirs(os.path.dirname(PEERS_FILE), exist_ok=True)
    with open(PEERS_FILE, 'w') as f:
        json.dump(peers, f, indent=2)


def generate_peer_token():
    """Genera un token seguro para autenticación entre peers"""
    return secrets.token_urlsafe(32)


def generate_video_token(video_path, peer_id='local', expiry_seconds=VIDEO_TOKEN_EXPIRY):
    """Genera un token JWT para acceder a un video específico"""
    if not JWT_AVAILABLE:
        return None
    
    payload = {
        'video_path': video_path,
        'peer_id': peer_id,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(seconds=expiry_seconds),
        'jti': secrets.token_hex(16)  # JWT ID único para revocación si es necesario
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_video_token(token):
    """Verifica un token JWT de video"""
    if not JWT_AVAILABLE:
        return None
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return {'error': 'Token expirado'}
    except jwt.InvalidTokenError:
        return {'error': 'Token inválido'}


def load_allowed_peers():
    """Carga la lista de peers autorizados a solicitar tokens"""
    if os.path.exists(ALLOWED_PEERS_FILE):
        with open(ALLOWED_PEERS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_allowed_peer(peer_id, peer_info):
    """Guarda un peer autorizado"""
    allowed = load_allowed_peers()
    allowed[peer_id] = {
        **peer_info,
        'added': datetime.now().isoformat()
    }
    os.makedirs(os.path.dirname(ALLOWED_PEERS_FILE), exist_ok=True)
    with open(ALLOWED_PEERS_FILE, 'w') as f:
        json.dump(allowed, f, indent=2)


def is_peer_allowed(peer_id, token):
    """Verifica si un peer está autorizado (con token válido)"""
    allowed = load_allowed_peers()
    
    if peer_id not in allowed:
        return False
    
    peer = allowed[peer_id]
    # Verificar que el token coincida
    return peer.get('token') == token


def get_catalog_for_sharing():
    """Genera el catálogo de videos para compartir con otros peers"""
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
    
    return {
        'items': items,
        'total_videos': len(items),
        'total_size': total_size,
        'server_time': datetime.now().isoformat(),
        'videos_path': VIDEOS_BASE_DIR
    }


def sync_peer(peer_id, peer_config):
    """Sincroniza el catálogo de un peer"""
    try:
        url = f"{peer_config['url']}/api/federation/catalog"
        headers = {
            'X-Peer-Token': peer_config.get('token', ''),
            'X-Peer-Id': peer_config.get('my_id', 'unknown')
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            catalog = response.json()
            with peers_lock:
                peers_cache[peer_id] = {
                    'catalog': catalog,
                    'last_sync': datetime.now().isoformat(),
                    'status': 'online',
                    'config': peer_config
                }
            return True
        else:
            with peers_lock:
                peers_cache[peer_id] = {
                    'catalog': {},
                    'last_sync': datetime.now().isoformat(),
                    'status': f'error_{response.status_code}',
                    'config': peer_config
                }
            return False
            
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
    """Worker thread que sincroniza periódicamente con los peers"""
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
# RUTAS API - VAN PRIMERO
# ============================================

@app.route('/api/libraries', methods=['GET'])
def get_libraries():
    """Obtiene todas las bibliotecas"""
    if os.path.exists(LIBRARIES_FILE):
        with open(LIBRARIES_FILE, 'r') as f:
            return jsonify(json.load(f))
    return jsonify({})


@app.route('/api/libraries', methods=['POST'])
def create_library():
    """Crea una nueva biblioteca"""
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
    
    # Crear directorio si no existe
    os.makedirs(os.path.dirname(LIBRARIES_FILE), exist_ok=True)
    with open(LIBRARIES_FILE, 'w') as f:
        json.dump(libraries, f, indent=2)
    
    return jsonify(libraries[library_id]), 201


@app.route('/api/libraries/<library_id>', methods=['DELETE'])
def delete_library(library_id):
    """Elimina una biblioteca"""
    if not os.path.exists(LIBRARIES_FILE):
        return jsonify({'error': 'No libraries found'}), 404
    
    with open(LIBRARIES_FILE, 'r') as f:
        libraries = json.load(f)
    
    if library_id in libraries:
        del libraries[library_id]
        with open(LIBRARIES_FILE, 'w') as f:
            json.dump(libraries, f, indent=2)
        return jsonify({'success': True})
    
    return jsonify({'error': 'Library not found'}), 404


@app.route('/api/scan', methods=['POST'])
def scan_videos():
    """Escanea videos en el directorio base"""
    videos = []
    base_path = Path(VIDEOS_BASE_DIR)
    
    if not base_path.exists():
        return jsonify({'videos': [], 'count': 0, 'base_path': VIDEOS_BASE_DIR})
    
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
    
    for file_path in base_path.rglob('*'):
        if file_path.suffix.lower() in video_extensions:
            relative_path = file_path.relative_to(base_path)
            videos.append({
                'id': str(file_path.stat().st_mtime) + str(file_path),
                'name': file_path.name,
                'path': str(relative_path),
                'full_path': str(file_path),
                'size': file_path.stat().st_size,
                'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            })
    
    videos.sort(key=lambda x: x['modified'], reverse=True)
    
    return jsonify({
        'videos': videos,
        'count': len(videos),
        'base_path': VIDEOS_BASE_DIR
    })


@app.route('/api/folder-contents', methods=['POST'])
def get_folder_contents():
    """Obtiene contenido de una carpeta específica"""
    data = request.json
    folder_path = data.get('path', '')
    
    full_path = Path(VIDEOS_BASE_DIR) / folder_path
    
    # Security check
    try:
        full_path.relative_to(Path(VIDEOS_BASE_DIR))
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 403
    
    if not full_path.exists() or not full_path.is_dir():
        return jsonify({'folders': [], 'videos': []})
    
    folders = []
    videos = []
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
    
    for item in sorted(full_path.iterdir()):
        if item.is_dir():
            folders.append({
                'name': item.name,
                'path': str(item.relative_to(Path(VIDEOS_BASE_DIR)))
            })
        elif item.suffix.lower() in video_extensions:
            relative_path = item.relative_to(Path(VIDEOS_BASE_DIR))
            videos.append({
                'name': item.name,
                'path': str(relative_path),
                'modified': datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                'size': item.stat().st_size
            })
    
    return jsonify({
        'folders': folders,
        'videos': videos,
        'current_path': folder_path
    })


@app.route('/videos/<path:filename>')
@cross_origin(origins="*")
def serve_video(filename):
    """Sirve archivos de video (con soporte para tokens JWT de Fase 2)"""
    video_path = Path(VIDEOS_BASE_DIR) / filename
    
    # Security check
    try:
        video_path.relative_to(Path(VIDEOS_BASE_DIR))
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 403
    
    if not video_path.exists():
        return jsonify({'error': 'Video not found'}), 404
    
    # Fase 2: Verificar token JWT si viene como parámetro (acceso desde peers)
    token = request.args.get('token')
    if token:
        if not JWT_AVAILABLE:
            return jsonify({'error': 'JWT no disponible en el servidor'}), 501
        
        payload = verify_video_token(token)
        if isinstance(payload, dict) and 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        # Verificar que el token es para este video específico
        if payload.get('video_path') != filename:
            return jsonify({'error': 'Token no válido para este video'}), 403
    
    # Si no hay token, permitimos acceso local (o podríamos requerir auth)
    # En producción, podrías querer requerir token siempre
    
    return send_file(str(video_path), mimetype='video/mp4')


@app.route('/api/health')
def health():
    """Health check"""
    return jsonify({'status': 'ok', 'videos_path': VIDEOS_BASE_DIR})


@app.route('/api/browse', methods=['GET', 'OPTIONS'])
@cross_origin(origins="*", supports_credentials=True)
def browse():
    """Navega por carpetas (versión GET para el frontend)"""
    folder_path = request.args.get('path', '')
    
    full_path = Path(VIDEOS_BASE_DIR) / folder_path
    
    # Security check
    try:
        full_path.relative_to(Path(VIDEOS_BASE_DIR))
    except ValueError:
        return jsonify({'items': [], 'breadcrumbs': [], 'current_path': folder_path, 'exists': False})
    
    if not full_path.exists():
        return jsonify({'items': [], 'breadcrumbs': [], 'current_path': folder_path, 'exists': False})
    
    if not full_path.is_dir():
        return jsonify({'items': [], 'breadcrumbs': [], 'current_path': folder_path, 'error': 'Not a directory'}), 400
    
    items = []
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
    
    try:
        for item in sorted(full_path.iterdir()):
            if item.is_dir():
                items.append({
                    'name': item.name,
                    'path': str(item.relative_to(Path(VIDEOS_BASE_DIR))),
                    'type': 'folder'
                })
            elif item.suffix.lower() in video_extensions:
                relative_path = item.relative_to(Path(VIDEOS_BASE_DIR))
                items.append({
                    'name': item.name,
                    'path': str(relative_path),
                    'type': 'video',
                    'modified': datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                    'size': item.stat().st_size
                })
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    
    # Generar breadcrumbs
    breadcrumbs = [{'name': '📁 Raíz', 'path': ''}]
    if folder_path:
        parts = folder_path.split('/')
        current = ''
        for part in parts:
            if part:
                current = f"{current}/{part}" if current else part
                breadcrumbs.append({'name': part, 'path': current})
    
    return jsonify({
        'items': items,
        'breadcrumbs': breadcrumbs,
        'current_path': folder_path,
        'exists': True,
        'base_path': VIDEOS_BASE_DIR
    })


# ============================================
# RUTAS API - FEDERACIÓN (FASE 1)
# ============================================

@app.route('/api/peers', methods=['GET'])
def list_peers():
    """Lista todos los peers registrados (sin tokens por seguridad)"""
    peers = load_peers()
    # No devolvemos los tokens por seguridad
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
            'video_count': cache_info.get('catalog', {}).get('total_videos', 0),
            'my_id': config.get('my_id', 'unknown')
        }
    return jsonify(safe_peers)


@app.route('/api/peers', methods=['POST'])
def add_peer():
    """Añade un nuevo peer (registra a un amigo)"""
    data = request.json
    
    peer_id = data.get('id') or secrets.token_hex(8)
    peer_url = data.get('url')
    peer_name = data.get('name', 'Amigo')
    peer_token = data.get('token')  # Token que me da el amigo para autenticarme
    my_id = data.get('my_id', 'me')  # Mi ID en su sistema
    
    if not peer_url:
        return jsonify({'error': 'URL del peer requerida'}), 400
    
    # Normalizar URL (quitar trailing slash)
    peer_url = peer_url.rstrip('/')
    
    peers = load_peers()
    
    # Verificar si ya existe
    if peer_id in peers:
        return jsonify({'error': 'Peer ya existe'}), 409
    
    peers[peer_id] = {
        'id': peer_id,
        'name': peer_name,
        'url': peer_url,
        'token': peer_token,
        'my_id': my_id,
        'enabled': True,
        'created': datetime.now().isoformat()
    }
    
    save_peers(peers)
    
    # Intentar sincronizar inmediatamente
    sync_peer(peer_id, peers[peer_id])
    
    return jsonify({
        'success': True,
        'peer': {
            'id': peer_id,
            'name': peer_name,
            'url': peer_url,
            'status': 'pending'
        }
    }), 201


@app.route('/api/peers/<peer_id>', methods=['DELETE'])
def remove_peer(peer_id):
    """Elimina un peer"""
    peers = load_peers()
    
    if peer_id not in peers:
        return jsonify({'error': 'Peer no encontrado'}), 404
    
    del peers[peer_id]
    save_peers(peers)
    
    with peers_lock:
        if peer_id in peers_cache:
            del peers_cache[peer_id]
    
    return jsonify({'success': True})


@app.route('/api/peers/<peer_id>/sync', methods=['POST'])
def force_sync_peer(peer_id):
    """Fuerza la sincronización manual de un peer"""
    peers = load_peers()
    
    if peer_id not in peers:
        return jsonify({'error': 'Peer no encontrado'}), 404
    
    success = sync_peer(peer_id, peers[peer_id])
    
    with peers_lock:
        cache = peers_cache.get(peer_id, {})
    
    return jsonify({
        'success': success,
        'peer_id': peer_id,
        'status': cache.get('status'),
        'last_sync': cache.get('last_sync'),
        'video_count': cache.get('catalog', {}).get('total_videos', 0)
    })


@app.route('/api/federation/catalog')
def federation_catalog():
    """Devuelve mi catálogo para que otros peers lo consuman"""
    # Verificar autenticación (token o código de invitación)
    peer_token = request.headers.get('X-Peer-Token')
    peer_id = request.headers.get('X-Peer-Id')
    
    # Verificar contra lista de peers autorizados
    allowed = load_allowed_peers()
    
    is_authorized = False
    if peer_token:
        # Buscar si algún peer autorizado tiene este token
        for pid, pinfo in allowed.items():
            if pinfo.get('token') == peer_token:
                is_authorized = True
                break
    
    # En modo desarrollo, también permitir sin token (para pruebas)
    if not is_authorized and os.environ.get('FEDERATION_ALLOW_ALL'):
        is_authorized = True
    
    if not is_authorized:
        return jsonify({'error': 'Autenticación requerida. Token inválido.'}), 401
    
    catalog = get_catalog_for_sharing()
    catalog['shared_by'] = {
        'id': 'me',
        'name': 'Mi Biblioteca'
    }
    
    return jsonify(catalog)


@app.route('/api/federation/unified')
def federation_unified():
    """Devuelve el catálogo unificado: local + todos los peers"""
    # Catálogo local
    local_catalog = get_catalog_for_sharing()
    
    # Catálogos de peers
    peer_catalogs = []
    with peers_lock:
        for peer_id, cache in peers_cache.items():
            if cache.get('status') == 'online':
                peer_catalogs.append({
                    'peer_id': peer_id,
                    'peer_name': cache['config'].get('name', peer_id),
                    'peer_url': cache['config'].get('url'),
                    'items': cache['catalog'].get('items', []),
                    'total_videos': cache['catalog'].get('total_videos', 0),
                    'last_sync': cache.get('last_sync')
                })
    
    return jsonify({
        'local': {
            'name': 'Mi Biblioteca',
            'items': local_catalog['items'],
            'total_videos': local_catalog['total_videos'],
            'total_size': local_catalog['total_size']
        },
        'peers': peer_catalogs,
        'sources_count': 1 + len(peer_catalogs),
        'total_unified_videos': local_catalog['total_videos'] + sum(p['total_videos'] for p in peer_catalogs)
    })


@app.route('/api/federation/invite', methods=['POST'])
def create_invitation():
    """
    Crea una invitación simple con código corto.
    Tu amigo genera un código, te lo manda, y tú lo usas para conectarte.
    """
    data = request.json
    
    # Generar código corto y legible (ej: ABC-123-XYZ)
    def generate_invite_code():
        parts = []
        for _ in range(3):
            parts.append(''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(3)))
        return '-'.join(parts)
    
    invite_code = generate_invite_code()
    
    invitation = {
        'code': invite_code,
        'token': generate_peer_token(),  # Token interno para autenticación
        'name': data.get('name', 'Invitado'),
        'description': data.get('description', ''),
        'permissions': data.get('permissions', ['read_catalog', 'read_videos']),
        'created': datetime.now().isoformat(),
        'expires': (datetime.now() + timedelta(days=7)).isoformat(),
        'used': False,
        'used_by': None,
        'used_at': None
    }
    
    # Guardar invitación pendiente
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
        'expires': invitation['expires'],
        'message': 'Comparte este código con tu amigo para que se conecte a tu biblioteca'
    })


# ============================================
# RUTAS API - FEDERACIÓN (INVITACIONES SIMPLES)
# ============================================

@app.route('/api/federation/join', methods=['POST'])
def join_with_invite():
    """
    Usar un código de invitación para conectarse a un amigo.
    El usuario introduce: URL del amigo + Código de invitación
    """
    data = request.json
    
    peer_url = data.get('url', '').rstrip('/')
    invite_code = data.get('invite_code', '').upper().replace(' ', '-')
    my_name = data.get('my_name', 'Amigo')
    
    if not peer_url:
        return jsonify({'error': 'URL del amigo requerida'}), 400
    
    if not invite_code:
        return jsonify({'error': 'Código de invitación requerido'}), 400
    
    try:
        # Verificar el código con el servidor del amigo
        verify_url = f"{peer_url}/api/federation/verify-invite"
        response = requests.post(verify_url, json={
            'invite_code': invite_code,
            'peer_name': my_name
        }, timeout=10)
        
        if response.status_code != 200:
            error_msg = response.json().get('error', 'Código inválido o expirado')
            return jsonify({'error': error_msg}), 400
        
        invite_data = response.json()
        
        # El código es válido, nos ha dado un token de acceso
        peer_token = invite_data.get('access_token')
        peer_name = invite_data.get('peer_name', 'Amigo')
        my_assigned_id = invite_data.get('your_id')  # ID que nos asigna el peer
        
        # Guardar este peer en nuestra configuración
        peer_id = secrets.token_hex(8)
        
        peers = load_peers()
        peers[peer_id] = {
            'id': peer_id,
            'name': peer_name,
            'url': peer_url,
            'token': peer_token,  # Token que nos dio el amigo para autenticarnos
            'invite_code': invite_code,
            'my_id': my_assigned_id,  # Cómo nos conoce él
            'enabled': True,
            'created': datetime.now().isoformat()
        }
        
        save_peers(peers)
        
        # Sincronizar inmediatamente
        sync_peer(peer_id, peers[peer_id])
        
        return jsonify({
            'success': True,
            'peer_id': peer_id,
            'peer_name': peer_name,
            'message': f'Conectado exitosamente a {peer_name}'
        })
        
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'No se pudo conectar con el servidor del amigo. Verifica la URL.'}), 503
    except Exception as e:
        return jsonify({'error': f'Error conectando: {str(e)}'}), 500


@app.route('/api/federation/verify-invite', methods=['POST'])
def verify_invite():
    """
    Verifica un código de invitación y devuelve token de acceso.
    Llamado por el servidor del amigo cuando alguien quiere unirse.
    """
    data = request.json
    invite_code = data.get('invite_code', '').upper().replace(' ', '-')
    peer_name = data.get('peer_name', 'Invitado')
    
    invitations_file = PEERS_FILE.replace('.json', '.invitations.json')
    
    if not os.path.exists(invitations_file):
        return jsonify({'error': 'No hay invitaciones activas'}), 404
    
    with open(invitations_file, 'r') as f:
        invitations = json.load(f)
    
    if invite_code not in invitations:
        return jsonify({'error': 'Código de invitación inválido'}), 400
    
    invitation = invitations[invite_code]
    
    # Verificar expiración
    if datetime.now() > datetime.fromisoformat(invitation['expires']):
        return jsonify({'error': 'Código de invitación expirado'}), 400
    
    # Verificar si ya fue usado
    if invitation.get('used'):
        return jsonify({'error': 'Código de invitación ya fue usado'}), 400
    
    # Marcar como usado
    invitation['used'] = True
    invitation['used_by'] = peer_name
    invitation['used_at'] = datetime.now().isoformat()
    
    # Generar un ID único para este peer
    peer_id = secrets.token_hex(8)
    
    # Guardar en lista de peers autorizados
    save_allowed_peer(peer_id, {
        'name': peer_name,
        'token': invitation['token'],
        'invite_code': invite_code,
        'added_via_invite': True
    })
    
    # Guardar invitaciones actualizadas
    with open(invitations_file, 'w') as f:
        json.dump(invitations, f, indent=2)
    
    # Responder con token de acceso
    return jsonify({
        'success': True,
        'access_token': invitation['token'],
        'peer_name': invitation.get('name', 'Mi Biblioteca'),
        'your_id': peer_id,
        'permissions': invitation.get('permissions', ['read_catalog'])
    })


@app.route('/api/federation/my-invites', methods=['GET'])
def list_my_invites():
    """Lista las invitaciones que he generado"""
    invitations_file = PEERS_FILE.replace('.json', '.invitations.json')
    
    if not os.path.exists(invitations_file):
        return jsonify({'invites': []})
    
    with open(invitations_file, 'r') as f:
        invitations = json.load(f)
    
    # Filtrar solo las no expiradas
    active_invites = []
    for code, inv in invitations.items():
        is_expired = datetime.now() > datetime.fromisoformat(inv['expires'])
        active_invites.append({
            'code': code,
            'name': inv.get('name'),
            'description': inv.get('description'),
            'created': inv['created'],
            'expires': inv['expires'],
            'used': inv.get('used', False),
            'used_by': inv.get('used_by'),
            'expired': is_expired
        })
    
    return jsonify({'invites': active_invites})


# ============================================
# RUTAS API - FEDERACIÓN FASE 2 (JWT TOKENS)
# ============================================

@app.route('/api/federation/video-token', methods=['POST'])
def request_video_token():
    """
    Fase 2: Un peer solicita un token para ver un video específico.
    Este endpoint debe ser llamado por el backend del peer, no directamente por el frontend.
    """
    if not JWT_AVAILABLE:
        return jsonify({'error': 'JWT no disponible. Instala: pip install PyJWT'}), 501
    
    data = request.json
    video_path = data.get('video_path')
    peer_id = request.headers.get('X-Peer-Id')
    peer_token = request.headers.get('X-Peer-Token')
    
    if not video_path:
        return jsonify({'error': 'video_path requerido'}), 400
    
    # Verificar que el peer está autorizado
    if peer_id and peer_token:
        if not is_peer_allowed(peer_id, peer_token):
            return jsonify({'error': 'Peer no autorizado'}), 403
    
    # Verificar que el video existe
    full_path = Path(VIDEOS_BASE_DIR) / video_path
    try:
        full_path.relative_to(Path(VIDEOS_BASE_DIR))
    except ValueError:
        return jsonify({'error': 'Invalid video path'}), 403
    
    if not full_path.exists():
        return jsonify({'error': 'Video no encontrado'}), 404
    
    # Generar token JWT
    token = generate_video_token(video_path, peer_id)
    
    return jsonify({
        'token': token,
        'video_path': video_path,
        'expires_in': VIDEO_TOKEN_EXPIRY,
        'expires_at': (datetime.utcnow() + timedelta(seconds=VIDEO_TOKEN_EXPIRY)).isoformat()
    })


@app.route('/api/federation/authorize-peer', methods=['POST'])
def authorize_peer():
    """
    Autoriza a un peer a solicitar tokens de video.
    Esto se hace cuando aceptamos una invitación o queremos dar acceso manual.
    """
    data = request.json
    peer_id = data.get('peer_id')
    peer_name = data.get('peer_name', 'Peer')
    peer_token = data.get('peer_token')
    
    if not peer_id or not peer_token:
        return jsonify({'error': 'peer_id y peer_token requeridos'}), 400
    
    save_allowed_peer(peer_id, {
        'name': peer_name,
        'token': peer_token
    })
    
    return jsonify({
        'success': True,
        'peer_id': peer_id,
        'message': f'Peer {peer_name} autorizado para solicitar tokens de video'
    })


@app.route('/api/federation/peers', methods=['GET'])
def list_authorized_peers():
    """Lista los peers autorizados (para administración)"""
    allowed = load_allowed_peers()
    return jsonify(allowed)


@app.route('/api/peers/<peer_id>/video-url', methods=['POST'])
def get_peer_video_url(peer_id):
    """
    Fase 2: Frontend pide a SU backend que obtenga URL firmada para video de un peer.
    Este es el flujo completo:
    1. Frontend (tu app) pide a tu backend: "Quiero ver video X del peer Y"
    2. Tu backend pide token al backend del peer Y
    3. Tu backend devuelve al frontend: URL con token incluido
    4. Frontend reproduce directamente desde peer Y con el token
    """
    data = request.json
    video_path = data.get('video_path')
    
    if not video_path:
        return jsonify({'error': 'video_path requerido'}), 400
    
    # Cargar config del peer
    peers = load_peers()
    if peer_id not in peers:
        return jsonify({'error': 'Peer no encontrado'}), 404
    
    peer = peers[peer_id]
    
    try:
        # Solicitar token al peer remoto
        token_url = f"{peer['url']}/api/federation/video-token"
        headers = {
            'X-Peer-Id': peer.get('my_id', 'unknown'),
            'X-Peer-Token': peer.get('token', ''),
            'Content-Type': 'application/json'
        }
        payload = {'video_path': video_path}
        
        response = requests.post(token_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            token_data = response.json()
            
            # Construir URL completa con token
            video_url = f"{peer['url']}/videos/{video_path}?token={token_data['token']}"
            
            return jsonify({
                'success': True,
                'video_url': video_url,
                'expires_in': token_data.get('expires_in', VIDEO_TOKEN_EXPIRY),
                'peer_id': peer_id
            })
        else:
            error_data = response.json() if response.text else {'error': 'Unknown error'}
            return jsonify({
                'error': 'Error obteniendo token del peer',
                'peer_error': error_data,
                'status_code': response.status_code
            }), 502
            
    except Exception as e:
        return jsonify({'error': f'Error conectando con peer: {str(e)}'}), 503


# ============================================
# RUTAS ESTÁTICAS (REACT FRONTEND) - AL FINAL
# Estas deben ir al final para no capturar /api/* y /videos/*
# ============================================

@app.route('/')
def index():
    """Sirve la página principal (React app)"""
    if os.path.exists(os.path.join(STATIC_FOLDER, 'index.html')):
        return send_from_directory(STATIC_FOLDER, 'index.html')
    return jsonify({'status': '360° Viewer API', 'static_folder': STATIC_FOLDER})


@app.route('/<path:path>')
def serve_static(path):
    """Sirve archivos estáticos del frontend (SPA fallback)"""
    # No capturar rutas de API ni videos
    if path.startswith('api/') or path.startswith('videos/'):
        return jsonify({'error': 'Not found'}), 404
    
    file_path = os.path.join(STATIC_FOLDER, path)
    # Si el archivo existe, lo sirve
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return send_from_directory(STATIC_FOLDER, path)
    # Si no existe, devuelve index.html (SPA routing)
    if os.path.exists(os.path.join(STATIC_FOLDER, 'index.html')):
        return send_from_directory(STATIC_FOLDER, 'index.html')
    return jsonify({'error': 'Not found'}), 404


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0', help='Host (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8080, help='Puerto (default: 8080)')
    parser.add_argument('--videos', help='Directorio de videos (default: /videos o VIDEOS_PATH)')
    args = parser.parse_args()
    
    # Si se pasa --videos, actualizar VIDEOS_BASE_DIR
    if args.videos:
        VIDEOS_BASE_DIR = args.videos
        print(f"📁 Directorio base (argumento): {VIDEOS_BASE_DIR}")
    else:
        print(f"📁 Directorio base: {VIDEOS_BASE_DIR}")
    
    print(f"📚 Bibliotecas en: {LIBRARIES_FILE}")
    print(f"👥 Peers en: {PEERS_FILE}")
    print(f"🔄 Sync interval: {FEDERATION_SYNC_INTERVAL}s")
    print(f"🌐 Servidor en: http://{args.host}:{args.port}")
    
    # Iniciar worker de federación en segundo plano
    sync_thread = threading.Thread(target=federation_sync_worker, daemon=True)
    sync_thread.start()
    print("🤝 Federación: Worker de sincronización iniciado")
    
    # Sincronización inicial
    peers = load_peers()
    if peers:
        print(f"🔄 Sincronizando {len(peers)} peers...")
        for peer_id, config in peers.items():
            sync_peer(peer_id, config)
    
    app.run(host=args.host, port=args.port, debug=False)
