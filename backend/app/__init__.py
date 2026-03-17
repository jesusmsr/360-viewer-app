"""
360° Video Viewer - Backend Modular
"""
from .config import Config
from .routes import federation_bp, web_bp

__version__ = "2.0.0"


def create_web_app():
    """Crear app de Web UI (puerto 8080)."""
    from flask import Flask
    from flask_cors import CORS
    
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": ["http://localhost:8080", "http://localhost:3000"]}})
    app.register_blueprint(web_bp)
    return app


def create_federation_app():
    """Crear app de Federación (puerto 8081)."""
    from flask import Flask
    
    app = Flask('federation')
    app.register_blueprint(federation_bp)
    return app
