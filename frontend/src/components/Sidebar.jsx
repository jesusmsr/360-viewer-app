import { useState, useMemo, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Folder,
  FolderOpen,
  Plus,
  X,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  Calendar,
  FileText,
} from 'lucide-react';

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
  onToggleCollapse,
}) {
  const { t } = useTranslation();
  const [showModal, setShowModal] = useState(false);
  const [newLibName, setNewLibName] = useState('');
  const [newLibPath, setNewLibPath] = useState('');
  const [sortBy, setSortBy] = useState('date');
  const [sortOrder, setSortOrder] = useState('desc');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (newLibName && newLibPath) {
      onAddLibrary(newLibName, newLibPath);
      setNewLibName('');
      setNewLibPath('');
      setShowModal(false);
    }
  };

  // Separar carpetas y videos
  const folders = useMemo(
    () => items.filter((i) => i.type === 'folder'),
    [items],
  );
  const videos = useMemo(
    () => items.filter((i) => i.type === 'video'),
    [items],
  );

  // Ordenar videos
  const sortedVideos = useMemo(() => {
    const sorted = [...videos];
    sorted.sort((a, b) => {
      if (sortBy === 'date') {
        return sortOrder === 'desc'
          ? b.modified - a.modified
          : a.modified - b.modified;
      } else {
        return sortOrder === 'desc'
          ? b.name.localeCompare(a.name)
          : a.name.localeCompare(b.name);
      }
    });
    return sorted;
  }, [videos, sortBy, sortOrder]);

  // Items ordenados: carpetas primero, luego videos ordenados
  const sortedItems = [...folders, ...sortedVideos];

  const toggleSort = (field) => {
    if (sortBy === field) {
      setSortOrder((prev) => (prev === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortBy(field);
      setSortOrder(field === 'date' ? 'desc' : 'asc');
    }
  };

  return (
    <>
      {/* Sidebar Container */}
      <div
        className={`relative flex transition-all duration-300 ${collapsed ? 'w-0' : 'w-80'}`}
      >
        {/* Sidebar Content */}
        <aside
          className={`bg-dark-800 border-r border-dark-600 flex flex-col h-full overflow-hidden transition-all duration-300 ${collapsed ? 'w-0 opacity-0' : 'w-80 opacity-100'}`}
        >
          <div className='p-5 border-b border-dark-600 min-w-[320px]'>
            <h1 className='text-xl font-semibold mb-1'>🎥 {t('app.title')}</h1>
            <p className='text-sm text-gray-400'>
              {t('sidebar.librariesTitle')}
            </p>
          </div>

          {/* Bibliotecas */}
          <div className='p-4 border-b border-dark-600 min-w-[320px]'>
            <button
              onClick={() => setShowModal(true)}
              className='w-full mt-3 py-2.5 border border-dashed border-gray-600 rounded-lg text-gray-400 hover:border-gray-500 hover:text-gray-300 hover:bg-white/5 transition-all flex items-center justify-center gap-2 text-sm'
            >
              <Plus size={16} />
              {t('sidebar.addLibrary')}
            </button>
          </div>

          {/* Navegación de carpetas */}
          <div className='flex-1 overflow-y-auto p-4 min-w-[320px]'>
            {/* Breadcrumbs */}
            <div className='flex items-center flex-wrap gap-1 mb-3 p-2.5 bg-white/5 rounded-lg text-sm'>
              {breadcrumbs.map((crumb, idx) => (
                <span key={idx} className='flex items-center'>
                  {idx > 0 && <span className='text-gray-600 mx-1'>›</span>}
                  <button
                    onClick={() => onNavigate(crumb.path)}
                    className={`hover:text-white transition-colors ${
                      idx === breadcrumbs.length - 1
                        ? 'text-white font-medium'
                        : 'text-gray-400'
                    }`}
                  >
                    {crumb.name}
                  </button>
                </span>
              ))}
            </div>

            {/* Controles de ordenación */}
            <div className='flex items-center gap-2 mb-3 p-2 bg-white/5 rounded-lg'>
              <span className='text-xs text-gray-500 uppercase'>
                {t('sidebar.sort.label')}
              </span>
              <button
                onClick={() => toggleSort('date')}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs transition-colors ${
                  sortBy === 'date'
                    ? 'bg-blue-500/20 text-blue-400'
                    : 'hover:bg-white/10'
                }`}
              >
                <Calendar size={12} />
                {t('sidebar.sort.date')}
                {sortBy === 'date' && (
                  <span className='text-[10px]'>
                    {sortOrder === 'desc' ? '↓' : '↑'}
                  </span>
                )}
              </button>
              <button
                onClick={() => toggleSort('name')}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs transition-colors ${
                  sortBy === 'name'
                    ? 'bg-blue-500/20 text-blue-400'
                    : 'hover:bg-white/10'
                }`}
              >
                <FileText size={12} />
                {t('sidebar.sort.name')}
                {sortBy === 'name' && (
                  <span className='text-[10px]'>
                    {sortOrder === 'desc' ? '↓' : '↑'}
                  </span>
                )}
              </button>
            </div>

            {/* Lista vertical de items */}
            <div className='space-y-1'>
              {sortedItems.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() =>
                    item.type === 'folder'
                      ? onNavigate(item.path)
                      : onPlayVideo(item)
                  }
                  className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg transition-all hover:bg-white/10 text-left ${
                    item.type === 'video' && currentVideo === item.path
                      ? 'bg-green-500/20 border border-green-500/50'
                      : 'bg-white/5 border border-transparent hover:border-white/10'
                  }`}
                >
                  <span className='text-2xl flex-shrink-0'>
                    {item.type === 'folder' ? '📁' : '🎬'}
                  </span>
                  <div className='flex-1 min-w-0'>
                    <p className='text-sm font-medium truncate'>{item.name}</p>
                    <p className='text-xs text-gray-500 flex items-center gap-2 mt-0.5'>
                      {item.type === 'folder' ? (
                        <span>
                          {item.item_count} {t('sidebar.items')}
                        </span>
                      ) : (
                        <>
                          <span>{formatSize(item.size)}</span>
                          {item.modified && (
                            <>
                              <span className='text-gray-600'>•</span>
                              <span>{formatDate(item.modified)}</span>
                            </>
                          )}
                        </>
                      )}
                    </p>
                  </div>
                </button>
              ))}
            </div>

            {sortedItems.length === 0 && (
              <div className='text-center py-10 text-gray-500'>
                <div className='text-4xl mb-2 opacity-50'>📂</div>
                <p className='text-sm'>{t('sidebar.emptyFolder')}</p>
              </div>
            )}
          </div>
        </aside>

        {/* Botón colapsar/expandir - SIEMPRE VISIBLE */}
        <button
          onClick={onToggleCollapse}
          className='absolute top-1/2 -translate-y-1/2 w-6 h-16 bg-dark-800 border border-dark-600 rounded-r-lg flex items-center justify-center text-xs text-gray-400 hover:bg-dark-700 hover:text-white transition-all z-50 shadow-lg'
          style={{
            left: collapsed ? '0' : '320px',
            borderLeft: collapsed ? '1px solid #333' : 'none',
          }}
          title={collapsed ? t('sidebar.expand') : t('sidebar.collapse')}
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>

      {/* Modal añadir biblioteca */}
      {showModal && (
        <div
          className='fixed inset-0 bg-black/80 flex items-center justify-center z-50'
          onClick={() => setShowModal(false)}
        >
          <div
            className='bg-dark-800 border border-dark-600 rounded-xl p-6 w-full max-w-md'
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className='text-lg font-semibold mb-4'>
              ➕ {t('modal.addLibrary')}
            </h3>
            <form onSubmit={handleSubmit} className='space-y-4'>
              <div>
                <label className='block text-sm text-gray-400 mb-1.5'>
                  {t('modal.name')}
                </label>
                <input
                  type='text'
                  value={newLibName}
                  onChange={(e) => setNewLibName(e.target.value)}
                  placeholder={t('modal.namePlaceholder')}
                  className='w-full px-4 py-2.5 bg-dark-900 border border-dark-600 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none'
                  autoFocus
                />
              </div>
              <div>
                <label className='block text-sm text-gray-400 mb-1.5'>
                  {t('modal.path')}
                </label>
                <input
                  type='text'
                  value={newLibPath}
                  onChange={(e) => setNewLibPath(e.target.value)}
                  placeholder={t('modal.pathPlaceholder')}
                  className='w-full px-4 py-2.5 bg-dark-900 border border-dark-600 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none'
                />
              </div>
              <div className='flex gap-3 pt-2'>
                <button
                  type='button'
                  onClick={() => setShowModal(false)}
                  className='flex-1 px-4 py-2.5 bg-white/10 rounded-lg hover:bg-white/15 transition-colors'
                >
                  {t('modal.cancel')}
                </button>
                <button
                  type='submit'
                  className='flex-1 px-4 py-2.5 bg-blue-600 rounded-lg hover:bg-blue-500 transition-colors'
                >
                  {t('modal.add')}
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

function formatDate(timestamp) {
  if (!timestamp) return '';
  const date = new Date(timestamp * 1000);
  return date.toLocaleDateString('en-US', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}
