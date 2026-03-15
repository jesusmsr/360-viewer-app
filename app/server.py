#!/usr/bin/env python3
"""
Servidor para 360° Video Viewer
Sistema de bibliotecas con navegación de carpetas
"""
from flask import Flask, send_from_directory, jsonify, request
import os
from pathlib import Path
import json

app = Flask(__name__)

# Configuración
VIDEOS_BASE_DIR = os.environ.get('VIDEOS_PATH', '/videos')
LIBRARIES_FILE = os.environ.get('LIBRARIES_FILE', '/app/.libraries.json')

# Extensiones de video soportadas
VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov', '.mkv', '.avi'}


def load_libraries():
    """Carga las bibliotecas guardadas"""
    if os.path.exists(LIBRARIES_FILE):
        try:
            with open(LIBRARIES_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_libraries(libraries):
    """Guarda las bibliotecas"""
    with open(LIBRARIES_FILE, 'w') as f:
        json.dump(libraries, f, indent=2)


def get_directory_contents(path):
    """Obtiene el contenido de un directorio (carpetas y videos)"""
    items = []
    
    if not os.path.exists(path):
        return items
    
    try:
        entries = sorted(os.listdir(path))
    except PermissionError:
        return items
    
    # Primero carpetas, luego videos
    folders = []
    videos = []
    
    for entry in entries:
        if entry.startswith('.'):
            continue
            
        full_path = os.path.join(path, entry)
        rel_path = os.path.relpath(full_path, VIDEOS_BASE_DIR)
        
        if os.path.isdir(full_path):
            folders.append({
                'name': entry,
                'type': 'folder',
                'path': rel_path,
                'item_count': len([f for f in os.listdir(full_path) if not f.startswith('.')])
            })
        else:
            ext = Path(entry).suffix.lower()
            if ext in VIDEO_EXTENSIONS:
                stat = os.stat(full_path)
                videos.append({
                    'name': entry,
                    'type': 'video',
                    'path': f'/videos/{rel_path}',
                    'size': stat.st_size,
                    'modified': stat.st_mtime,
                    'ext': ext
                })
    
    return folders + videos


@app.route('/')
def index():
    """Sirve la página principal"""
    return send_from_directory('.', 'index.html')


@app.route('/api/libraries', methods=['GET'])
def get_libraries():
    """Obtiene todas las bibliotecas configuradas"""
    libraries = load_libraries()
    return jsonify(libraries)


@app.route('/api/libraries', methods=['POST'])
def add_library():
    """Añade una nueva biblioteca"""
    data = request.json
    name = data.get('name', '').strip()
    path = data.get('path', '').strip()
    
    if not name or not path:
        return jsonify({'error': 'Nombre y ruta requeridos'}), 400
    
    # Sanitizar ruta (debe estar dentro de VIDEOS_BASE_DIR)
    full_path = os.path.join(VIDEOS_BASE_DIR, path.lstrip('/'))
    if not full_path.startswith(VIDEOS_BASE_DIR):
        return jsonify({'error': 'Ruta no válida'}), 400
    
    if not os.path.exists(full_path):
        return jsonify({'error': 'El directorio no existe'}), 404
    
    libraries = load_libraries()
    library_id = str(len(libraries) + 1)
    libraries[library_id] = {
        'id': library_id,
        'name': name,
        'path': path.lstrip('/'),
        'full_path': full_path
    }
    save_libraries(libraries)
    
    return jsonify(libraries[library_id])


@app.route('/api/libraries/<library_id>', methods=['DELETE'])
def delete_library(library_id):
    """Elimina una biblioteca"""
    libraries = load_libraries()
    if library_id in libraries:
        del libraries[library_id]
        save_libraries(libraries)
        return jsonify({'success': True})
    return jsonify({'error': 'Biblioteca no encontrada'}), 404


@app.route('/api/browse')
def browse_directory():
    """Navega por un directorio y devuelve su contenido"""
    path = request.args.get('path', '')
    
    # Sanitizar ruta
    full_path = os.path.join(VIDEOS_BASE_DIR, path.lstrip('/'))
    if not full_path.startswith(VIDEOS_BASE_DIR):
        return jsonify({'error': 'Ruta no válida'}), 400
    
    if not os.path.exists(full_path):
        return jsonify({'error': 'Directorio no encontrado'}), 404
    
    # Obtener breadcrumbs
    breadcrumbs = []
    rel_parts = path.strip('/').split('/') if path else []
    current = ''
    breadcrumbs.append({'name': '📁 Raíz', 'path': ''})
    for part in rel_parts:
        current = os.path.join(current, part) if current else part
        breadcrumbs.append({'name': part, 'path': current})
    
    contents = get_directory_contents(full_path)
    
    return jsonify({
        'path': path,
        'full_path': full_path,
        'breadcrumbs': breadcrumbs,
        'items': contents
    })


@app.route('/api/scan')
def scan_all_videos():
    """Escanea y devuelve todos los videos del directorio base"""
    videos = []
    
    if not os.path.exists(VIDEOS_BASE_DIR):
        return jsonify(videos)
    
    for root, dirs, files in os.walk(VIDEOS_BASE_DIR):
        # Ignorar directorios ocultos
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            if file.startswith('.'):
                continue
                
            ext = Path(file).suffix.lower()
            if ext in VIDEO_EXTENSIONS:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, VIDEOS_BASE_DIR)
                
                videos.append({
                    'name': file,
                    'path': f'/videos/{rel_path}',
                    'folder': os.path.dirname(rel_path) or 'Raíz',
                    'size': os.path.getsize(full_path),
                    'modified': os.path.getmtime(full_path)
                })
    
    videos.sort(key=lambda x: x['modified'], reverse=True)
    return jsonify(videos)


@app.route('/videos/<path:filename>')
def serve_video(filename):
    """Sirve los archivos de video"""
    return send_from_directory(VIDEOS_BASE_DIR, filename)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0', help='Host (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8080, help='Puerto (default: 8080)')
    parser.add_argument('--videos', default='/videos', help='Directorio base de videos')
    parser.add_argument('--libraries', default='/app/.libraries.json', help='Archivo de bibliotecas')
    args = parser.parse_args()
    
    VIDEOS_BASE_DIR = args.videos
    LIBRARIES_FILE = args.libraries
    
    print(f"📁 Directorio base: {VIDEOS_BASE_DIR}")
    print(f"📚 Bibliotecas en: {LIBRARIES_FILE}")
    print(f"🌐 Servidor en: http://{args.host}:{args.port}")
    
    app.run(host=args.host, port=args.port, debug=False)
