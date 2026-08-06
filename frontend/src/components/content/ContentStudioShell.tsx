import { useTranslation } from 'react-i18next';

export default function ContentStudioShell() {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col h-screen bg-[var(--color-surface)] text-[var(--color-text-primary)]">
      <main id="main-content" className="flex-1 flex items-center justify-center min-h-0">
        <div className="text-center">
          <h1 className="text-2xl font-semibold mb-2">{t('app.title')}</h1>
          <p className="text-base text-[var(--color-text-muted)] m-0">{t('app.subtitle')}</p>
        </div>
      </main>
    </div>
  );
}
