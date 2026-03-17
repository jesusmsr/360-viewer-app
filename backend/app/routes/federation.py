"""
Rutas de federación P2P (puerto 8081).
Protegidas por invites JWT.
"""
import secrets
from datetime import datetime

from flask import Blueprint, request, jsonify, abort

from app.config import Config
from app.models.peer import Peer
from app.services.peer_service import PeerService
from app.services.invite_service import InviteService
from app.services.video_service import VideoService
from app.utils.auth import generate_jwt, verify_jwt, generate_video_token, require_auth_header
from app.utils.rate_limiter import RateLimiter
from app.utils.cors import CORSManager

# Blueprint
federation_bp = Blueprint('federation', __name__)

# Rate limiters
invite_limiter = RateLimiter(Config.RATE_LIMIT_WINDOW)
request_limiter = RateLimiter(Config.RATE_LIMIT_WINDOW)
cors_manager = CORSManager()


@federation_bp.before_request
def before_request():
    """Middleware: rate limiting y CORS."""
    # Rate limiting general
    client_ip = request.remote_addr or 'unknown'
    allowed, retry_after = request_limiter.check(f"req:{client_ip}", Config.RATE_LIMIT_MAX_REQUESTS)
    
    if not allowed:
        return jsonify({'error': 'Rate limit exceeded', 'retry_after': retry_after}), 429
    
    # Preflight OPTIONS
    if request.method == 'OPTIONS':
        return handle_preflight()


def handle_preflight():
    """Manejar peticiones OPTIONS (preflight CORS)."""
    origin = request.headers.get('Origin', '*')
    
    if cors_manager.is_allowed(origin):
        response = jsonify({'status': 'ok'})
        cors_manager.add_cors_headers(response, origin)
        return response, 200
    
    return jsonify({'error': 'Origin not allowed'}), 403


@federation_bp.after_request
def after_request(response):
    """Añadir headers de seguridad."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # CORS dinámico
    origin = request.headers.get('Origin')
    if origin:
        cors_manager.add_cors_headers(response, origin)
    
    return response


def require_auth():
    """Middleware: requerir autenticación."""
    payload = require_auth_header(request)
    if not payload:
        return jsonify({'error': 'Autenticación requerida'}), 401
    
    request.peer_payload = payload
    return None


@federation_bp.route('/api/federation/verify-invite', methods=['POST'])
def verify_invite():
    """Verifica un invite y devuelve info del servidor."""
    # Rate limiting específico para invites
    client_ip = request.remote_addr or 'unknown'
    allowed, retry_after = invite_limiter.check(f"invite:{client_ip}", Config.RATE_LIMIT_MAX_INVITE)
    
    if not allowed:
        return jsonify({'error': 'Demasiados intentos', 'retry_after': retry_after}), 429
    
    data = request.json
    invite_code = data.get('invite_code', '').upper().replace(' ', '-')
    peer_name = data.get('peer_name', 'Invitado')
    
    invite = InviteService.get_invite(invite_code)
    
    if not invite:
        return jsonify({'error': 'Código inválido'}), 404
    
    if not invite.can_use():
        if invite.used:
            return jsonify({'error': 'Código ya usado'}), 410
        return jsonify({'error': 'Código expirado'}), 410
    
    # Obtener mi ID
    my_peers = PeerService.list_peers()
    my_id = my_peers[0].id if my_peers else 'server_' + secrets.token_hex(4)
    
    return jsonify({
        'valid': True,
        'peer_name': invite.name,
        'server_id': my_id,
        'server_name': 'Mi NAS'
    })


@federation_bp.route('/api/federation/join', methods=['POST'])
def join_with_invite():
    """Unirse usando invite. Genera JWT, NO guarda peer."""
    data = request.json
    invite_code = data.get('invite_code', '').upper().replace(' ', '-')
    peer_name = data.get('peer_name', 'Invitado')
    peer_id = data.get('my_id') or ('peer_' + secrets.token_hex(8))
    
    invite = InviteService.get_invite(invite_code)
    
    if not invite:
        return jsonify({'error': 'Código inválido'}), 404
    
    if not invite.can_use():
        if invite.used:
            return jsonify({'error': 'Código ya usado'}), 410
        return jsonify({'error': 'Código expirado'}), 410
    
    # Marcar como usado
    InviteService.use_invite(invite_code, peer_name)
    
    # Generar JWT
    access_token = generate_jwt(peer_id, peer_name, invite.permissions)
    
    # Obtener mi ID
    my_peers = PeerService.list_peers()
    my_id = my_peers[0].id if my_peers else 'server_' + secrets.token_hex(4)
    
    return jsonify({
        'success': True,
        'access_token': access_token,
        'peer_name': invite.name,
        'your_id': peer_id,
        'server_id': my_id,
        'server_name': 'Mi NAS'
    })


@federation_bp.route('/api/federation/catalog')
def federation_catalog():
    """Catálogo de videos disponibles."""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    catalog = VideoService.get_catalog()
    catalog['shared_by'] = {'id': 'me', 'name': 'Mi Biblioteca'}
    
    return jsonify(catalog)


@federation_bp.route('/api/federation/browse')
def federation_browse():
    """Navegación jerárquica de carpetas."""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    folder_path = request.args.get('path', '')
    result = VideoService.browse_folder(folder_path)
    
    return jsonify(result)


@federation_bp.route('/api/federation/video-token', methods=['POST'])
def request_video_token():
    """Solicitar token para ver un video."""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    data = request.json
    video_path = data.get('video_path')
    peer_id = request.peer_payload.get('peer_id', 'unknown')
    
    if not video_path:
        return jsonify({'error': 'video_path requerido'}), 400
    
    # Validar que el video existe
    video_info = VideoService.get_video_info(video_path)
    if not video_info:
        return jsonify({'error': 'Video no encontrado'}), 404
    
    token = generate_video_token(video_path, peer_id)
    
    return jsonify({
        'token': token,
        'expires_in': Config.VIDEO_TOKEN_EXPIRY
    })


@federation_bp.route('/videos/<path:filename>')
def serve_video_federation(filename):
    """Servir video con token obligatorio."""
    from app.utils.auth import verify_video_token
    
    # Token es OBLIGATORIO
    token = request.args.get('token')
    if not token:
        return jsonify({'error': 'Token requerido'}), 401
    
    payload = verify_video_token(token)
    if 'error' in payload:
        return jsonify({'error': payload['error']}), 401
    
    if payload.get('video_path') != filename:
        return jsonify({'error': 'Token no válido para este video'}), 403
    
    # Servir video con range support
    range_header = request.headers.get('Range')
    data, status, start, total_size = VideoService.serve_video(filename, range_header)
    
    if data is None:
        return jsonify({'error': 'Video no encontrado'}), 404
    
    response = federation_bp.make_response(data)
    response.status_code = status
    
    if status == 206:
        response.headers['Content-Range'] = f'bytes {start}-{start + len(data) - 1}/{total_size}'
        response.headers['Accept-Ranges'] = 'bytes'
    
    response.headers['Content-Type'] = 'video/mp4'
    
    return response


@federation_bp.route('/api/federation/invites', methods=['GET'])
def list_invites():
    """Listar invitaciones (solo administrador/local)."""
    # Esto debería estar protegido por IP o auth local
    # Por ahora, requerimos auth de peer
    auth_error = require_auth()
    if auth_error:
        # Permitir desde localhost sin auth
        if request.remote_addr not in ['127.0.0.1', 'localhost', '::1']:
            return auth_error
    
    invites = InviteService.list_invites()
    return jsonify({
        'invites': [inv.to_dict() for inv in invites]
    })


@federation_bp.route('/api/federation/invites', methods=['POST'])
def create_invite():
    """Crear nueva invitación."""
    data = request.json or {}
    name = data.get('name', 'Invitado')
    
    invite = InviteService.create_invite(name)
    
    return jsonify({
        'success': True,
        'invite': invite.to_dict()
    })
