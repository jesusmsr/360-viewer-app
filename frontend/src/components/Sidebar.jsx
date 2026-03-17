import { useState, useMemo, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Folder,
  FolderOpen,
  Plus,
  X,
  ChevronLeft,
  Calendar,
  FileText,
  Users,
  RefreshCw,
  Link,
  Wifi,
  WifiOff,
  Copy,
  Gift,
} from 'lucide-react';

export function Sidebar({
  libraries,
  currentLibrary,
  onSelectLibrary,
  onAddLibrary,
  onDeleteLibrary,
  peers,
  selectedPeer,
  onSelectPeer,
  onAddPeer,
  onRemovePeer,
  onSyncPeer,
  onRefreshPeers,
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
  const [showPeerModal, setShowPeerModal] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [newLibName, setNewLibName] = useState('');
  const [newLibPath, setNewLibPath] = useState('');
  const [newPeerName, setNewPeerName] = useState('');
  const [newPeerUrl, setNewPeerUrl] = useState('');
  const [newPeerCode, setNewPeerCode] = useState('');
  const [urlError, setUrlError] = useState('');
  const [sortBy, setSortBy] = useState('date');
  const [sortOrder, setSortOrder] = useState('desc');

  // Estados para generar invitaciones
  const [inviteCode, setInviteCode] = useState(null);
  const [inviteLoading, setInviteLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [myInvites, setMyInvites] = useState([]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (newLibName && newLibPath) {
      onAddLibrary(newLibName, newLibPath);
      setNewLibName('');
      setNewLibPath('');
      setShowModal(false);
    }
  };

  const handleAddPeer = async (e) => {
    e.preventDefault();

    // Validate URL before submission
    if (!isValidUrl(newPeerUrl)) {
      setUrlError('Please enter a valid URL (e.g., http://example.com:3000)');
      return;
    }

    if (newPeerName && newPeerUrl && newPeerCode) {
      // Usar el nuevo sistema de invitación con código
      const result = await joinWithInviteCode({
        name: newPeerName,
        url: newPeerUrl,
        invite_code: newPeerCode,
      });

      if (result.success) {
        // Guardar el peer en nuestro backend local
        // Usar SIEMPRE el nombre que puso el usuario, no el del servidor
        if (onAddPeer) {
          await onAddPeer({
            id: result.peer_id,
            name: newPeerName, // ← Usar el nombre que escribió el usuario
            url: newPeerUrl,
            token: result.token || null,
          });
        }

        setNewPeerName('');
        setNewPeerUrl('');
        setNewPeerCode('');
        setUrlError('');
        setShowPeerModal(false);
        // Recargar peers
        if (onRefreshPeers) onRefreshPeers();
      } else {
        alert(result.error || 'Error conectando con el amigo');
      }
    }
  };

  // Función para unirse usando código de invitación
  const joinWithInviteCode = async (data) => {
    try {
      const peerUrl = data.url.replace(/\/$/, '');

      // Generar un ID único para este peer
      const myPeerId =
        'peer_' +
        Date.now().toString(36) +
        Math.random().toString(36).substr(2, 5);

      const response = await fetch(`${peerUrl}/api/federation/join`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Peer-Id': myPeerId,
          'X-Peer-Name': data.name,
        },
        body: JSON.stringify({
          url: data.url,
          invite_code: data.invite_code,
          my_name: data.name,
          my_id: myPeerId, // Enviamos nuestro ID para que el NAS lo use
        }),
      });

      if (response.ok) {
        return await response.json();
      } else {
        const error = await response.json();
        return { success: false, error: error.error };
      }
    } catch (err) {
      return { success: false, error: 'Error de conexión' };
    }
  };

  // Generar código de invitación
  const generateInvite = async () => {
    setInviteLoading(true);
    try {
      const response = await fetch('/api/federation/invite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'Invitado',
          description: 'Invitación generada desde la app',
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setInviteCode(data.invite_code);
        loadMyInvites(); // Recargar lista
      }
    } catch (err) {
      console.error('Error generando invitación:', err);
    }
    setInviteLoading(false);
  };

  // Cargar mis invitaciones
  const loadMyInvites = async () => {
    try {
      const response = await fetch('/api/federation/my-invites');
      if (response.ok) {
        const data = await response.json();
        setMyInvites(data.invites || []);
      }
    } catch (err) {
      console.error('Error cargando invitaciones:', err);
    }
  };

  // Copiar al portapapeles
  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Validate URL format
  const isValidUrl = (url) => {
    try {
      const urlObj = new URL(url);
      return (
        (urlObj.protocol === 'http:' || urlObj.protocol === 'https:') &&
        urlObj.hostname.length > 0
      );
    } catch {
      return false;
    }
  };

  // Handle URL input with validation
  const handleUrlChange = (e) => {
    const url = e.target.value;
    setNewPeerUrl(url);

    // Real-time validation
    if (url && !isValidUrl(url)) {
      setUrlError('Please enter a valid URL (e.g., http://example.com:3000)');
    } else {
      setUrlError('');
    }
  };

  // Cargar invitaciones al abrir modal y resetear código
  useEffect(() => {
    if (showInviteModal) {
      setInviteCode(null); // Resetear para mostrar botón de generar
      setCopied(false);
      loadMyInvites();
    }
  }, [showInviteModal]);

  // Separar carpetas y videos
  const safeItems = items || [];
  const folders = useMemo(
    () => safeItems.filter((i) => i.type === 'folder'),
    [safeItems],
  );
  const videos = useMemo(
    () => safeItems.filter((i) => i.type === 'video'),
    [safeItems],
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
            <p className='text-xs uppercase text-gray-500 mb-3 tracking-wider'>
              {t('sidebar.myLibraries')}
            </p>
            <div className='space-y-1'>
              {/* Opción Raíz */}
              <button
                onClick={() => onSelectLibrary(null)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                  !currentLibrary
                    ? 'bg-blue-500/20 text-blue-400'
                    : 'hover:bg-white/5'
                }`}
              >
                <FolderOpen size={20} />
                <span className='flex-1 text-left text-sm'>
                  {t('sidebar.allFolders')}
                </span>
              </button>

              {/* Bibliotecas guardadas */}
              {Object.entries(libraries || {}).map(([id, lib]) => (
                <div key={id} className='group relative'>
                  <button
                    onClick={() => onSelectLibrary(id)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                      currentLibrary === id
                        ? 'bg-blue-500/20 text-blue-400'
                        : 'hover:bg-white/5'
                    }`}
                  >
                    <Folder size={20} />
                    <span className='flex-1 text-left text-sm truncate'>
                      {lib.name}
                    </span>
                  </button>
                  <button
                    onClick={() => onDeleteLibrary(id)}
                    className='absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 p-1.5 rounded text-red-400 hover:bg-red-500/20 transition-all'
                    title={t('sidebar.deleteLibrary')}
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
            </div>

            <button
              onClick={() => setShowModal(true)}
              className='w-full mt-3 py-2.5 border border-dashed border-gray-600 rounded-lg text-gray-400 hover:border-gray-500 hover:text-gray-300 hover:bg-white/5 transition-all flex items-center justify-center gap-2 text-sm'
            >
              <Plus size={16} />
              {t('sidebar.addLibrary')}
            </button>
          </div>

          {/* Peers / Amigos conectados */}
          <div className='p-4 border-b border-dark-600 min-w-[320px]'>
            <div className='flex items-center justify-between mb-3'>
              <p className='text-xs uppercase text-gray-500 tracking-wider flex items-center gap-2'>
                <Users size={14} />
                {t('sidebar.peersTitle') || 'Amigos'}
              </p>
              <button
                onClick={() =>
                  onSyncPeer &&
                  peers &&
                  Object.keys(peers).forEach((id) => onSyncPeer(id))
                }
                className='p-1 rounded hover:bg-white/10 text-gray-500 hover:text-gray-300'
                title={t('sidebar.syncAll') || 'Sincronizar todos'}
              >
                <RefreshCw size={14} />
              </button>
            </div>

            <div className='space-y-1'>
              {/* Mi Biblioteca (Local) */}
              <button
                onClick={() => onSelectPeer('local')}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                  selectedPeer === 'local'
                    ? 'bg-blue-500/20 text-blue-400'
                    : 'hover:bg-white/5'
                }`}
              >
                <FolderOpen size={20} />
                <span className='flex-1 text-left text-sm'>
                  {t('sidebar.myLibrary') || 'Mi Biblioteca'}
                </span>
              </button>

              {/* Peers conectados */}
              {Object.entries(peers || {}).map(([id, peer]) => (
                <div key={id} className='group relative'>
                  <button
                    onClick={() => onSelectPeer(id)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                      selectedPeer === id
                        ? 'bg-blue-500/20 text-blue-400'
                        : 'hover:bg-white/5'
                    }`}
                  >
                    {peer.status === 'online' ? (
                      <Wifi size={18} className='text-green-400' />
                    ) : (
                      <WifiOff size={18} className='text-gray-500' />
                    )}
                    <span className='flex-1 text-left text-sm truncate'>
                      {peer.name}
                    </span>
                  </button>
                  <div className='absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 flex items-center gap-1'>
                    <button
                      onClick={() => onSyncPeer(id)}
                      className='p-1.5 rounded text-blue-400 hover:bg-blue-500/20 transition-all'
                      title={t('sidebar.sync') || 'Sincronizar'}
                    >
                      <RefreshCw size={12} />
                    </button>
                    <button
                      onClick={() => onRemovePeer(id)}
                      className='p-1.5 rounded text-red-400 hover:bg-red-500/20 transition-all'
                      title={t('sidebar.deletePeer') || 'Eliminar'}
                    >
                      <X size={12} />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className='flex gap-2 mt-3'>
              <button
                onClick={() => setShowPeerModal(true)}
                className='flex-1 py-2.5 border border-dashed border-gray-600 rounded-lg text-gray-400 hover:border-gray-500 hover:text-gray-300 hover:bg-white/5 transition-all flex items-center justify-center gap-2 text-sm'
              >
                <Link size={16} />
                {t('sidebar.addPeer') || 'Conectar'}
              </button>
              <button
                onClick={() => setShowInviteModal(true)}
                className='py-2.5 px-3 border border-dashed border-gray-600 rounded-lg text-gray-400 hover:border-green-500 hover:text-green-400 hover:bg-green-500/10 transition-all'
                title={t('sidebar.generateInvite') || 'Generar invitación'}
              >
                <Gift size={16} />
              </button>
            </div>
          </div>

          {/* Navegación de carpetas */}
          <div className='flex-1 overflow-y-auto p-4 min-w-[320px]'>
            {/* Breadcrumbs */}
            <div className='flex items-center flex-wrap gap-1 mb-3 p-2.5 bg-white/5 rounded-lg text-sm'>
              {(breadcrumbs || []).map((crumb, idx) => (
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

      {/* Modal añadir peer */}
      {showPeerModal && (
        <div
          className='fixed inset-0 bg-black/80 flex items-center justify-center z-50'
          onClick={() => setShowPeerModal(false)}
        >
          <div
            className='bg-dark-800 border border-dark-600 rounded-xl p-6 w-full max-w-md'
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className='text-lg font-semibold mb-2'>
              🔗 {t('modal.addPeer')}
            </h3>
            <form onSubmit={handleAddPeer} className='space-y-4'>
              <div>
                <label className='block text-sm text-gray-400 mb-1.5'>
                  {t('modal.name')}
                </label>
                <input
                  type='text'
                  value={newPeerName}
                  onChange={(e) => setNewPeerName(e.target.value)}
                  placeholder={t('modal.namePlaceholder')}
                  className='w-full px-4 py-2.5 bg-dark-900 border border-dark-600 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none'
                  autoFocus
                />
              </div>
              <div>
                <label className='block text-sm text-gray-400 mb-1.5'>
                  {t('modal.url')}
                </label>
                <input
                  type='text'
                  value={newPeerUrl}
                  onChange={handleUrlChange}
                  placeholder={t('modal.urlPlaceholder')}
                  className={`w-full px-4 py-2.5 bg-dark-900 border rounded-lg text-white placeholder-gray-500 focus:outline-none ${
                    urlError
                      ? 'border-red-500 focus:border-red-500'
                      : 'border-dark-600 focus:border-blue-500'
                  }`}
                />
                {urlError && (
                  <p className='text-xs text-red-400 mt-1'>{urlError}</p>
                )}
              </div>
              <div>
                <label className='block text-sm text-gray-400 mb-1.5'>
                  {t('modal.inviteCode')}
                </label>
                <input
                  type='text'
                  value={newPeerCode}
                  onChange={(e) => setNewPeerCode(e.target.value.toUpperCase())}
                  placeholder={t('modal.inviteCodePlaceholder')}
                  className='w-full px-4 py-2.5 bg-dark-900 border border-dark-600 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none font-mono tracking-wider'
                />
              </div>
              <div className='flex gap-3 pt-2'>
                <button
                  type='button'
                  onClick={() => setShowPeerModal(false)}
                  className='flex-1 px-4 py-2.5 bg-white/10 rounded-lg hover:bg-white/15 transition-colors'
                >
                  {t('modal.cancel')}
                </button>
                <button
                  type='submit'
                  className='flex-1 px-4 py-2.5 bg-blue-600 rounded-lg hover:bg-blue-500 transition-colors'
                >
                  {t('modal.connect')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal generar invitación */}
      {showInviteModal && (
        <div
          className='fixed inset-0 bg-black/80 flex items-center justify-center z-50'
          onClick={() => setShowInviteModal(false)}
        >
          <div
            className='bg-dark-800 border border-dark-600 rounded-xl p-6 w-full max-w-md'
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className='text-lg font-semibold mb-2'>
              🎁 {t('modal.generateInvite') || 'Generar invitación'}
            </h3>
            <p className='text-sm text-gray-400 mb-4'>
              {t('modal.inviteDescription')}
            </p>

            {!inviteCode ? (
              <div className='text-center py-6'>
                <button
                  onClick={generateInvite}
                  disabled={inviteLoading}
                  className='px-6 py-3 bg-green-600 rounded-lg hover:bg-green-500 transition-colors disabled:opacity-50 flex items-center gap-2 mx-auto'
                >
                  {inviteLoading ? (
                    t('modal.generating')
                  ) : (
                    <>
                      <Gift size={18} /> {t('modal.generateCode')}
                    </>
                  )}
                </button>
              </div>
            ) : (
              <div className='bg-dark-900 border border-green-500/30 rounded-lg p-4 mb-4'>
                <p className='text-sm text-gray-400 mb-2'>
                  {t('modal.shareCode')}
                </p>
                <div className='flex items-center gap-2'>
                  <code className='flex-1 bg-dark-800 px-4 py-3 rounded-lg text-2xl font-mono text-green-400 tracking-wider text-center'>
                    {inviteCode}
                  </code>
                  <button
                    onClick={() => copyToClipboard(inviteCode)}
                    className='p-3 bg-white/10 rounded-lg hover:bg-white/20 transition-colors'
                    title={t('modal.copy')}
                  >
                    <Copy size={18} />
                  </button>
                </div>
                {copied && (
                  <p className='text-sm text-green-400 mt-2 text-center'>
                    {t('modal.copied')}
                  </p>
                )}
                <p className='text-xs text-gray-500 mt-3'>
                  {t('modal.inviteExpiry')}
                </p>
              </div>
            )}

            {/* Lista de invitaciones activas */}
            {myInvites.length > 0 && (
              <div className='mt-4'>
                <h4 className='text-sm font-medium text-gray-400 mb-2'>
                  {t('modal.yourInvites')}
                </h4>
                <div className='space-y-2 max-h-40 overflow-y-auto'>
                  {(myInvites || []).map((inv) => (
                    <div
                      key={inv.code}
                      className={`flex items-center justify-between p-2 rounded-lg text-sm ${
                        inv.used
                          ? 'bg-gray-800/50 text-gray-500'
                          : 'bg-dark-900'
                      }`}
                    >
                      <div>
                        <span className='font-mono'>{inv.code}</span>
                        {inv.used && (
                          <span className='text-xs ml-2'>
                            ✓ {t('modal.usedBy')} {inv.used_by}
                          </span>
                        )}
                        {inv.expired && !inv.used && (
                          <span className='text-xs ml-2 text-red-400'>
                            {t('modal.expired')}
                          </span>
                        )}
                      </div>
                      {!inv.used && !inv.expired && (
                        <button
                          onClick={() => copyToClipboard(inv.code)}
                          className='p-1 hover:bg-white/10 rounded'
                          title={t('modal.copy')}
                        >
                          <Copy size={14} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className='flex justify-end mt-4'>
              <button
                onClick={() => setShowInviteModal(false)}
                className='px-4 py-2 bg-white/10 rounded-lg hover:bg-white/15 transition-colors'
              >
                {t('modal.close')}
              </button>
            </div>
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

  const date =
    typeof timestamp === 'number'
      ? new Date(timestamp * 1000)
      : new Date(timestamp);

  if (isNaN(date.getTime())) return '';

  return date.toLocaleDateString('en-US', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}
