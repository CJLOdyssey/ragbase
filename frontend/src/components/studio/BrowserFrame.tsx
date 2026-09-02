import { useEffect, useState } from 'react';
import { ExternalLink, X } from 'lucide-react';

export default function BrowserFrame() {
  const [img, setImg] = useState<string | null>(null);
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    const onFrame = (e: Event) => {
      setImg((e as CustomEvent<string>).detail);
      setUrl(null);
    };
    const onUrl = (e: Event) => {
      setUrl((e as CustomEvent<string>).detail);
      setImg(null);
    };
    const onClear = () => {
      setImg(null);
      setUrl(null);
    };
    window.addEventListener('browser-frame', onFrame);
    window.addEventListener('browser-open-url', onUrl);
    window.addEventListener('clear-browser-url', onClear);
    return () => {
      window.removeEventListener('browser-frame', onFrame);
      window.removeEventListener('browser-open-url', onUrl);
      window.removeEventListener('clear-browser-url', onClear);
    };
  }, []);

  if (!img && !url) return null;

  return (
    <div className="rounded-xl overflow-hidden border border-[var(--color-border)] flex flex-col">
      <div className="flex items-center gap-2 px-3 py-2 bg-[var(--color-surface-hover)] border-b border-[var(--color-border)]">
        <div className="flex-1 text-xs text-[var(--color-text-muted)] truncate">
          {url ? <ExternalLink size={12} className="inline mr-1" /> : null}
          {url || 'Browser screenshot'}
        </div>
        <button
          className="p-1 rounded hover:bg-[var(--color-surface-raised)]"
          onClick={() => {
            setImg(null);
            setUrl(null);
            import('../../stores/messageHandler').then((m) =>
              m.clearPendingBrowserUrl(),
            );
          }}
        >
          <X size={14} />
        </button>
      </div>
      {img && (
        <img src={`data:image/png;base64,${img}`} alt="" className="w-full" />
      )}
      {url && (
        <iframe
          src={url}
          className="w-full h-[480px] bg-white"
          sandbox="allow-scripts allow-forms"
          referrerPolicy="no-referrer"
        />
      )}
    </div>
  );
}
