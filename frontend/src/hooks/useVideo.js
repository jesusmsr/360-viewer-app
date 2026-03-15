import { useState, useEffect, useRef, useCallback } from 'react';

// Detectar si estamos en desarrollo o producción
const VIDEO_BASE = import.meta.env.DEV ? 'http://localhost:8080/videos' : '/videos';

export function useVideo() {
  const videoRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  
  // Refs para controlar el comportamiento del seek
  // null = no estamos en seek, true = estaba reproduciendo, false = estaba pausado
  const wasPlayingBeforeSeekRef = useRef(null);
  const seekTimeoutRef = useRef(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime);
    };

    const handleLoadedMetadata = () => {
      setDuration(video.duration);
    };

    const handlePlay = () => {
      console.log('Video event: play, wasPlayingBeforeSeek:', wasPlayingBeforeSeekRef.current);
      
      // Solo interceptar si acabamos de hacer seek y el video estaba pausado
      // wasPlayingBeforeSeekRef === false significa "estaba pausado antes del seek"
      if (wasPlayingBeforeSeekRef.current === false) {
        console.log('Forcing pause - was paused before seek');
        // Pequeño delay para asegurar que se ejecuta después del play automático
        setTimeout(() => {
          if (videoRef.current && !videoRef.current.paused) {
            videoRef.current.pause();
          }
        }, 0);
        return;
      }
      
      setIsPlaying(true);
    };
    
    const handlePause = () => {
      console.log('Video event: pause');
      setIsPlaying(false);
    };
    
    const handleEnded = () => setIsPlaying(false);

    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    video.addEventListener('ended', handleEnded);

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
      video.removeEventListener('ended', handleEnded);
      
      if (seekTimeoutRef.current) {
        clearTimeout(seekTimeoutRef.current);
      }
    };
  }, []);

  // Keyboard controls - Space para toggle play/pause
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        return;
      }
      
      if (e.code === 'Space') {
        e.preventDefault();
        togglePlay();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const togglePlay = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    
    if (video.paused) {
      video.play().catch(() => {});
    } else {
      video.pause();
    }
  }, []);

  const startSeek = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    
    // Limpiar timeout anterior si existe
    if (seekTimeoutRef.current) {
      clearTimeout(seekTimeoutRef.current);
    }
    
    // Guardar si estaba reproduciendo ANTES de pausar (true/false)
    wasPlayingBeforeSeekRef.current = !video.paused;
    
    console.log('Start seek, was playing:', wasPlayingBeforeSeekRef.current);
    
    // Pausar el video durante el arrastre
    video.pause();
  }, []);

  const endSeek = useCallback((time) => {
    const video = videoRef.current;
    if (!video) return;
    
    const shouldPlay = wasPlayingBeforeSeekRef.current;
    console.log('End seek, setting time to:', time, 'was playing:', shouldPlay);
    
    // Cambiar el tiempo
    video.currentTime = time;
    setCurrentTime(time);
    
    if (shouldPlay === true) {
      // Si estaba reproduciendo, reproducir de nuevo
      seekTimeoutRef.current = setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.play().catch(() => {});
        }
        // Limpiar flag después de reproducir
        wasPlayingBeforeSeekRef.current = null;
      }, 50);
    } else if (shouldPlay === false) {
      // Si estaba pausado, mantener pausado
      // El navegador intentará reproducir automáticamente, lo interceptamos en handlePlay
      // Pero también forzamos pausa aquí por si acaso
      seekTimeoutRef.current = setTimeout(() => {
        if (videoRef.current && !videoRef.current.paused) {
          console.log('Forcing pause after seek');
          videoRef.current.pause();
        }
      }, 50);
      
      // Mantener el flag durante 300ms para interceptar el play automático del navegador
      seekTimeoutRef.current = setTimeout(() => {
        wasPlayingBeforeSeekRef.current = null;
        console.log('Cleared seek flag');
      }, 300);
    }
  }, []);

  const setVideoVolume = useCallback((vol) => {
    const video = videoRef.current;
    if (!video) return;
    video.volume = vol;
    setVolume(vol);
    if (vol > 0 && video.muted) {
      video.muted = false;
      setIsMuted(false);
    }
  }, []);

  const toggleMute = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    video.muted = !video.muted;
    setIsMuted(video.muted);
  }, []);

  const loadVideo = useCallback((src) => {
    const video = videoRef.current;
    if (!video) return;
    
    // Resetear el flag de seek al cargar nuevo video
    wasPlayingBeforeSeekRef.current = null;
    if (seekTimeoutRef.current) {
      clearTimeout(seekTimeoutRef.current);
    }
    
    // Construir URL completa del video
    const videoUrl = src.startsWith('http') ? src : `${VIDEO_BASE}/${src}`;
    console.log('Loading video:', videoUrl);
    
    video.pause();
    video.src = videoUrl;
    video.load();
    
    video.oncanplay = () => {
      video.play().catch(() => {});
    };
  }, []);

  return {
    videoRef,
    isPlaying,
    currentTime,
    duration,
    volume,
    isMuted,
    togglePlay,
    startSeek,
    endSeek,
    setVideoVolume,
    toggleMute,
    loadVideo
  };
}
