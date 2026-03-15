import { useState, useEffect, useCallback } from 'react';

const API_BASE = '/api';

export function useLibraries() {
  const [libraries, setLibraries] = useState({});
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

  useEffect(() => {
    fetchLibraries();
  }, [fetchLibraries]);

  // Navegar directorio
  const browseDirectory = useCallback(async (path = '') => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/browse?path=${encodeURIComponent(path)}`);
      const data = await response.json();
      
      if (data.error) {
        setError(data.error);
        return;
      }
      
      setItems(data.items);
      setBreadcrumbs(data.breadcrumbs);
      setCurrentPath(path);
    } catch (err) {
      setError('Error navegando directorio');
    } finally {
      setLoading(false);
    }
  }, []);

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

  return {
    libraries,
    currentPath,
    items,
    breadcrumbs,
    loading,
    error,
    browseDirectory,
    addLibrary,
    deleteLibrary
  };
}
