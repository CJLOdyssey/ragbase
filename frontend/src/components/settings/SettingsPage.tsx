import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { KeyRound, Loader2, Plus, Trash2, Zap } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  createKey,
  deleteKey,
  listKeys,
  testKeyConnection,
} from '../../api/client/keys';
import { useToast } from '../../utils/useToast';

export default function SettingsPage() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({
    provider: '',
    label: '',
    api_key: '',
    base_url: '',
    models: '',
  });

  const { data: keys = [] } = useQuery({
    queryKey: ['keys'],
    queryFn: listKeys,
  });

  const invalidateKeys = () =>
    void queryClient.invalidateQueries({ queryKey: ['keys'] });

  const saveMutation = useMutation({
    mutationFn: () =>
      createKey({
        provider: form.provider.trim(),
        label: form.label.trim(),
        api_key: form.api_key.trim(),
        base_url: form.base_url.trim() || undefined,
        models: form.models
          .split(',')
          .map((m) => m.trim())
          .filter(Boolean),
      }),
    onSuccess: () => {
      toast(t('settings.saveSuccess'), 'success');
      setAdding(false);
      setForm({
        provider: '',
        label: '',
        api_key: '',
        base_url: '',
        models: '',
      });
      invalidateKeys();
    },
    onError: () => toast(t('settings.saveFailed'), 'error'),
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => deleteKey(id),
    onSuccess: () => {
      toast(t('settings.deleteSuccess'), 'success');
      invalidateKeys();
    },
    onError: () => toast(t('settings.saveFailed'), 'error'),
  });

  const testMutation = useMutation({
    mutationFn: (id: string) => testKeyConnection(id),
    onSuccess: (res) => {
      toast(
        res.success ? t('settings.testSuccess') : t('settings.testFailed'),
        res.success ? 'success' : 'error',
      );
    },
    onError: () => toast(t('settings.testFailed'), 'error'),
  });

  const canSave =
    form.provider.trim() && form.label.trim() && form.api_key.trim();

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-[900px] mx-auto px-6 py-8">
        <h1 className="text-xl font-semibold text-[var(--color-text-primary)] mb-2">
          {t('settings.title')}
        </h1>
        <p className="text-sm text-[var(--color-text-muted)] mb-6">
          {t('settings.apiKeyHint')}
        </p>

        <section aria-label={t('settings.section.api')}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-[var(--color-text-primary)]">
              {t('settings.section.api')}
            </h2>
            <button
              type="button"
              onClick={() => setAdding((v) => !v)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-surface-raised)] border border-[var(--color-border)] text-[var(--color-text-primary)] cursor-pointer hover:bg-[var(--color-surface-hover)]"
            >
              <Plus size={14} />
              {t('settings.add')}
            </button>
          </div>

          {adding && (
            <form
              className="flex flex-col gap-3 mb-4 p-4 rounded-xl bg-[var(--color-surface-raised)] border border-[var(--color-border)]"
              onSubmit={(e) => {
                e.preventDefault();
                saveMutation.mutate();
              }}
            >
              <label className="flex flex-col gap-1 text-xs text-[var(--color-text-muted)]">
                {t('settings.provider')}
                <input
                  value={form.provider}
                  onChange={(e) =>
                    setForm({ ...form, provider: e.target.value })
                  }
                  placeholder={t('settings.providerPlaceholder')}
                  className="px-3 py-2 rounded-lg text-sm text-[var(--color-text-primary)] bg-[var(--color-surface)] border border-[var(--color-border)]"
                  required
                />
              </label>
              <label className="flex flex-col gap-1 text-xs text-[var(--color-text-muted)]">
                {t('settings.label')}
                <input
                  value={form.label}
                  onChange={(e) => setForm({ ...form, label: e.target.value })}
                  placeholder={t('settings.labelPlaceholder')}
                  className="px-3 py-2 rounded-lg text-sm text-[var(--color-text-primary)] bg-[var(--color-surface)] border border-[var(--color-border)]"
                  required
                />
              </label>
              <label className="flex flex-col gap-1 text-xs text-[var(--color-text-muted)]">
                {t('settings.apiKey')}
                <input
                  type="password"
                  value={form.api_key}
                  onChange={(e) =>
                    setForm({ ...form, api_key: e.target.value })
                  }
                  placeholder={t('settings.apiKeyPlaceholder')}
                  className="px-3 py-2 rounded-lg text-sm text-[var(--color-text-primary)] bg-[var(--color-surface)] border border-[var(--color-border)]"
                  required
                />
              </label>
              <label className="flex flex-col gap-1 text-xs text-[var(--color-text-muted)]">
                {t('settings.baseUrl')}
                <input
                  value={form.base_url}
                  onChange={(e) =>
                    setForm({ ...form, base_url: e.target.value })
                  }
                  className="px-3 py-2 rounded-lg text-sm text-[var(--color-text-primary)] bg-[var(--color-surface)] border border-[var(--color-border)]"
                />
              </label>
              <label className="flex flex-col gap-1 text-xs text-[var(--color-text-muted)]">
                {t('settings.models')}
                <input
                  value={form.models}
                  onChange={(e) => setForm({ ...form, models: e.target.value })}
                  placeholder={t('settings.modelsPlaceholder')}
                  className="px-3 py-2 rounded-lg text-sm text-[var(--color-text-primary)] bg-[var(--color-surface)] border border-[var(--color-border)]"
                />
              </label>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setAdding(false)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] cursor-pointer"
                >
                  {t('settings.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={!canSave || saveMutation.isPending}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-white cursor-pointer bg-[var(--color-accent, #4f46e5)] hover:opacity-90 disabled:opacity-60"
                >
                  {saveMutation.isPending && (
                    <Loader2 size={14} className="animate-spin" />
                  )}
                  {t('settings.save')}
                </button>
              </div>
            </form>
          )}

          {keys.length === 0 ? (
            <p className="text-sm text-[var(--color-text-muted)]">
              {t('settings.empty')}
            </p>
          ) : (
            <ul className="flex flex-col gap-2">
              {keys.map((key) => (
                <li
                  key={key.id}
                  className="flex items-center gap-3 p-3 rounded-xl bg-[var(--color-surface-raised)] border border-[var(--color-border)]"
                >
                  <KeyRound
                    size={16}
                    className="text-[var(--color-text-muted)] shrink-0"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-[var(--color-text-primary)] truncate">
                        {key.label}
                      </span>
                      {key.is_default && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--color-surface-hover)] text-[var(--color-text-muted)]">
                          {t('settings.default')}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-[var(--color-text-muted)] truncate">
                      {key.provider} · {key.key_masked}
                      {key.models.length > 0 && ` · ${key.models.join(', ')}`}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => testMutation.mutate(key.id)}
                    disabled={testMutation.isPending}
                    className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] cursor-pointer hover:bg-[var(--color-surface-hover)] disabled:opacity-60"
                    aria-label={`${t('settings.test')}: ${key.label}`}
                  >
                    <Zap size={13} />
                    {t('settings.test')}
                  </button>
                  <button
                    type="button"
                    onClick={() => removeMutation.mutate(key.id)}
                    disabled={removeMutation.isPending}
                    className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] cursor-pointer hover:bg-[var(--color-surface-hover)] disabled:opacity-60"
                    aria-label={`${t('settings.deleteSuccess')}: ${key.label}`}
                  >
                    <Trash2 size={13} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
