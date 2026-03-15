# 🎥 360° Video Viewer - React + Tailwind

Versión moderna con **React**, **Vite** y **Tailwind CSS**.

## ✨ Características

- ⚛️ **React 18** con Hooks
- 🎨 **Tailwind CSS** para estilos modernos
- ⚡ **Vite** para desarrollo rápido
- 📚 **Sistema de Bibliotecas** con navegación por carpetas
- 🎬 **Reproductor 360°** con A-Frame
- 🎮 **Controles completos**: Play/Pause, Timeline, Volumen
- 📱 **Responsive**: Sidebar colapsable
- 🐳 **Dockerizado** para TrueNAS Scale

## 📁 Estructura

```
360-viewer-react/
├── backend/           # Flask API (sin cambios)
│   ├── server.py
│   └── Dockerfile
├── frontend/          # React + Vite + Tailwind
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.jsx       # Bibliotecas + navegación
│   │   │   ├── VideoPlayer.jsx   # A-Frame 360°
│   │   │   └── VideoControls.jsx # Controles de reproducción
│   │   ├── hooks/
│   │   │   ├── useVideo.js       # Lógica del video
│   │   │   └── useLibraries.js   # API de bibliotecas
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   ├── tailwind.config.js
│   └── Dockerfile
└── docker-compose.yml
```

## 🚀 Desarrollo Local

### Requisitos
- Node.js 18+
- Python 3.11+

### 1. Backend
```bash
cd backend
pip install flask flask-cors
python server.py --videos "E:\proyects\360-viewer\videos"
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```

Abre: http://localhost:5173

## 🐳 Despliegue en TrueNAS Scale

```bash
# Edita docker-compose.yml y cambia la ruta de videos
volumes:
  - /mnt/tu-pool/videos-360:/videos:ro

# Despliega
docker-compose up -d
```

Accede a: http://tu-nas

## 🎮 Uso

### Bibliotecas
- Crea bibliotecas virtuales apuntando a carpetas específicas
- Ejemplo: `viajes/2024-japon`

### Navegación
- Click en carpetas para entrar
- Breadcrumbs para volver atrás
- Sidebar colapsable con botón ◀/▶

### Controles de Video
- **▶️/⏸️**: Play/Pausa
- **Timeline**: Arrastra para adelantar/atrasar
- **🔊**: Volumen con slider
- **VR**: Botón en esquina para gafas

## 🛠️ Tecnologías

| Capa | Tecnología |
|------|------------|
| Frontend | React 18, Vite, Tailwind CSS, Lucide Icons |
| Backend | Flask, Flask-CORS |
| 360° | A-Frame |
| Contenedor | Docker, Nginx |

## 📦 Construcción Manual

```bash
# Frontend
cd frontend
npm install
npm run build

# Backend
cd ../backend
docker build -t 360-viewer-backend .

# Todo
cd ..
docker-compose up --build -d
```

## 🔧 Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `VIDEOS_PATH` | Directorio de videos | `/videos` |
| `LIBRARIES_FILE` | JSON de bibliotecas | `/app/data/.libraries.json` |
| `FLASK_CORS` | Habilitar CORS | `false` |

## 📝 Licencia

MIT
