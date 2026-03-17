import { useState, useEffect, useCallback } from 'react';

const API_BASE = '/api';

export function useLibraries() {
  const [libraries, setLibraries] = useState({});
  const [peers, setPeers] = useState({});
  const [selectedPeer, setSelectedPeer] = useState('local'); // 'local' o peer_id
  const [currentPath, setCurrentPath] = useState('');
  const [items, setItems] = useState([]);
  const [breadcrumbs, setBreadcrumbs] = useState([{ name: '📁 Raíz', path: '' }]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Cargar bibliotecas
  const fetchLibraries = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/libraries`);
      const data = await response.json();
      setLibraries(data);
    } catch (err) {
      setError('Error cargando bibliotecas');
    }
  }, []);

  // Cargar peers (amigos conectados)
  const fetchPeers = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/peers`);
      const data = await response.json();
      setPeers(data);
    } catch (err) {
      console.error('Error cargando peers:', err);
    }
  }, []);

  useEffect(() => {
    fetchLibraries();
    fetchPeers();
    // Refrescar peers cada 30 segundos
    const interval = setInterval(fetchPeers, 30000);
    return () => clearInterval(interval);
  }, [fetchLibraries, fetchPeers]);

  // Navegar directorio (local o de un peer)
  const browseDirectory = useCallback(async (path = '', peerId = null) => {
    setLoading(true);
    const targetPeer = peerId || selectedPeer;
    
    try {
      if (targetPeer === 'local') {
        // Catálogo local
        const response = await fetch(`${API_BASE}/browse?path=${encodeURIComponent(path)}`);
        const data = await response.json();
        
        if (data.error) {
          setError(data.error);
          return;
        }
        
        setItems(data.items);
        setBreadcrumbs(data.breadcrumbs);
      } else {
        // Catálogo de un peer - usar browse jerárquico
        const response = await fetch(
          `${API_BASE}/peers/${targetPeer}/browse?path=${encodeURIComponent(path)}`
        );
        const data = await response.json();
        
        if (!response.ok || data.error) {
          setError(data.error || 'Error cargando peer');
          setItems([]);
          return;
        }
        
        // Marcar items como del peer
        const peerItems = data.items.map(item => ({
          ...item,
          source: targetPeer
        }));
        
        setItems(peerItems);
        
        // Actualizar breadcrumbs
        if (path === '') {
          // Raíz del peer
          const peerInfo = peers[targetPeer];
          setBreadcrumbs([{ name: `📁 ${peerInfo?.name || 'Invitado'}`, path: '' }]);
        } else {
          // Dentro de una carpeta - construir breadcrumbs
          const parts = path.split('/').filter(p => p);
          const newBreadcrumbs = [
            { name: `📁 ${peers[targetPeer]?.name || 'Invitado'}`, path: '' }
          ];
          
          let currentPath = '';
          for (const part of parts) {
            currentPath = currentPath ? `${currentPath}/${part}` : part;
            newBreadcrumbs.push({ name: part, path: currentPath });
          }
          
          setBreadcrumbs(newBreadcrumbs);
        }
      }
      
      setCurrentPath(path);
      setSelectedPeer(targetPeer);
    } catch (err) {
      setError('Error navegando directorio');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [selectedPeer, peers]);

  // Añadir un peer (conectar con amigo)
  const addPeer = useCallback(async (peerData) => {
    try {
      const response = await fetch(`${API_BASE}/peers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(peerData)
      });
      
      if (response.ok) {
        await fetchPeers();
        return { success: true };
      } else {
        const error = await response.json();
        return { success: false, error: error.error };
      }
    } catch (err) {
      return { success: false, error: 'Error de conexión' };
    }
  }, [fetchPeers]);

  // Eliminar un peer
  const removePeer = useCallback(async (peerId) => {
    try {
      const response = await fetch(`${API_BASE}/peers/${peerId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        await fetchPeers();
        if (selectedPeer === peerId) {
          setSelectedPeer('local');
        }
        return true;
      }
      return false;
    } catch (err) {
      return false;
    }
  }, [fetchPeers, selectedPeer]);

  // Forzar sincronización de un peer
  const syncPeer = useCallback(async (peerId) => {
    try {
      const response = await fetch(`${API_BASE}/peers/${peerId}/sync`, {
        method: 'POST'
      });
      
      if (response.ok) {
        await fetchPeers();
        return { success: true };
      }
      return { success: false };
    } catch (err) {
      return { success: false, error: err.message };
    }
  }, [fetchPeers]);

  // Añadir biblioteca
  const addLibrary = useCallback(async (name, path) => {
    try {
      const response = await fetch(`${API_BASE}/libraries`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, path })
      });
      
      if (response.ok) {
        await fetchLibraries();
        return { success: true };
      } else {
        const error = await response.json();
        return { success: false, error: error.error };
      }
    } catch (err) {
      return { success: false, error: 'Error de conexión' };
    }
  }, [fetchLibraries]);

  // Eliminar biblioteca
  const deleteLibrary = useCallback(async (id) => {
    try {
      const response = await fetch(`${API_BASE}/libraries/${id}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        await fetchLibraries();
        return true;
      }
      return false;
    } catch (err) {
      return false;
    }
  }, [fetchLibraries]);

  // FASE 2: Obtener URL de video (local o con token de peer)
  const getVideoUrl = useCallback(async (videoPath, peerId = 'local') => {
    if (peerId === 'local') {
      // Video local - URL directa
      return {
        success: true,
        videoUrl: `${API_BASE}/videos/${encodeURIComponent(videoPath)}`,
        isLocal: true
      };
    }
    
    // Video de peer - Solicitar token a nuestro backend
    try {
      const response = await fetch(`${API_BASE}/peers/${peerId}/video-url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_path: videoPath })
      });
      
      if (response.ok) {
        const data = await response.json();
        return {
          success: true,
          videoUrl: data.url,
          expiresIn: data.expires_in,
          isLocal: false
        };
      } else {
        const error = await response.json();
        return {
          success: false,
          error: error.error || 'Error obteniendo token de video'
        };
      }
    } catch (err) {
      return {
        success: false,
        error: 'Error de conexión solicitando token'
      };
    }
  }, []);

  return {
    libraries,
    peers,
    selectedPeer,
    setSelectedPeer,
    currentPath,
    items,
    breadcrumbs,
    loading,
    error,
    browseDirectory,
    addLibrary,
    deleteLibrary,
    addPeer,
    removePeer,
    syncPeer,
    refreshPeers: fetchPeers,
    getVideoUrl  // Fase 2: función para obtener URLs firmadas
  };
}
