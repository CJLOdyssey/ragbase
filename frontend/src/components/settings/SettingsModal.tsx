import { useState } from 'react';
import { changeLanguage } from '../../i18n/index';
import ToggleSwitch from '@/components/shared/ToggleSwitch';
import { Modal as AntdModal } from 'antd';
import { Globe, Info, Shield } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import ChangePasswordForm from './ChangePasswordForm';
import { useSettings } from '../../contexts/SettingsContext';

interface Props {
  onClose: () => void;
}

type SettingsTab = 'general' | 'security' | 'about';

const VERSION = '1.0.0';
const BUILD_TIME = '2026-05-08';

export default function SettingsModal({ onClose }: Props) {
  const { t, i18n } = useTranslation();
  const { settings, updateSettings } = useSettings();
  const [activeTab, setActiveTab] = useState<SettingsTab>('general');
  const fontPct = ((settings.fontSize - 14) / 6) * 100;

  return (
    <AntdModal
      title={t('settings.title')}
      open={true}
      onCancel={onClose}
      centered
      width={970}
      className="mobile-fullscreen"
      classNames={{ container: 'flex flex-col overflow-hidden' }}
      styles={{
        container: { height: 600 },
        // antd v6 body 默认 flex:0 1 auto + min-height:auto，会被内容撑高、
        // 被 container 的 overflow-hidden 硬裁（无滚动条截断）；须约束在
        // 剩余空间内，内部 overflow-y-auto 才有滚动基准。
        body: { flex: 1, minHeight: 0 },
      }}
      footer={
        <>
          <button
            className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-surface-raised)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
            onClick={onClose}
          >
            {t('settings.cancel')}
          </button>
          <button
            className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-colors duration-150 bg-[var(--color-surface-hover)] text-[var(--color-text-primary)] hover:bg-[var(--color-surface-elevated)] disabled:bg-[var(--color-surface-hover)] disabled:text-[var(--color-text-muted)] disabled:cursor-not-allowed"
            onClick={onClose}
          >
            {t('settings.save')}
          </button>
        </>
      }
    >
      <div className="flex h-full min-h-0 flex-col overflow-hidden md:flex-row">
        {/* 移动端：顶部水平 Tab 栏；桌面端：左侧垂直 Tab 栏 */}
        <div className="flex flex-row gap-1 overflow-x-auto border-b border-[var(--color-border)] px-2 py-2 md:w-[160px] md:flex-col md:border-b-0 md:border-r md:border-r-[var(--color-border-subtle)] md:px-4 md:py-5 md:overflow-x-hidden">
          {(
            [
              ['general', Globe],
              ['security', Shield],
              ['about', Info],
            ] as const
          ).map(([tab, Icon]) => (
            <button
              key={tab}
              className={`flex items-center gap-2 whitespace-nowrap p-2 px-3 bg-transparent border-none rounded-md text-[var(--color-text-secondary)] text-sm cursor-pointer transition-[background,color] duration-150 text-left hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] md:gap-3 ${activeTab === tab ? 'bg-[var(--color-surface-hover)] text-[var(--color-text-primary)]' : ''}`}
              onClick={() => setActiveTab(tab as SettingsTab)}
            >
              <Icon size={16} />
              <span>{t('settings.' + tab)}</span>
            </button>
          ))}
        </div>

        <div className="flex-1 px-6 py-5 overflow-y-auto min-h-0">
          {activeTab === 'general' && (
            <div className="flex flex-col gap-6">
              <section>
                <h4 className="text-sm font-semibold text-[var(--color-text-primary)] mb-4 tracking-tight">
                  {t('settings.general')}
                </h4>
                <div className="flex items-center justify-between py-3">
                  <div className="flex-1">
                    <label className="block text-sm text-[var(--color-text-primary)]">
                      {t('settings.language')}
                    </label>
                    <span className="text-xs text-[var(--color-text-muted)] leading-relaxed">
                      {t('settings.languageDesc')}
                    </span>
                  </div>
                  <select
                    className="p-2 px-3 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-md text-[var(--color-text-primary)] text-sm min-w-[140px] cursor-pointer focus:border-[var(--color-accent)]"
                    value={i18n.language}
                    onChange={(e) => changeLanguage(e.target.value)}
                  >
                    <option value="zh-CN">{t('lang.zh')}</option>
                    <option value="en-US">English</option>
                  </select>
                </div>
              </section>

              <section>
                <h4 className="text-sm font-semibold text-[var(--color-text-primary)] mb-4 tracking-tight">
                  {t('settings.appearance')}
                </h4>
                <div className="flex items-center justify-between py-3">
                  <div className="flex-1">
                    <label className="block text-sm text-[var(--color-text-primary)]">
                      {t('settings.theme')}
                    </label>
                    <span className="text-xs text-[var(--color-text-muted)] leading-relaxed">
                      {t('settings.themeDesc')}
                    </span>
                  </div>
                  <select
                    className="p-2 px-3 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-md text-[var(--color-text-primary)] text-sm min-w-[140px] cursor-pointer focus:border-[var(--color-accent)]"
                    value={settings.theme}
                    onChange={(e) =>
                      updateSettings({
                        theme: e.target.value as 'dark' | 'light' | 'system',
                      })
                    }
                  >
                    <option value="dark">{t('settings.dark')}</option>
                    <option value="light">{t('settings.light')}</option>
                    <option value="system">{t('settings.system')}</option>
                  </select>
                </div>
                <div className="flex items-center justify-between py-3">
                  <div className="flex-1">
                    <label className="block text-sm text-[var(--color-text-primary)]">
                      {t('settings.fontSize')}
                    </label>
                    <span className="text-xs text-[var(--color-text-muted)] leading-relaxed">
                      {t('settings.fontSizeDesc')}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="range"
                      min="14"
                      max="20"
                      step="1"
                      value={settings.fontSize}
                      onChange={(e) =>
                        updateSettings({ fontSize: Number(e.target.value) })
                      }
                      style={{
                        background: `linear-gradient(to right, var(--color-accent) 0%, var(--color-accent) ${fontPct}%, var(--color-surface-hover) ${fontPct}%, var(--color-surface-hover) 100%)`,
                      }}
                      className="w-[120px] h-[6px] rounded-[var(--radius-btn)] appearance-none cursor-pointer accent-[var(--color-accent)]"
                    />
                    <span className="text-sm font-semibold text-[var(--color-text-secondary)] min-w-[32px] text-right">
                      {settings.fontSize}px
                    </span>
                  </div>
                </div>
              </section>

              <section>
                <h4 className="text-sm font-semibold text-[var(--color-text-primary)] mb-4 tracking-tight">
                  AI Chat
                </h4>
                <div className="flex items-center justify-between py-3">
                  <div className="flex-1">
                    <label className="block text-sm text-[var(--color-text-primary)]">
                      {t('settings.sendMode')}
                    </label>
                    <span className="text-xs text-[var(--color-text-muted)] leading-relaxed">
                      {t('settings.sendModeDesc')}
                    </span>
                  </div>
                  <select
                    className="p-2 px-3 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-md text-[var(--color-text-primary)] text-sm min-w-[140px] cursor-pointer focus:border-[var(--color-accent)]"
                    value={settings.sendMode}
                    onChange={(e) =>
                      updateSettings({
                        sendMode: e.target.value as 'enter' | 'ctrl-enter',
                      })
                    }
                  >
                    <option value="enter">{t('settings.enterSend')}</option>
                    <option value="ctrl-enter">Ctrl + Enter</option>
                  </select>
                </div>
                <div className="flex items-center justify-between py-3">
                  <div className="flex-1">
                    <label className="block text-sm text-[var(--color-text-primary)]">
                      {t('settings.autoSave')}
                    </label>
                    <span className="text-xs text-[var(--color-text-muted)] leading-relaxed">
                      {t('settings.autoSaveDesc')}
                    </span>
                  </div>
                  <ToggleSwitch
                    checked={settings.autoSave}
                    onChange={(v) => updateSettings({ autoSave: v })}
                  />
                </div>
                <div className="flex items-center justify-between py-3">
                  <div className="flex-1">
                    <label className="block text-sm text-[var(--color-text-primary)]">
                      {t('settings.streamOutput')}
                    </label>
                    <span className="text-xs text-[var(--color-text-muted)] leading-relaxed">
                      {t('settings.streamOutputDesc')}
                    </span>
                  </div>
                  <ToggleSwitch
                    checked={settings.streamOutput}
                    onChange={(v) => updateSettings({ streamOutput: v })}
                  />
                </div>
              </section>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="flex flex-col gap-6">
              <section>
                <h4 className="text-sm font-semibold text-[var(--color-text-primary)] mb-4 tracking-tight">
                  {t('settings.changePassword.title')}
                </h4>
                <ChangePasswordForm />
              </section>
            </div>
          )}

          {activeTab === 'about' && (
            <div>
              <h4>{t('settings.about')}</h4>
              <AppIdentity />
              <InfoGrid />
            </div>
          )}
        </div>
      </div>
    </AntdModal>
  );
}

function AppIdentity() {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        padding: '24px 20px',
        width: '100%',
        background: 'var(--color-surface-raised)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-card)',
        marginBottom: 16,
      }}
    >
      <div
        style={{
          width: 52,
          height: 52,
          borderRadius: 14,
          background:
            'linear-gradient(135deg, color-mix(in srgb, var(--color-accent) 40%, transparent), color-mix(in srgb, var(--color-accent) 10%, transparent))',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--color-accent)',
          flexShrink: 0,
          boxShadow:
            '0 2px 8px color-mix(in srgb, var(--color-accent) 20%, transparent)',
        }}
      >
        <Info size={24} />
      </div>
      <div>
        <div
          style={{
            fontSize: 18,
            fontWeight: 650,
            color: 'var(--color-text-primary)',
            letterSpacing: '-0.02em',
          }}
        >
          RagBase
        </div>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            marginTop: 4,
          }}
        >
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
              padding: '2px 8px',
              borderRadius: 4,
              background:
                'color-mix(in srgb, var(--color-accent) 12%, transparent)',
              color: 'var(--color-accent)',
              fontSize: 11,
              fontWeight: 500,
            }}
          >
            v {VERSION}
          </span>
          <span
            style={{
              fontSize: 11,
              color: 'var(--color-text-muted)',
            }}
          >
            {BUILD_TIME}
          </span>
        </div>
      </div>
    </div>
  );
}

function InfoGrid() {
  const rows = [
    { label: 'Version', value: VERSION },
    { label: 'Build', value: BUILD_TIME },
    { label: 'Frontend', value: 'React 18 + Vite 6' },
    { label: 'Backend', value: 'FastAPI + Python 3.12' },
    { label: 'License', value: 'MIT' },
  ];
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 1,
        width: '100%',
        background: 'var(--color-border)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-card)',
        overflow: 'hidden',
      }}
    >
      {rows.map((row) => (
        <div
          key={row.label}
          style={{
            padding: '12px 16px',
            background: 'var(--color-surface-raised)',
            fontSize: 13,
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
          }}
        >
          <span
            style={{
              color: 'var(--color-text-muted)',
              fontSize: 11,
            }}
          >
            {row.label}
          </span>
          <span
            style={{
              color: 'var(--color-text-primary)',
              fontWeight: 450,
            }}
          >
            {row.value}
          </span>
        </div>
      ))}
    </div>
  );
}
