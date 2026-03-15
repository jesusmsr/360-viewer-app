import { useState, useCallback, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { VideoPlayer } from './components/VideoPlayer';
import { VideoControls } from './components/VideoControls';
import { useVideo } from './hooks/useVideo';
import { useLibraries } from './hooks/useLibraries';
import { Menu } from 'lucide-react';

function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    return localStorage.getItem('sidebarCollapsed') === 'true';
  });
  const [currentLibrary, setCurrentLibrary] = useState(null);
  const [currentVideo, setCurrentVideo] = useState(null);
  const [currentVideoName, setCurrentVideoName] = useState('');
  const [libraryBasePath, setLibraryBasePath] = useState('');

  const {
    videoRef,
    isPlaying,
    currentTime,
    duration,
    volume,
    isMuted,
    togglePlay,
    seek,
    setVideoVolume,
    toggleMute,
    loadVideo
  } = useVideo();

  const {
    libraries,
    currentPath,
    items,
    breadcrumbs,
    loading,
    browseDirectory,
    addLibrary,
    deleteLibrary
  } = useLibraries();

  // Guardar estado del sidebar
  useEffect(() => {
    localStorage.setItem('sidebarCollapsed', sidebarCollapsed);
  }, [sidebarCollapsed]);

  // Cargar ruta base de biblioteca
  useEffect(() => {
    if (currentLibrary && libraries[currentLibrary]) {
      setLibraryBasePath(libraries[currentLibrary].path);
      browseDirectory(libraries[currentLibrary].path);
    } else {
      setLibraryBasePath('');
      browseDirectory('');
    }
  }, [currentLibrary, libraries]);

  const handleSelectLibrary = useCallback((id) => {
    setCurrentLibrary(id);
  }, []);

  const handleNavigate = useCallback((path) => {
    browseDirectory(path);
  }, [browseDirectory]);

  const handlePlayVideo = useCallback((videoItem) => {
    setCurrentVideo(videoItem.path);
    setCurrentVideoName(videoItem.name);
    loadVideo(videoItem.path);
  }, [loadVideo]);

  const handleAddLibrary = useCallback(async (name, path) => {
    const result = await addLibrary(name, path);
    return result;
  }, [addLibrary]);

  const handleDeleteLibrary = useCallback(async (id) => {
    if (confirm('¿Eliminar esta biblioteca?')) {
      await deleteLibrary(id);
      if (currentLibrary === id) {
        setCurrentLibrary(null);
      }
    }
  }, [deleteLibrary, currentLibrary]);

  return (
    <div className="flex h-screen bg-dark-900">
      {/* Sidebar */}
      <Sidebar
        libraries={libraries}
        currentLibrary={currentLibrary}
        onSelectLibrary={handleSelectLibrary}
        onAddLibrary={handleAddLibrary}
        onDeleteLibrary={handleDeleteLibrary}
        currentPath={currentPath}
        breadcrumbs={breadcrumbs}
        items={items}
        onNavigate={handleNavigate}
        onPlayVideo={handlePlayVideo}
        currentVideo={currentVideo}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      {/* Área de video */}
      <main className="flex-1 flex flex-col relative min-w-0 overflow-hidden">
        {/* Botón para mostrar sidebar cuando está colapsado */}
        {sidebarCollapsed && (
          <button
            onClick={() => setSidebarCollapsed(false)}
            className="absolute top-5 left-5 z-40 p-2.5 bg-dark-800/90 backdrop-blur border border-dark-600 rounded-lg hover:bg-dark-700 transition-colors"
            title="Mostrar bibliotecas"
          >
            <Menu size={20} />
          </button>
        )}

        {/* Reproductor */}
        <VideoPlayer
          videoRef={videoRef}
          currentVideo={currentVideo}
          currentVideoName={currentVideoName}
        />

        {/* Controles */}
        <VideoControls
          isPlaying={isPlaying}
          currentTime={currentTime}
          duration={duration}
          volume={volume}
          isMuted={isMuted}
          onTogglePlay={togglePlay}
          onSeek={seek}
          onVolumeChange={setVideoVolume}
          onToggleMute={toggleMute}
        />
      </main>
    </div>
  );
}

export default App;
