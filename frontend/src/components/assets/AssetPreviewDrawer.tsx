import type { ReactNode } from 'react';
import { STATUS_COLORS } from '../shared/statusColors';
import { useQuery } from '@tanstack/react-query';
import { Drawer, Progress } from 'antd';
import { FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { AssetItem } from '../../types/assets';
import { listAssetChunks, type IndexProgress } from '../../api/client/assets';
import { ExtBadge, StatusPill } from './AssetBadges';
import { getAssetStatus, getExt } from './assetUtils';

interface AssetPreviewDrawerProps {
  asset: AssetItem;
  indexing: { id: string; deadline: number }[];
  progressMap: Record<string, IndexProgress>;
  onClose: () => void;
  onOpenChunks: (asset: AssetItem) => void;
}

function KVRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="grid grid-cols-[88px_1fr] items-center min-h-7 mb-2.5">
      <span className="text-xs text-[var(--color-text-tertiary)]">{label}</span>
      <span className="text-[13px] text-[var(--color-text-primary)]">
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
  onOpenChunks,
}: AssetPreviewDrawerProps) {
  const { t } = useTranslation();
  const ext = getExt(asset.name);
  const progress = progressMap[asset.id];
  const status = getAssetStatus(asset, indexing, progress);
  const isProcessing = status === 'processing';

  const { data: chunks, isLoading } = useQuery({
    queryKey: ['asset-chunks', asset.id],
    queryFn: () => listAssetChunks(asset.id),
    enabled: asset.indexed,
  });

  return (
    <Drawer
      title={asset.name}
      placement="right"
      width={480}
      open
      onClose={onClose}
      styles={{ body: { padding: 20 } }}
    >
      <Section label={t('assets.section.fileInfo')}>
        <KVRow
          label={t('assets.info.format')}
          value={
            <span className="inline-flex items-center gap-2">
              <ExtBadge ext={ext} />
              <span className="font-mono uppercase text-[var(--color-text-secondary)]">
                {ext || asset.assetType}
              </span>
            </span>
          }
        />
        <KVRow
          label={t('assets.info.size')}
          value={
            <span className="font-mono text-[var(--color-text-secondary)]">
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
          value={<StatusPill status={status} />}
        />
        <KVRow
          label={t('assets.info.chunks')}
          value={
            asset.indexed ? (
              <span className="font-mono text-[var(--color-text-secondary)]">
                {chunks ? `${chunks.length} ${t('assets.chunkUnit')}` : '—'}
              </span>
            ) : (
              <span className="text-[var(--color-text-muted)]">—</span>
            )
          }
        />
        <KVRow
          label={t('assets.info.updated')}
          value={<span className="text-[var(--color-text-muted)]">—</span>}
        />
      </Section>

      <Section label={t('assets.section.chunks')}>
        {isProcessing ? (
          <div className="text-center py-6">
            <Progress
              percent={progress?.percentage ?? 0}
              strokeColor={STATUS_COLORS.amber}
              size="small"
            />
            <div className="text-[12.5px] text-[var(--color-text-secondary)] mt-3">
              {t('assets.processing')}
            </div>
          </div>
        ) : asset.indexed ? (
          isLoading ? (
            <div className="py-8 text-center text-[13px] text-[var(--color-text-muted)]">
              {t('assets.loading')}
            </div>
          ) : !chunks || chunks.length === 0 ? (
            <div className="py-8 text-center flex flex-col items-center">
              <FileText
                size={24}
                className="mb-2 text-[var(--color-text-muted)]"
              />
              <p className="text-[13px] text-[var(--color-text-primary)] m-0">
                {t('assets.noChunks')}
              </p>
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-2">
                {chunks.slice(0, 3).map((chunk, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-[9px] border border-[var(--color-border)] bg-[var(--color-surface)] flex flex-col gap-1.5"
                  >
                    <div className="text-[10px] font-mono text-[var(--color-text-tertiary)]">
                      CHUNK #{i + 1}
                    </div>
                    {chunk.tags.length > 0 && (
                      <div className="flex gap-1 flex-wrap">
                        {chunk.tags.map((tag) => (
                          <span
                            key={tag}
                            className="text-[10px] px-1 py-0.5 rounded bg-[var(--color-surface-hover)] text-[var(--color-text-secondary)]"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                    <div className="text-[12.5px] text-[var(--color-text-secondary)] leading-[1.6] whitespace-pre-wrap break-words">
                      {chunk.text}
                    </div>
                  </div>
                ))}
              </div>
              {chunks.length > 3 && (
                <button
                  type="button"
                  onClick={() => onOpenChunks(asset)}
                  className="mt-3 w-full text-[12.5px] text-[var(--color-accent-soft)] cursor-pointer border-none bg-transparent hover:underline"
                >
                  {t('assets.viewAllChunks', { count: chunks.length })}
                </button>
              )}
            </>
          )
        ) : (
          <div className="py-8 text-center text-[13px] text-[var(--color-text-muted)]">
            {t('assets.notIndexed')}
          </div>
        )}
      </Section>
    </Drawer>
  );
}
