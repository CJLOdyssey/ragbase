import { Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface TestResult {
  success: boolean;
  message: string;
  latency?: number;
}

interface Props {
  onTest: () => void;
  disabled: boolean;
  testing: boolean;
  testResult: TestResult | null;
}

export default function ConnectionTest({
  onTest,
  disabled,
  testing,
  testResult,
}: Props) {
  const { t } = useTranslation();
  return (
    <div className="pt-4 mt-2 border-t border-[var(--color-border)]">
      <button
        type="button"
        className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium cursor-pointer border transition-colors duration-150 bg-transparent text-[var(--color-text-secondary)] border-[var(--color-border)] hover:border-[var(--color-accent)] hover:text-[var(--color-accent)] disabled:opacity-40 disabled:cursor-not-allowed"
        onClick={onTest}
        disabled={disabled || testing}
      >
        {testing ? <Loader2 size={14} className="animate-spin" /> : null}
        {testing ? t('providerEdit.testing') : t('providerEdit.testConnection')}
      </button>

      {testResult && (
        <div
          className={`mt-3 px-3 py-2 rounded-md text-sm border ${
            testResult.success
              ? 'bg-[color-mix(in_srgb,var(--color-success)_10%,transparent)] border-[color-mix(in_srgb,var(--color-success)_25%,transparent)] text-[var(--color-success)]'
              : 'bg-[color-mix(in_srgb,var(--color-danger)_10%,transparent)] border-[color-mix(in_srgb,var(--color-danger)_25%,transparent)] text-[var(--color-danger)]'
          }`}
        >
          {testResult.success
            ? t('providerEdit.connectionSuccess')
            : '❌ ' + testResult.message}
          {testResult.latency ? (
            <span className="ml-2 opacity-70">{testResult.latency}ms</span>
          ) : null}
        </div>
      )}
    </div>
  );
}
