import { useState, useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Sidebar } from './components/Sidebar';
import { VideoPlayer } from './components/VideoPlayer';
import { VideoControls } from './components/VideoControls';
import { useVideo } from './hooks/useVideo';
import { useLibraries } from './hooks/useLibraries';

function App() {
  const { t } = useTranslation();
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
    startSeek,
    endSeek,
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
    if (confirm(t('confirm.deleteLibrary'))) {
      await deleteLibrary(id);
      if (currentLibrary === id) {
        setCurrentLibrary(null);
      }
    }
  }, [deleteLibrary, currentLibrary, t]);

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
          onStartSeek={startSeek}
          onEndSeek={endSeek}
          onVolumeChange={setVideoVolume}
          onToggleMute={toggleMute}
        />
      </main>
    </div>
  );
}

export default App;
