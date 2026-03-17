# 🎥 360° Video Viewer - P2P Federation Edition

Visor de videos 360° con **federación P2P** entre dispositivos. Comparte tu biblioteca de videos 360° de forma segura con amigos/familia usando invites de 16 caracteres.

## ✨ Características

### 🎬 Reproducción 360°
- ⚛️ **React 18** con Hooks
- 🎨 **Tailwind CSS** para estilos modernos
- ⚡ **Vite** para desarrollo rápido
- 🎬 **Reproductor 360°** con A-Frame
- 🎮 **Controles completos**: Play/Pause, Timeline, Volumen, VR

### 🌐 Federación P2P
- 🔗 **Conexión peer-to-peer** entre dispositivos
- 🎟️ **Invites seguros** (16 caracteres alfanuméricos)
- 🔐 **Autenticación JWT** (sin credenciales compartidas)
- 🎥 **Streaming directo** de videos entre peers
- 📁 **Navegación jerárquica** de carpetas

### 🔒 Seguridad
- ⏱️ **Rate limiting** (5 intentos/min para invites)
- 🎫 **Tokens obligatorios** para acceso a videos
- 🔒 **CORS dinámico** (solo orígenes de peers registrados)
- 🛡️ **Headers de seguridad** (HSTS, XSS protection)

## 📁 Estructura del Proyecto

```
360-viewer-app/
├── backend/                    # Flask API - Arquitectura Modular
│   ├── server.py              # Entry point (~30 líneas)
│   ├── app/                   # Paquete principal
│   │   ├── __init__.py        # Factory functions
│   │   ├── config.py          # Configuración centralizada
│   │   ├── models/            # Dataclasses
│   │   │   ├── peer.py        # Modelo Peer
│   │   │   └── invite.py      # Modelo Invite
│   │   ├── services/          # Lógica de negocio
│   │   │   ├── peer_service.py
│   │   │   ├── invite_service.py
│   │   │   └── video_service.py
│   │   ├── utils/             # Utilidades
│   │   │   ├── auth.py        # JWT (generate/verify)
│   │   │   ├── rate_limiter.py
│   │   │   └── cors.py        # CORS dinámico
│   │   └── routes/            # Blueprints Flask
│   │       ├── federation.py  # API P2P (puerto 8081)
│   │       └── web.py         # API Web (puerto 8080)
│   └── Dockerfile
├── frontend/                   # React + Vite + Tailwind
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.jsx    # Bibliotecas + Peers
│   │   │   ├── VideoPlayer.jsx
│   │   │   └── VideoControls.jsx
│   │   ├── hooks/
│   │   │   ├── useVideo.js
│   │   │   └── useLibraries.js
│   │   └── i18n/              # Internacionalización
│   │       └── locales/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🏗️ Arquitectura Dual-Puerto

```
┌─────────────────┐     ┌─────────────────┐
│   Web UI        │     │   Federación    │
│   Port 8080     │     │   Port 8081     │
├─────────────────┤     ├─────────────────┤
│ • Navegación    │     │ • Invites JWT   │
│ • Peers local   │     │ • Catalog sync  │
│ • Invites mgmt  │     │ • Video tokens  │
│ • Local videos  │     │ • CORS dinámico │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────┴──────┐
              │   Videos    │
              │  /videos    │
              └─────────────┘
```

## 🚀 Desarrollo Local

### Requisitos
- Node.js 18+
- Python 3.11+
- Docker (opcional)

### Opción 1: Desarrollo con Python directo

```bash
# 1. Backend

cd backend

# Crear entorno virtual (recomendado)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# o: venv\Scripts\activate  # Windows

# Instalar dependencias
pip install flask flask-cors pyjwt

# Crear directorio de datos
mkdir -p /tmp/360-data

# Arrancar servidor (modo desarrollo)
export VIDEOS_DIR="/ruta/a/tus/videos"
export PEERS_FILE="/tmp/360-data/.peers.json"
export DATA_DIR="/tmp/360-data"
export PORT=8080
export FEDERATION_PORT=8081

python server.py
```

El backend arranca **dos servidores**:
- 🎬 Web UI: http://localhost:8080
- 🌐 Federación: http://localhost:8081

### Opción 2: Desarrollo Frontend con backend real

```bash
# Terminal 1: Backend (como arriba)
cd backend
source venv/bin/activate
python server.py

# Terminal 2: Frontend
cd frontend
npm install

# Proxy al backend para evitar CORS
npm run dev
```

El frontend estará en http://localhost:5173 y proxyará las llamadas API al backend.

### Opción 3: Todo con Docker Compose

```bash
# Edita docker-compose.yml para apuntar a tus videos
volumes:
  - /ruta/a/tus/videos:/videos:ro
  - ./backend-data:/app/data

# Arrancar todo
docker-compose up --build

# Acceder:
# Web UI: http://localhost:8080
# Federación API: http://localhost:8081
```

## 🐳 Despliegue en Producción (TrueNAS/Docker)

### 1. Construir imagen

```bash
# Clonar o copiar proyecto
cd 360-viewer-app

# Construir imagen
docker build -t tu-usuario/360-viewer:latest .

# Subir a registry (opcional)
docker push tu-usuario/360-viewer:latest
```

### 2. Docker Compose (TrueNAS Scale)

```yaml
version: "3.8"
services:
  viewer:
    image: tu-usuario/360-viewer:latest
    container_name: 360-viewer
    ports:
      - "8080:8080"   # Web UI (localhost/Cloudflare)
      - "8081:8081"   # Federación P2P (internet)
    environment:
      - PORT=8080
      - FEDERATION_PORT=8081
      - JWT_SECRET=tu-clave-secreta-muy-larga-aqui
      - DATA_DIR=/app/data
    volumes:
      - /mnt/tu-pool/videos-360:/videos:ro
      - /mnt/tu-pool/360-data:/app/data
    restart: unless-stopped
```

### 3. Cloudflare Tunnel (opcional pero recomendado)

Para exponer la federación de forma segura:

```bash
# Instalar cloudflared
docker run -d \
  --name cloudflare-tunnel \
  cloudflare/cloudflared:latest tunnel --no-autoupdate run \
  --token TU_TOKEN_AQUI
```

Configura el tunnel para apuntar a `http://360-viewer:8081`

## 🎮 Uso

### 1. Configurar tu servidor

1. Abre la Web UI (http://localhost:8080)
2. Ve a la sección "Peers" en el sidebar
3. Genera un invite code

### 2. Conectar otro dispositivo

1. En el segundo dispositivo, abre la Web UI
2. Ve a "Peers" → "Add Peer"
3. Introduce el invite code de 16 caracteres
4. El peer se añade automáticamente

### 3. Ver videos remotos

1. Selecciona el peer en el sidebar
2. Navega por sus carpetas
3. Click en un video para reproducir
4. El video se transmite directamente del peer remoto

## 🔧 Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `PORT` | Puerto Web UI | `8080` |
| `FEDERATION_PORT` | Puerto P2P | `8081` |
| `VIDEOS_DIR` | Directorio de videos | `/videos` |
| `DATA_DIR` | Directorio de datos | `/app/data` |
| `PEERS_FILE` | Ruta archivo peers | `/app/data/.peers.json` |
| `JWT_SECRET` | Clave secreta JWT | *(hardcoded - cambiar!)* |
| `JWT_EXPIRY_DAYS` | Expiración tokens | `30` |
| `VIDEO_TOKEN_EXPIRY` | Expiración video tokens | `3600` (1h) |
| `RATE_LIMIT_MAX_INVITE` | Max intentos invite/min | `5` |
| `RATE_LIMIT_MAX_REQUESTS` | Max requests/min | `100` |

## 🔐 Seguridad

### Invites
- **16 caracteres** alfanuméricos (A-Z, 2-9, sin 0,O,I,L)
- ~10^28 combinaciones posibles
- Expiran en 7 días por defecto
- Uso único (se invalidan al usarse)

### Autenticación
- **JWT firmados** para peers
- **Video tokens** de 1 hora de duración
- Sin credenciales compartidas persistentes

### Rate Limiting
- 5 intentos/minuto para invites (anti fuerza bruta)
- 100 requests/minuto general (anti DoS)

### CORS
- Dinámico basado en peers registrados
- Solo orígenes conocidos permitidos
- Preflight validado

## 🧪 Testing

```bash
# Backend tests (futuro)
cd backend
pip install pytest pytest-flask
pytest

# Frontend tests
cd frontend
npm test
```

## 📝 API Endpoints

### Federación (Port 8081) - Requiere Auth

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/federation/verify-invite` | POST | Verificar invite code |
| `/api/federation/join` | POST | Unirse con invite |
| `/api/federation/catalog` | GET | Listar catálogo |
| `/api/federation/browse` | GET | Navegar carpetas |
| `/api/federation/video-token` | POST | Obtener token video |
| `/videos/<path>` | GET | Stream video (token requerido) |

### Web (Port 8080) - Local/Auth opcional

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/peers` | GET/POST | Listar/Añadir peers |
| `/api/peers/<id>/sync` | POST | Sincronizar con peer |
| `/api/peers/<id>/video-url` | POST | URL firmada video |
| `/api/peers/<id>/browse` | GET | Navegar peer remoto |
| `/api/invites` | GET/POST | Gestionar invites |
| `/api/videos` | GET | Listar videos locales |

## 🛠️ Stack Tecnológico

| Capa | Tecnología |
|------|------------|
| Frontend | React 18, Vite, Tailwind CSS, i18next, Lucide Icons |
| Backend | Flask, Flask-CORS, PyJWT |
| 360° | A-Frame |
| Auth | JWT (HS256) |
| Contenedor | Docker, multi-stage build |

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/nueva-funcionalidad`)
3. Commit (`git commit -am 'Añadir nueva funcionalidad'`)
4. Push (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📝 Licencia

MIT License - Ver [LICENSE](LICENSE) para detalles.

---

**Nota**: Este proyecto está en desarrollo activo. La API puede cambiar entre versiones.
