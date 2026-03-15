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
    """Sirve archivos de video"""
    video_path = Path(VIDEOS_BASE_DIR) / filename
    
    # Security check
    try:
        video_path.relative_to(Path(VIDEOS_BASE_DIR))
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 403
    
    if not video_path.exists():
        return jsonify({'error': 'Video not found'}), 404
    
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
    # Verificar autenticación
    peer_token = request.headers.get('X-Peer-Token')
    peer_id = request.headers.get('X-Peer-Id')
    
    # En Fase 1: aceptamos cualquier token no vacío (se puede mejorar)
    # Idealmente verificaríamos contra una lista de peers que nos han dado permiso
    if not peer_token:
        return jsonify({'error': 'Autenticación requerida'}), 401
    
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
    """Crea una invitación para que alguien se conecte a mí"""
    data = request.json
    
    invitation = {
        'token': generate_peer_token(),
        'name': data.get('name', 'Invitado'),
        'permissions': data.get('permissions', ['read_catalog']),
        'created': datetime.now().isoformat(),
        'expires': (datetime.now() + timedelta(days=7)).isoformat()
    }
    
    # Guardar invitación pendiente
    invitations_file = PEERS_FILE.replace('.json', '.invitations.json')
    invitations = {}
    if os.path.exists(invitations_file):
        with open(invitations_file, 'r') as f:
            invitations = json.load(f)
    
    invitations[invitation['token']] = invitation
    
    os.makedirs(os.path.dirname(invitations_file), exist_ok=True)
    with open(invitations_file, 'w') as f:
        json.dump(invitations, f, indent=2)
    
    return jsonify({
        'invitation_token': invitation['token'],
        'expires': invitation['expires'],
        'invite_url': f"/api/federation/join?token={invitation['token']}"
    })


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
