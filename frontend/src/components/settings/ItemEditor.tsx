import type { ReactNode } from 'react';
import Modal from '@/components/shared/Modal';
import { Save } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface Props {
  kind: string;
  form: { show: boolean; data: unknown; errors: string[] };
  editingItem: Record<string, unknown> | null;
  onSave: () => void;
  onClose: () => void;
  setFormData: (fn: (d: unknown) => unknown) => void;
  children: ReactNode;
}

// 通用编辑弹窗 —— 主窗口可传入自定义渲染逻辑；workstation 专属的
// Tool/MCP/Skill FormModal 分支已裁剪，不做特定字段表单。
export default function ItemEditor({
  kind,
  form,
  editingItem,
  onSave,
  onClose,
  setFormData,
  children,
}: Props) {
  const { t } = useTranslation();
  if (!form.show) return <>{children}</>;

  const data = (form.data ?? {}) as Record<string, unknown>;
  const set = (key: string, value: unknown) =>
    setFormData((d) => ({ ...(d as object), [key]: value }));

  return (
    <>
      {children}
      <Modal
        title={editingItem ? t('workstation.edit') : t('configItem.add')}
        onClose={onClose}
        width={440}
        bodyClassName="px-6 py-5 space-y-4"
        footer={
          <>
            <button
              type="button"
              className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
              onClick={onClose}
            >
              {t('confirm.cancel')}
            </button>
            <button
              type="button"
              className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-all duration-150 bg-[var(--color-accent)] text-white hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed"
              onClick={onSave}
              disabled={typeof data.name !== 'string' || !data.name.trim()}
            >
              <Save size={14} />
              {t('providerEdit.save')}
            </button>
          </>
        }
      >
        {form.errors.length > 0 && (
          <div className="bg-[color-mix(in_srgb,var(--color-danger)_10%,transparent)] border border-[color-mix(in_srgb,var(--color-danger)_25%,transparent)] rounded-lg py-2 px-3.5 text-[var(--color-danger)] text-sm">
            {form.errors.join('；')}
          </div>
        )}
        <div>
          <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5">
            {t('providerEdit.name')}
          </label>
          <input
            type="text"
            value={(data.name as string) || ''}
            onChange={(e) => set('name', e.target.value)}
            className="w-full py-2 px-3 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-md text-[var(--color-text-primary)] text-sm font-sans outline-none transition-colors focus:border-[var(--color-accent)] placeholder:text-[var(--color-text-muted)]"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5">
            描述
          </label>
          <textarea
            value={(data.description as string) || ''}
            onChange={(e) => set('description', e.target.value)}
            rows={3}
            className="w-full py-2 px-3 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-md text-[var(--color-text-primary)] text-sm font-sans outline-none transition-colors focus:border-[var(--color-accent)] placeholder:text-[var(--color-text-muted)] resize-none"
          />
        </div>
        {kind === 'tool' && (
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5">
              {t('providerEdit.baseUrl')}
            </label>
            <input
              type="text"
              value={(data.endpoint as string) || ''}
              onChange={(e) => set('endpoint', e.target.value)}
              className="w-full py-2 px-3 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-md text-[var(--color-text-primary)] text-sm font-sans outline-none transition-colors focus:border-[var(--color-accent)] placeholder:text-[var(--color-text-muted)]"
            />
          </div>
        )}
      </Modal>
    </>
  );
}
