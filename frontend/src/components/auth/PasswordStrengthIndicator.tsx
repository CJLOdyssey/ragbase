import type { TFunction } from 'i18next';
import { useTranslation } from 'react-i18next';

interface Props {
  password: string;
  validated: boolean;
}

const SPECIAL_CHARS = '!@#$%^&*()_+-=[]{}|;\':",./<>?~';

interface Check {
  label: string;
  pass: boolean;
}

function checks(password: string, t: TFunction): Check[] {
  const common = new Set([
    'password',
    'password123',
    'admin123',
    'admin888',
    '12345678',
    'qwerty123',
    'letmein',
    'welcome',
    'monkey',
    'dragon',
    'passw0rd',
    'abc123',
    '123456789',
    'iloveyou',
    'trustno1',
    'sunshine',
    'master',
    'access',
    'shadow',
    'michael',
  ]);
  return [
    { label: t('auth.pwdLen8'), pass: password.length >= 8 },
    { label: t('auth.pwdNumber'), pass: /\d/.test(password) },
    { label: t('auth.pwdLower'), pass: /[a-z]/.test(password) },
    { label: t('auth.pwdUpper'), pass: /[A-Z]/.test(password) },
    {
      label: t('auth.pwdSpecial'),
      pass: [...password].some((c) => SPECIAL_CHARS.includes(c)),
    },
    { label: t('auth.pwdCommon'), pass: !common.has(password.toLowerCase()) },
  ];
}

export default function PasswordStrengthIndicator({
  password,
  validated,
}: Props) {
  const { t } = useTranslation();
  if (!password) return null;

  const items = checks(password, t);
  const passed = items.filter((c) => c.pass).length;
  const total = items.length;
  const failed = items.filter((c) => !c.pass);

  return (
    <div className="mt-1.5 mb-2.5">
      <div className="flex gap-1 mb-1.5">
        {items.map((c, i) => (
          <div
            key={i}
            className="flex-1 h-[3px] rounded-sm transition-[background] duration-200"
            style={{
              background: c.pass
                ? 'var(--color-success)'
                : 'var(--color-border)',
            }}
          />
        ))}
      </div>

      {validated && failed.length > 0 && (
        <div className="text-xs text-[var(--color-text-tertiary)] leading-relaxed">
          {failed.map((c, i) => (
            <span key={i}>
              {i > 0 && ' · '}○ {c.label}
            </span>
          ))}
        </div>
      )}

      {validated && passed === total && (
        <div className="text-xs text-[var(--color-success)]">
          {t('auth.allMet')}
        </div>
      )}
    </div>
  );
}
