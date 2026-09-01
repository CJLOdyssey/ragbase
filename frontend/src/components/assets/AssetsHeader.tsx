import type { RefObject } from 'react';
import { FileText, FileUp, LayoutGrid, Link, Table2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export type ViewMode = 'table' | 'grid';

interface AssetsHeaderProps {
  view: ViewMode;
  onViewChange: (v: ViewMode) => void;
  onUrlImport: () => void;
  fileInputRef: RefObject<HTMLInputElement | null>;
  uploadPending: boolean;
  onFileSelect?: (file: File) => void;
}

export default function AssetsHeader({
  view,
  onViewChange,
  onUrlImport,
  fileInputRef,
  uploadPending,
  onFileSelect,
}: AssetsHeaderProps) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-3 px-4 py-4 border-b border-[var(--color-border)] shrink-0 sm:px-6 lg:px-8">
      {/* Row 1: 标题 */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-7 h-7 rounded-lg flex items-center justify-center border text-[var(--color-accent-soft)] bg-[color-mix(in_srgb,var(--color-accent)_12%,transparent)] border-[color-mix(in_srgb,var(--color-accent)_22%,transparent)] shrink-0">
          <FileText size={14} />
        </div>
        <div className="min-w-0">
          <h1 className="m-0 text-[18px] font-bold tracking-[-0.03em] text-[var(--color-text-primary)] leading-none">
            {t('assets.title')}
          </h1>
          <p className="m-0 mt-1 text-[12.5px] leading-[1.4] text-[var(--color-text-muted)] hidden sm:block">
            {t('assets.subtitle')}
          </p>
        </div>
      </div>

      {/* Row 2: URL导入 + 上传素材 + 视图切换 */}
      <div className="flex items-center justify-between gap-2">
        <button
          className="inline-flex items-center gap-2 min-h-[44px] px-3.5 rounded-full text-[13px] font-medium cursor-pointer border border-[var(--color-border)] bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] transition-colors"
          onClick={onUrlImport}
        >
          <Link size={15} />
          {t('assets.urlImport.button')}
        </button>

        <div className="flex items-center gap-2 shrink-0">
          <button
            className="inline-flex items-center gap-2 min-h-[44px] px-3 sm:px-4 rounded-full border-none text-white text-[13px] font-medium cursor-pointer bg-[linear-gradient(135deg,var(--color-accent),var(--color-accent-hover))] shadow-[0_2px_10px_color-mix(in_srgb,var(--color-accent)_28%,transparent)] hover:shadow-[0_4px_18px_color-mix(in_srgb,var(--color-accent)_45%,transparent)] hover:-translate-y-px transition-all disabled:opacity-60 disabled:cursor-not-allowed"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadPending}
          >
            <FileUp size={15} />
            {uploadPending
              ? t('assets.upload.uploading')
              : t('assets.upload.button')}
          </button>

          <div className="flex items-center p-0.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-raised)]">
            {(['table', 'grid'] as const).map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => onViewChange(v)}
                aria-label={
                  v === 'table' ? t('assets.viewTable') : t('assets.viewGrid')
                }
                className={`min-w-[44px] min-h-[44px] rounded-md border-none cursor-pointer inline-flex items-center justify-center transition-colors ${view === v ? 'bg-[var(--color-surface-overlay)] text-[var(--color-text-primary)] shadow-sm' : 'bg-transparent text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]'}`}
              >
                {v === 'table' ? <Table2 size={14} /> : <LayoutGrid size={14} />}
              </button>
            ))}
          </div>
        </div>
      </div>

      <input
        ref={fileInputRef as RefObject<HTMLInputElement>}
        type="file"
        accept="image/png,image/jpeg,image/webp,application/pdf,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        className="hidden"
        data-testid="asset-file-input"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f && onFileSelect) onFileSelect(f);
          e.currentTarget.value = '';
        }}
      />
    </div>
  );
}
