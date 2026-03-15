import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Play, Pause, Volume2, VolumeX } from 'lucide-react';

export function VideoControls({
  isPlaying,
  currentTime,
  duration,
  volume,
  isMuted,
  onTogglePlay,
  onStartSeek,
  onEndSeek,
  onVolumeChange,
  onToggleMute
}) {
  const { t } = useTranslation();
  const [isDragging, setIsDragging] = useState(false);
  const [dragValue, setDragValue] = useState(0);
  const sliderRef = useRef(null);

  const formatTime = (seconds) => {
    if (isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const progress = duration ? ((isDragging ? dragValue : currentTime) / duration) * 100 : 0;

  // Manejar inicio del arrastre
  const handleMouseDown = (e) => {
    e.preventDefault();
    
    // Iniciar el seek (esto pausará el video y guardará el estado)
    onStartSeek();
    
    setIsDragging(true);
    
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
    const time = (percentage / 100) * duration;
    setDragValue(time);
  };

  // Manejar movimiento durante el arrastre
  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e) => {
      if (!sliderRef.current) return;
      const rect = sliderRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
      const time = (percentage / 100) * duration;
      setDragValue(time);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      // Al soltar, finalizar el seek (aplicar tiempo y mantener pausado si es necesario)
      onEndSeek(dragValue);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragValue, duration, onEndSeek]);

  // Manejar click simple en la barra
  const handleClick = (e) => {
    if (isDragging) return;
    
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
    const time = (percentage / 100) * duration;
    
    // Click simple: iniciar seek, mover, finalizar seek
    onStartSeek();
    onEndSeek(time);
  };

  return (
    <div className="bg-gradient-to-t from-black/90 via-black/70 to-transparent px-5 py-4 flex items-center gap-4">
      {/* Play/Pause */}
      <button
        onClick={onTogglePlay}
        className="w-11 h-11 rounded-full bg-blue-600 hover:bg-blue-500 flex items-center justify-center transition-all hover:scale-105"
        title={isPlaying ? t('controls.pause') : t('controls.play')}
      >
        {isPlaying ? <Pause size={20} fill="white" /> : <Play size={20} fill="white" className="ml-0.5" />}
      </button>

      {/* Timeline */}
      <div className="flex-1 flex flex-col gap-1.5">
        <div 
          ref={sliderRef}
          onClick={handleClick}
          onMouseDown={handleMouseDown}
          className="relative h-5 flex items-center cursor-pointer group"
        >
          {/* Barra de fondo */}
          <div className="absolute w-full h-1.5 bg-gray-700 rounded-full overflow-hidden">
            {/* Barra de progreso */}
            <div 
              className="h-full bg-blue-500 rounded-full"
              style={{ width: `${progress}%` }}
            />
          </div>
          
          {/* Thumb (punto) */}
          <div 
            className="absolute w-3 h-3 bg-white rounded-full shadow-lg transform -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity"
            style={{ left: `${progress}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-400 font-mono">
          <span>{formatTime(isDragging ? dragValue : currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>
      </div>

      {/* Volume */}
      <div className="flex items-center gap-2">
        <button
          onClick={onToggleMute}
          className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          title={isMuted ? t('controls.unmute') : t('controls.mute')}
        >
          {isMuted || volume === 0 ? (
            <VolumeX size={20} />
          ) : volume < 0.5 ? (
            <Volume2 size={20} className="opacity-70" />
          ) : (
            <Volume2 size={20} />
            )}
        </button>
        <input
          type="range"
          min="0"
          max="100"
          value={isMuted ? 0 : volume * 100}
          onChange={(e) => onVolumeChange(e.target.value / 100)}
          className="volume w-20"
        />
      </div>
    </div>
  );
}
