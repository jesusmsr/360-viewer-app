import { useEffect, useRef } from 'react';

export function VideoPlayer({ videoRef, currentVideo, currentVideoName }) {
  const containerRef = useRef(null);

  useEffect(() => {
    // Permitir play con click en el video (para navegadores que bloquean autoplay)
    const handleClick = () => {
      if (videoRef.current && videoRef.current.paused) {
        videoRef.current.play().catch(() => {});
      }
    };

    document.addEventListener('click', handleClick, { once: true });
    return () => document.removeEventListener('click', handleClick);
  }, [videoRef]);

  return (
    <div 
      ref={containerRef}
      className="flex-1 relative bg-black"
      style={{ 
        position: 'relative',
        overflow: 'hidden'
      }}
    >
      {/* A-Frame Scene - PRIMERO para que esté debajo de los overlays */}
      <a-scene 
        embedded 
        vr-mode-ui="enabled: true"
        renderer="antialias: true; colorManagement: true;"
        style={{ 
          width: '100%', 
          height: '100%',
          position: 'absolute',
          top: 0,
          left: 0,
        }}
      >
        <a-assets>
          <video 
            ref={videoRef}
            id="video360" 
            autoPlay 
            loop 
            crossOrigin="anonymous" 
            playsInline
            style={{ display: 'none' }}
          />
        </a-assets>

        <a-videosphere 
          src="#video360" 
          rotation="0 -90 0"
        />

        {/* Cámara con controles mejorados */}
        <a-entity 
          camera 
          look-controls="enabled: true; mouseEnabled: true; touchEnabled: true; reverseMouseDrag: false"
          wasd-controls="enabled: false"
          position="0 0 0"
        >
          <a-cursor 
            color="#FFFFFF" 
            fuse="false"
            raycaster="objects: .clickable"
            scale="0.5 0.5 0.5"
          />
        </a-entity>
      </a-scene>

      {/* Info del video - encima pero sin bloquear */}
      {currentVideo && (
        <div 
          className="absolute top-5 left-1/2 -translate-x-1/2 bg-black/70 backdrop-blur-sm px-5 py-2.5 rounded-full text-sm max-w-[50%] truncate"
          style={{ 
            zIndex: 100,
            pointerEvents: 'none',
            userSelect: 'none'
          }}
        >
          🎬 {currentVideoName || 'Reproduciendo...'}
        </div>
      )}

      {/* Instrucciones cuando no hay video */}
      {!currentVideo && (
        <div 
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-center text-gray-500"
          style={{ 
            zIndex: 100,
            pointerEvents: 'none',
            userSelect: 'none'
          }}
        >
          <div className="text-6xl mb-4 opacity-30">🎥</div>
          <p className="text-lg">Selecciona un video para reproducir</p>
          <p className="text-sm mt-2 opacity-70">Soporta videos 360° equirectangulares</p>
        </div>
      )}

      {/* Instrucciones flotantes */}
      <div 
        className="absolute bottom-24 left-1/2 -translate-x-1/2 bg-black/70 backdrop-blur-sm px-5 py-2.5 rounded-full text-xs text-gray-300 whitespace-nowrap"
        style={{ 
          zIndex: 100,
          pointerEvents: 'none',
          userSelect: 'none'
        }}
      >
        🖱️ Arrastra para rotar | 📱 Gira móvil | 🥽 VR para gafas
      </div>
    </div>
  );
}
