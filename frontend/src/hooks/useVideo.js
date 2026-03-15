import { useState, useEffect, useRef, useCallback } from 'react';

export function useVideo() {
  const videoRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  
  // Refs para controlar el comportamiento del seek
  const isSeekingRef = useRef(false);
  const shouldBePausedRef = useRef(false);
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
      console.log('Video event: play, isSeeking:', isSeekingRef.current, 'shouldBePaused:', shouldBePausedRef.current);
      
      // Si el video debería estar pausado (recién después de seek), forzar pausa
      if (shouldBePausedRef.current) {
        console.log('Forcing pause - should be paused');
        // Pequeño delay para evitar conflicto con el evento
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
    
    // Limpiar el flag de pausa forzada si el usuario quiere reproducir manualmente
    shouldBePausedRef.current = false;
    
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
    
    isSeekingRef.current = true;
    shouldBePausedRef.current = video.paused;
    
    console.log('Start seek, was paused:', shouldBePausedRef.current);
    
    // Pausar el video inmediatamente
    video.pause();
  }, []);

  const endSeek = useCallback((time) => {
    const video = videoRef.current;
    if (!video) return;
    
    console.log('End seek, setting time to:', time, 'should stay paused:', shouldBePausedRef.current);
    
    // Cambiar el tiempo
    video.currentTime = time;
    setCurrentTime(time);
    
    // El navegador va a intentar reproducir automáticamente
    // Mantener el flag shouldBePausedRef activo durante un tiempo
    isSeekingRef.current = false;
    
    if (shouldBePausedRef.current) {
      // Intentar pausar varias veces para asegurar
      const attempts = [0, 50, 100, 200, 300];
      attempts.forEach(delay => {
        setTimeout(() => {
          if (videoRef.current && !videoRef.current.paused) {
            console.log('Forcing pause, attempt at', delay, 'ms');
            videoRef.current.pause();
          }
        }, delay);
      });
      
      // Limpiar el flag después de un tiempo razonable
      seekTimeoutRef.current = setTimeout(() => {
        shouldBePausedRef.current = false;
        console.log('Cleared shouldBePaused flag');
      }, 500);
    } else {
      // Si debería reproducir, limpiar flag inmediatamente
      shouldBePausedRef.current = false;
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
    
    video.pause();
    video.src = src;
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
