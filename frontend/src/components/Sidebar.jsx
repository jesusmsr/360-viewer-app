import { useState } from 'react';
import { Folder, FolderOpen, Plus, X, ChevronLeft, ChevronRight } from 'lucide-react';

export function Sidebar({ 
  libraries, 
  currentLibrary, 
  onSelectLibrary, 
  onAddLibrary, 
  onDeleteLibrary,
  currentPath,
  breadcrumbs,
  items,
  onNavigate,
  onPlayVideo,
  currentVideo,
  collapsed,
  onToggleCollapse
}) {
  const [showModal, setShowModal] = useState(false);
  const [newLibName, setNewLibName] = useState('');
  const [newLibPath, setNewLibPath] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (newLibName && newLibPath) {
      onAddLibrary(newLibName, newLibPath);
      setNewLibName('');
      setNewLibPath('');
      setShowModal(false);
    }
  };

  return (
    <>
      {/* Sidebar Container */}
      <div className={`relative flex transition-all duration-300 ${collapsed ? 'w-0' : 'w-80'}`}>
        {/* Sidebar Content */}
        <aside className={`bg-dark-800 border-r border-dark-600 flex flex-col h-full overflow-hidden transition-all duration-300 ${collapsed ? 'w-0 opacity-0' : 'w-80 opacity-100'}`}>
          <div className="p-5 border-b border-dark-600 min-w-[320px]">
            <h1 className="text-xl font-semibold mb-1">🎥 360° Viewer</h1>
            <p className="text-sm text-gray-400">Bibliotecas de video</p>
          </div>
          
          {/* Bibliotecas */}
          <div className="p-4 border-b border-dark-600 min-w-[320px]">
            <p className="text-xs uppercase text-gray-500 mb-3 tracking-wider">Mis Bibliotecas</p>
            <div className="space-y-1">
              {/* Opción Raíz */}
              <button
                onClick={() => onSelectLibrary(null)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                  !currentLibrary ? 'bg-blue-500/20 text-blue-400' : 'hover:bg-white/5'
                }`}
              >
                <FolderOpen size={20} />
                <span className="flex-1 text-left text-sm">Todas las carpetas</span>
              </button>
              
              {/* Bibliotecas guardadas */}
              {Object.entries(libraries).map(([id, lib]) => (
                <div key={id} className="group relative">
                  <button
                    onClick={() => onSelectLibrary(id)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                      currentLibrary === id ? 'bg-blue-500/20 text-blue-400' : 'hover:bg-white/5'
                    }`}
                  >
                    <Folder size={20} />
                    <span className="flex-1 text-left text-sm truncate">{lib.name}</span>
                  </button>
                  <button
                    onClick={() => onDeleteLibrary(id)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 p-1.5 rounded text-red-400 hover:bg-red-500/20 transition-all"
                    title="Eliminar"
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
            </div>
            
            <button
              onClick={() => setShowModal(true)}
              className="w-full mt-3 py-2.5 border border-dashed border-gray-600 rounded-lg text-gray-400 hover:border-gray-500 hover:text-gray-300 hover:bg-white/5 transition-all flex items-center justify-center gap-2 text-sm"
            >
              <Plus size={16} />
              Añadir biblioteca
            </button>
          </div>
          
          {/* Navegación de carpetas */}
          <div className="flex-1 overflow-y-auto p-4 min-w-[320px]">
            {/* Breadcrumbs */}
            <div className="flex items-center flex-wrap gap-1 mb-4 p-2.5 bg-white/5 rounded-lg text-sm">
              {breadcrumbs.map((crumb, idx) => (
                <span key={idx} className="flex items-center">
                  {idx > 0 && <span className="text-gray-600 mx-1">›</span>}
                  <button
                    onClick={() => onNavigate(crumb.path)}
                    className={`hover:text-white transition-colors ${
                      idx === breadcrumbs.length - 1 ? 'text-white font-medium' : 'text-gray-400'
                    }`}
                  >
                    {crumb.name}
                  </button>
                </span>
              ))}
            </div>
            
            {/* Grid de items */}
            <div className="grid grid-cols-3 gap-2">
              {items.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => item.type === 'folder' ? onNavigate(item.path) : onPlayVideo(item)}
                  className={`aspect-square flex flex-col items-center justify-center p-3 rounded-xl transition-all hover:bg-white/10 hover:-translate-y-0.5 ${
                    item.type === 'video' && currentVideo === item.path 
                      ? 'bg-green-500/20 border-2 border-green-500/50' 
                      : 'bg-white/5 border-2 border-transparent'
                  }`}
                >
                  <span className="text-3xl mb-1">
                    {item.type === 'folder' ? '📁' : '🎬'}
                  </span>
                  <span className="text-xs text-center leading-tight line-clamp-2 overflow-hidden">
                    {item.name}
                  </span>
                  <span className="text-[10px] text-gray-500 mt-1">
                    {item.type === 'folder' ? `${item.item_count} items` : formatSize(item.size)}
                  </span>
                </button>
              ))}
            </div>
            
            {items.length === 0 && (
              <div className="text-center py-10 text-gray-500">
                <div className="text-4xl mb-2 opacity-50">📂</div>
                <p className="text-sm">Esta carpeta está vacía</p>
              </div>
            )}
          </div>
        </aside>
        
        {/* Botón colapsar/expandir - SIEMPRE VISIBLE */}
        <button
          onClick={onToggleCollapse}
          className="absolute top-1/2 -translate-y-1/2 w-6 h-16 bg-dark-800 border border-dark-600 rounded-r-lg flex items-center justify-center text-xs text-gray-400 hover:bg-dark-700 hover:text-white transition-all z-50 shadow-lg"
          style={{ 
            left: collapsed ? '0' : '320px',
            borderLeft: collapsed ? '1px solid #333' : 'none'
          }}
          title={collapsed ? "Expandir" : "Colapsar"}
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>

      {/* Modal añadir biblioteca */}
      {showModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50" onClick={() => setShowModal(false)}>
          <div className="bg-dark-800 border border-dark-600 rounded-xl p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold mb-4">➕ Añadir Biblioteca</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">Nombre</label>
                <input
                  type="text"
                  value={newLibName}
                  onChange={(e) => setNewLibName(e.target.value)}
                  placeholder="Mis Videos de Viaje"
                  className="w-full px-4 py-2.5 bg-dark-900 border border-dark-600 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">Ruta de carpeta (relativa a /videos)</label>
                <input
                  type="text"
                  value={newLibPath}
                  onChange={(e) => setNewLibPath(e.target.value)}
                  placeholder="viajes/2024"
                  className="w-full px-4 py-2.5 bg-dark-900 border border-dark-600 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 px-4 py-2.5 bg-white/10 rounded-lg hover:bg-white/15 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2.5 bg-blue-600 rounded-lg hover:bg-blue-500 transition-colors"
                >
                  Añadir
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}

function formatSize(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}
