import { useCallback, useRef, useState } from 'react';
import EmptyState from '../shared/EmptyState';
import { useQuery } from '@tanstack/react-query';
import { FileText, Upload } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { listAssets, uploadAsset } from '../../api/client/assets';
import { useToast } from '../../utils/useToast';

interface AssetPickerProps {
  selected: string[];
  onChange: (ids: string[]) => void;
}

export default function AssetPicker({ selected, onChange }: AssetPickerProps) {
  const { t } = useTranslation();
  const { toast } = useToast();
  const { data: assets = [], refetch } = useQuery({
    queryKey: ['assets'],
    queryFn: listAssets,
  });
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const toggle = useCallback(
    (id: string) => {
      onChange(
        selected.includes(id)
          ? selected.filter((x) => x !== id)
          : [...selected, id],
      );
    },
    [selected, onChange],
  );

  const handleUpload = useCallback(
    async (file: File | undefined) => {
      if (!file) return;
      setUploading(true);
      try {
        await uploadAsset(file);
        toast(t('assets.upload.success'), 'success');
        await refetch();
      } catch {
        toast(t('assets.upload.failed'), 'error');
      } finally {
        setUploading(false);
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    },
    [refetch, toast, t],
  );

  return (
    <section
      aria-label={t('assets.title')}
      className="bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--da-input-radius)] p-4"
    >
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-medium text-[var(--color-text-primary)]">
          {t('assets.title')}
        </h2>
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-surface-hover)] text-[var(--color-text-primary)] cursor-pointer hover:bg-[var(--color-border)] disabled:opacity-60"
        >
          <Upload size={14} />
          <span>{t('assets.upload.button')}</span>
        </button>
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          aria-hidden="true"
          tabIndex={-1}
          onChange={(e) => void handleUpload(e.target.files?.[0])}
        />
      </div>

      {assets.length === 0 ? (
        <EmptyState
          title={t('assets.list.empty')}
          icon={<FileText size={24} />}
        />
      ) : (
        <ul className="flex flex-col gap-1.5 max-h-48 overflow-y-auto">
          {assets.map((asset) => (
            <li key={asset.id}>
              <label className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg cursor-pointer hover:bg-[var(--color-surface-hover)]">
                <input
                  type="checkbox"
                  checked={selected.includes(asset.id)}
                  onChange={() => toggle(asset.id)}
                />
                <FileText
                  size={14}
                  className="text-[var(--color-text-muted)] shrink-0"
                />
                <span className="text-sm text-[var(--color-text-primary)] truncate">
                  {asset.name}
                </span>
                <span className="text-xs text-[var(--color-text-muted)] ml-auto shrink-0">
                  {asset.asset_type}
                </span>
              </label>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
