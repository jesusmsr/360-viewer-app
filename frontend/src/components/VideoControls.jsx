import { Play, Pause, Volume2, VolumeX, Maximize } from 'lucide-react';

export function VideoControls({
  isPlaying,
  currentTime,
  duration,
  volume,
  isMuted,
  onTogglePlay,
  onSeek,
  onVolumeChange,
  onToggleMute
}) {
  const formatTime = (seconds) => {
    if (isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleTimelineChange = (e) => {
    const time = (e.target.value / 100) * duration;
    onSeek(time);
  };

  const progress = duration ? (currentTime / duration) * 100 : 0;

  return (
    <div className="bg-gradient-to-t from-black/90 via-black/70 to-transparent px-5 py-4 flex items-center gap-4">
      {/* Play/Pause */}
      <button
        onClick={onTogglePlay}
        className="w-11 h-11 rounded-full bg-blue-600 hover:bg-blue-500 flex items-center justify-center transition-all hover:scale-105"
        title={isPlaying ? 'Pausa' : 'Play'}
      >
        {isPlaying ? <Pause size={20} fill="white" /> : <Play size={20} fill="white" className="ml-0.5" />}
      </button>

      {/* Timeline */}
      <div className="flex-1 flex flex-col gap-1.5">
        <input
          type="range"
          min="0"
          max="100"
          value={progress}
          onChange={handleTimelineChange}
          className="w-full h-1.5"
        />
        <div className="flex justify-between text-xs text-gray-400 font-mono">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>
      </div>

      {/* Volume */}
      <div className="flex items-center gap-2">
        <button
          onClick={onToggleMute}
          className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          title={isMuted ? 'Activar sonido' : 'Silenciar'}
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
