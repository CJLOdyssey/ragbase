import { useEffect, useState } from 'react';
import ConfirmDialog from '../shared/ConfirmDialog';
import EmptyState from '../shared/EmptyState';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Download, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  deleteMemory,
  exportSessionMemories,
  listSessionMemories,
  type MemoryItem,
} from '../../api/client/sessions';
import Logger from '../../utils/logger';
import { useToast } from '../../utils/useToast';

interface Props {
  sessionId: string;
  onClose: () => void;
}

export default function MemoryPanel({ sessionId, onClose }: Props) {
  const { t } = useTranslation();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [deleteTarget, setDeleteTarget] = useState<MemoryItem | null>(null);

  // 覆盖层与 antd Modal 一致的键盘体验：Escape 关闭。
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  const { data: memories = [], isLoading } = useQuery({
    queryKey: ['memories', sessionId],
    queryFn: () => listSessionMemories(sessionId),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteMemory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memories', sessionId] });
      setDeleteTarget(null);
      toast(t('toast.saveSuccess'), 'success');
    },
    onError: () => toast(t('toast.error'), 'error'),
  });

  const handleExport = async (format: 'json' | 'md') => {
    try {
      const blob = await exportSessionMemories(sessionId, format);
      const ext = format === 'json' ? 'json' : 'md';
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `memories_${sessionId}.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      Logger.warn('[memory] export failed: %s', err);
      toast(t('toast.error'), 'error');
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
        <h2 className="text-sm font-semibold text-[var(--color-text-primary)] m-0">
          {t('memory.title')}
        </h2>
        <div className="flex items-center gap-1">
          <button
            className="p-1.5 rounded bg-transparent border-none cursor-pointer text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] transition-colors duration-150"
            onClick={() => handleExport('json')}
            title={t('memory.exportJson')}
          >
            <Download size={14} />
          </button>
          <button
            className="p-1.5 rounded bg-transparent border-none cursor-pointer text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] transition-colors duration-150"
            onClick={onClose}
            title={t('common.close')}
          >
            ✕
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-3">
        {isLoading ? (
          <div className="text-sm text-[var(--color-text-muted)] py-8 text-center">
            {t('common.loading')}
          </div>
        ) : memories.length === 0 ? (
          <EmptyState
            title={t('memory.empty')}
            description={t('memory.emptyDesc')}
          />
        ) : (
          <div className="flex flex-col gap-2">
            {memories.map((m) => (
              <div
                key={m.id}
                className="flex items-start gap-2 p-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-raised)]"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-[var(--color-accent)]">
                      {m.agent_role}
                    </span>
                    <span className="text-xs text-[var(--color-text-muted)]">
                      {m.content_type}
                    </span>
                  </div>
                  <p className="text-sm text-[var(--color-text-primary)] m-0 leading-relaxed">
                    {m.summary}
                  </p>
                  {m.created_at && (
                    <span className="text-xs text-[var(--color-text-muted)] mt-1 block">
                      {new Date(m.created_at).toLocaleString()}
                    </span>
                  )}
                </div>
                <button
                  className="p-1 rounded bg-transparent border-none cursor-pointer text-[var(--color-text-muted)] hover:text-[var(--color-danger)] hover:bg-[var(--color-danger)]/10 transition-colors duration-150 shrink-0"
                  onClick={() => setDeleteTarget(m)}
                  title={t('confirm.delete')}
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {deleteTarget && (
        <ConfirmDialog
          title={t('memory.deleteTitle')}
          message={t('memory.deleteConfirm')}
          danger
          confirmLabel={t('confirm.delete')}
          onConfirm={() => deleteMutation.mutate(deleteTarget.id)}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </div>
  );
}
