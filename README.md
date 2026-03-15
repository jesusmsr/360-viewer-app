# 🎥 360° Video Viewer

Aplicación web ligera para visualizar videos 360° con **sistema de bibliotecas** y navegación por carpetas.

## ✨ Características

- ✅ **Sistema de Bibliotecas**: Crea bibliotecas virtuales apuntando a carpetas específicas
- ✅ **Navegación por Carpetas**: Explora tu colección como un explorador de archivos
- ✅ **Reproducción 360°**: Videos equirectangulares con controles intuitivos
- ✅ **Múltiples formatos**: MP4, WebM, MOV, MKV, AVI
- ✅ **VR Ready**: Modo VR para gafas compatibles (WebXR)
- ✅ **Dockerizado**: Listo para TrueNAS Scale

## 📁 Sistema de Bibliotecas

En lugar de mostrar todos los videos mezclados, organiza tu contenido:

1. **Añade bibliotecas** apuntando a subcarpetas específicas
2. **Navega** por carpetas con breadcrumbs
3. **Visualiza** videos con miniaturas de carpeta

Ejemplo de estructura:
```
/videos
├── viajes/
│   ├── 2023-italia/
│   ├── 2024-japon/
│   └── playa-360.mp4
├── eventos/
│   ├── boda/
│   └── cumpleaños/
└── drone/
    └── montanas-360.mp4
```

## 🚀 Instalación en TrueNAS Scale

### Método 1: Docker Compose (Recomendado)

1. **Edita el `docker-compose.yml`** y cambia la ruta de tus videos:
   ```yaml
   volumes:
     - /mnt/tu-pool/videos-360:/videos:ro
   ```

2. **Despliega:**
   ```bash
   docker-compose up -d
   ```

### Método 2: TrueNAS Scale Apps (Custom App)

1. Ve a **Apps** → **Discover Apps** → **Custom App**

2. Configura:
   - **Application Name:** `360-viewer`
   - **Image:** `360-viewer:latest` (o constrúyela primero)
   - **Container Port:** 8080
   - **Host Port:** 8080

3. **Storage**:
   - **Host Path:** `/mnt/tu-pool/videos-360`
   - **Mount Path:** `/videos`
   - **Read Only:** ✅
   
   - **Host Path:** `/mnt/tu-pool/app-data/360-viewer`
   - **Mount Path:** `/app/data`
   - **Read Only:** ❌ (para persistir bibliotecas)

4. **Environment Variables**:
   - `VIDEOS_PATH` = `/videos`
   - `LIBRARIES_FILE` = `/app/data/.libraries.json`

### Método 3: Script de despliegue

```bash
./deploy-truenas.sh /mnt/tu-pool/videos-360 8080
```

## 🎮 Uso

### 1. Crear Bibliotecas

1. Haz clic en **"Añadir biblioteca"**
2. Pon un nombre descriptivo: *"Viajes 2024"*
3. Escribe la ruta relativa: `viajes/2024-japon`
4. ¡Listo! La biblioteca aparece en el sidebar

### 2. Navegar y Reproducir

- **Carpetas**: Doble clic para entrar
- **Breadcrumbs**: Navega hacia atrás fácilmente
- **Videos**: Click para reproducir en 360°

### 3. Controles 360°

| Dispositivo | Control |
|-------------|---------|
| **Desktop** | Click y arrastra |
| **Móvil** | Gira el dispositivo o desliza |
| **VR** | Botón VR (esquina) para gafas |

## 📂 Estructura del Proyecto

```
360-viewer/
├── app/
│   ├── index.html          # UI con navegación de bibliotecas
│   └── server.py           # API: bibliotecas + navegación
├── Dockerfile              # Imagen Docker
├── docker-compose.yml      # Despliegue con volúmenes
├── deploy-truenas.sh       # Script automático
└── README.md
```

## 🔧 API Endpoints

- `GET /api/libraries` - Lista bibliotecas
- `POST /api/libraries` - Crea biblioteca (`{name, path}`)
- `DELETE /api/libraries/{id}` - Elimina biblioteca
- `GET /api/browse?path=` - Navega directorios
- `GET /videos/{ruta}` - Sirve archivos de video

## 🐛 Solución de Problemas

### No aparecen carpetas
- Verifica que el directorio `/videos` esté montado correctamente
- Revisa permisos de lectura: `chmod -R 755 /mnt/tu-pool/videos-360`

### El video no carga
- Asegúrate de que es un video **equirectangular 360°**
- Formatos soportados: MP4, WebM, MOV, MKV, AVI
- Verifica que el archivo no esté corrupto

### Las bibliotecas no se guardan
- El volumen `/app/data` debe tener permisos de escritura
- Verifica que `LIBRARIES_FILE` apunte a `/app/data/.libraries.json`

## 💡 Tips

- **Organiza por temas**: Crea bibliotecas para viajes, eventos, drone...
- **Usa nombres claros**: Facilita encontrar contenido
- **Estructura anidada**: Carpetas dentro de carpetas para organizar
- **Sin límite**: Crea todas las bibliotecas que necesites

## 📱 Compatibilidad

- Chrome/Edge/Firefox/Safari modernos
- iOS Safari (con interacción para autoplay)
- Android Chrome
- Gafas VR con WebXR (Oculus, Quest, etc.)

## 📜 Licencia

MIT - Uso libre para proyectos personales
