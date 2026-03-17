"""
Rutas de la aplicación.
"""
from .federation import federation_bp
from .web import web_bp

__all__ = ['federation_bp', 'web_bp']
