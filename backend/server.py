#!/usr/bin/env python3
"""
Servidor para 360° Video Viewer
Sistema de bibliotecas con navegación de carpetas
"""
from flask import Flask, send_from_directory, jsonify, request, send_file
from flask_cors import CORS
import os
from pathlib import Path
import json
from datetime import datetime

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


@app.route('/api/browse', methods=['GET'])
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
    args = parser.parse_args()
    
    print(f"📁 Directorio base: {VIDEOS_BASE_DIR}")
    print(f"📚 Bibliotecas en: {LIBRARIES_FILE}")
    print(f"🌐 Servidor en: http://{args.host}:{args.port}")
    
    app.run(host=args.host, port=args.port, debug=False)
