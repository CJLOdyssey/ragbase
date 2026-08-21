import type { ReactNode } from 'react';
import Modal from '../shared/Modal';
import { useTranslation } from 'react-i18next';
import type { AssetItem } from '../../types/assets';
import type { IndexProgress } from '../../api/client/assets';
import { ExtBadge, StatusPill } from './AssetBadges';
import { getAssetStatus, getExt } from './assetUtils';

interface AssetPreviewDrawerProps {
  asset: AssetItem;
  indexing: { id: string; deadline: number }[];
  progressMap: Record<string, IndexProgress>;
  onClose: () => void;
  onOpenChunks?: (asset: AssetItem) => void;
}

function formatUpdatedAt(v?: string | null): string {
  if (!v) return '—';
  try {
    const d = new Date(v);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    return `${y}-${m}-${day} ${hh}:${mm}`;
  } catch {
    return '—';
  }
}

function KVRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="grid grid-cols-[88px_1fr] items-center h-7 mb-2.5">
      <span className="text-xs leading-none text-[var(--color-text-tertiary)]">
        {label}
      </span>
      <span className="text-[13px] leading-none text-[var(--color-text-primary)] flex items-center justify-start h-7 w-full">
        {value}
      </span>
    </div>
  );
}

function Section({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="mb-[22px]">
      <div className="text-[10.5px] font-mono font-semibold tracking-[0.08em] uppercase text-[var(--color-text-tertiary)] mb-3">
        {label}
      </div>
      {children}
    </div>
  );
}

export default function AssetPreviewDrawer({
  asset,
  indexing,
  progressMap,
  onClose,
}: AssetPreviewDrawerProps) {
  const { t } = useTranslation();
  const ext = getExt(asset.name);
  const progress = progressMap[asset.id];
  const status = getAssetStatus(asset, indexing, progress);

  return (
    <Modal
      title={asset.name}
      onClose={onClose}
      ariaLabel={asset.name}
      width={640}
      hideHeaderBorder
      hideFooterBorder
      bodyClassName="p-6 max-h-[70vh] overflow-y-auto"
      footer={
        <button
          type="button"
          onClick={onClose}
          className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none bg-[var(--color-accent)] text-white hover:opacity-90"
        >
          {t('common.close')}
        </button>
      }
    >
      <Section label={t('assets.section.fileInfo')}>
        <KVRow
          label={t('assets.info.format')}
          value={
            <span className="-ml-1">
              <ExtBadge ext={ext} />
            </span>
          }
        />
        <KVRow
          label={t('assets.info.size')}
          value={
            <span className="font-mono text-[var(--color-text-secondary)] inline-flex items-center h-7">
              {asset.sizeBytes < 1024
                ? `${asset.sizeBytes} B`
                : asset.sizeBytes < 1024 * 1024
                  ? `${(asset.sizeBytes / 1024).toFixed(1)} KB`
                  : `${(asset.sizeBytes / 1024 / 1024).toFixed(1)} MB`}
            </span>
          }
        />
        <KVRow
          label={t('assets.info.status')}
          value={
            <span className="-ml-2">
              <StatusPill status={status} />
            </span>
          }
        />
        <KVRow
          label={t('assets.info.chunks')}
          value={
            <span className="font-mono text-[var(--color-text-secondary)] inline-flex items-center h-7">
              {asset.chunkCount != null
                ? `${asset.chunkCount} ${t('assets.chunkUnit')}`
                : '—'}
            </span>
          }
        />
        <KVRow
          label={t('assets.info.updated')}
          value={
            <span className="text-[var(--color-text-muted)] inline-flex items-center h-7">
              {formatUpdatedAt(asset.updatedAt)}
            </span>
          }
        />
      </Section>
    </Modal>
  );
}
