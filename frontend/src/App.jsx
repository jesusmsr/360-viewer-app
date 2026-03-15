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
    loadVideo,
  } = useVideo();

  const {
    libraries,
    peers,
    selectedPeer,
    setSelectedPeer,
    currentPath,
    items,
    breadcrumbs,
    loading,
    browseDirectory,
    addLibrary,
    deleteLibrary,
    addPeer,
    removePeer,
    syncPeer,
    getVideoUrl,
    refreshPeers,
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
    setSelectedPeer('local'); // Volver a local al seleccionar biblioteca
  }, [setSelectedPeer]);

  const handleSelectPeer = useCallback((peerId) => {
    setSelectedPeer(peerId);
    setCurrentLibrary(null); // Limpiar biblioteca al seleccionar peer
    browseDirectory('', peerId); // Cargar items del peer
  }, [browseDirectory, setSelectedPeer]);

  const handleNavigate = useCallback(
    (path) => {
      browseDirectory(path);
    },
    [browseDirectory],
  );

  const handlePlayVideo = useCallback(
    async (videoItem) => {
      setCurrentVideo(videoItem.path);
      setCurrentVideoName(videoItem.name);
      
      // Fase 2: Si es video de peer, obtener URL firmada primero
      const peerId = videoItem.source || selectedPeer;
      
      if (peerId && peerId !== 'local') {
        // Video de peer - solicitar token
        console.log(`Solicitando token para video de peer ${peerId}:`, videoItem.path);
        const result = await getVideoUrl(videoItem.path, peerId);
        
        if (result.success) {
          console.log('Token obtenido, reproduciendo:', result.videoUrl);
          loadVideo(result.videoUrl);  // URL completa con token
        } else {
          console.error('Error obteniendo token:', result.error);
          alert(`Error: ${result.error}`);
        }
      } else {
        // Video local - reproducción directa
        loadVideo(videoItem.path);  // Sin prefijo, useVideo lo añade
      }
    },
    [loadVideo, getVideoUrl, selectedPeer],
  );

  const handleAddLibrary = useCallback(
    async (name, path) => {
      const result = await addLibrary(name, path);
      return result;
    },
    [addLibrary],
  );

  const handleDeleteLibrary = useCallback(
    async (id) => {
      if (confirm(t('confirm.deleteLibrary'))) {
        await deleteLibrary(id);
        if (currentLibrary === id) {
          setCurrentLibrary(null);
        }
      }
    },
    [deleteLibrary, currentLibrary, t],
  );

  // Handlers para peers (Fase 1 & 2)
  const handleAddPeer = useCallback(
    async (peerData) => {
      const result = await addPeer(peerData);
      return result;
    },
    [addPeer],
  );

  const handleRemovePeer = useCallback(
    async (peerId) => {
      if (confirm(t('confirm.deletePeer') || '¿Eliminar conexión con este amigo?')) {
        const result = await removePeer(peerId);
        if (result && selectedPeer === peerId) {
          setSelectedPeer('local');
        }
        return result;
      }
      return false;
    },
    [removePeer, selectedPeer, t],
  );

  const handleSyncPeer = useCallback(
    async (peerId) => {
      const result = await syncPeer(peerId);
      return result;
    },
    [syncPeer],
  );

  return (
    <div className='flex h-screen bg-dark-900'>
      {/* Sidebar */}
      <Sidebar
        libraries={libraries}
        currentLibrary={currentLibrary}
        onSelectLibrary={handleSelectLibrary}
        onAddLibrary={handleAddLibrary}
        onDeleteLibrary={handleDeleteLibrary}
        peers={peers}
        selectedPeer={selectedPeer}
        onSelectPeer={handleSelectPeer}
        onAddPeer={handleAddPeer}
        onRemovePeer={handleRemovePeer}
        onSyncPeer={handleSyncPeer}
        onRefreshPeers={refreshPeers}
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
      <main className='flex-1 flex flex-col relative min-w-0 overflow-hidden'>
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
