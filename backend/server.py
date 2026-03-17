#!/usr/bin/env python3
"""
360° Video Viewer - Servidor Modular
Puerto 8080: Web UI (localhost only)
Puerto 8081: Federación P2P (protegida por invites JWT)
"""

import threading
import logging

from app import create_web_app, create_federation_app
from app.config import Config


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear ambas apps
    web_app = create_web_app()
    fed_app = create_federation_app()
    
    # Iniciar servidor de federación en thread separado
    fed_thread = threading.Thread(
        target=lambda: fed_app.run(
            host='0.0.0.0',
            port=Config.FEDERATION_PORT,
            debug=False,
            threaded=True
        )
    )
    fed_thread.daemon = True
    fed_thread.start()
    
    logging.info(f"🌐 Federación iniciada en puerto {Config.FEDERATION_PORT}")
    
    # Iniciar servidor web (bloqueante)
    logging.info(f"🎬 Web UI iniciada en puerto {Config.WEB_PORT}")
    web_app.run(
        host='0.0.0.0',
        port=Config.WEB_PORT,
        debug=False,
        threaded=True
    )
