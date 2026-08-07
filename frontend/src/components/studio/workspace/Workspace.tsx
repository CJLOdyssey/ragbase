import React from 'react';
import type { WorkspaceTab } from '../../../types/studio';
import { getAgentType, getWorkspaceTabs } from '../../../utils/workspaceConfig';
import {
  FileCode,
  FolderKanban,
  Maximize2,
  PanelRightClose,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface WorkspaceProps {
  selectedAgentId: string | null;
  activeTab: WorkspaceTab;
  setActiveTab: (tab: WorkspaceTab) => void;
  isWorkspaceOpen: boolean;
  setIsWorkspaceOpen: (open: boolean) => void;
  toggleWorkspaceFullscreen: () => void;
  workspaceRef: React.Ref<HTMLElement>;
}

export default function Workspace({
  selectedAgentId,
  activeTab,
  setActiveTab,
  isWorkspaceOpen,
  setIsWorkspaceOpen,
  toggleWorkspaceFullscreen,
  workspaceRef,
}: WorkspaceProps) {
  const { t } = useTranslation();
  if (!selectedAgentId || !isWorkspaceOpen) return null;

  return (
    <aside
      className="w-[clamp(280px,22vw,360px)] flex flex-col border-l border-[var(--color-border)] bg-[var(--color-surface)] flex-shrink-0 overflow-hidden"
      ref={workspaceRef}
    >
      <header className="flex items-center justify-between px-2 py-1.5 border-b border-[var(--color-border)] bg-[var(--color-surface-raised)] flex-shrink-0">
        <div className="flex items-center gap-0.5 overflow-x-auto">
          {getWorkspaceTabs(getAgentType(selectedAgentId)).map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs cursor-pointer border-none transition-colors duration-150 whitespace-nowrap ${activeTab === tab.id ? 'bg-[var(--color-accent)]/10 text-[var(--color-accent)] font-medium' : 'bg-transparent text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]'}`}
            >
              <tab.icon size={14} />
              {t(tab.labelKey)}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-0.5 flex-shrink-0">
          <button
            className="p-1 rounded bg-transparent border-none text-[var(--color-text-muted)] cursor-pointer transition-colors flex items-center justify-center hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
            title={t('workspace.fullscreen')}
            onClick={toggleWorkspaceFullscreen}
          >
            <Maximize2 size={14} />
          </button>
          <button
            onClick={() => setIsWorkspaceOpen(false)}
            className="p-1 rounded bg-transparent border-none text-[var(--color-text-muted)] cursor-pointer transition-colors flex items-center justify-center hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
            title={t('workspace.collapse')}
          >
            <PanelRightClose size={14} />
          </button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-[200px] border-r border-[var(--color-border)] flex flex-col bg-[var(--color-surface-raised)] flex-shrink-0">
          <div className="flex items-center gap-2 p-3 text-xs font-semibold text-[var(--color-text-secondary)] border-b border-[var(--color-border)] uppercase tracking-[0.5px]">
            <FolderKanban size={14} />
            <span>{t('workspace.fileExplorer')}</span>
          </div>
          <div className="flex-1 overflow-y-auto py-2">
            <div className="flex flex-col items-center justify-center py-8 px-4 text-[var(--color-text-muted)] text-center">
              <FileCode size={32} className="mb-2 opacity-50" />
              <p className="text-xs m-0">{t('workspace.emptyFiles')}</p>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto flex flex-col">
          {activeTab.includes('preview') ? (
            <div className="h-full w-full flex items-center justify-center bg-[var(--color-surface-raised)] relative">
              <div className="flex flex-col items-center justify-center text-[var(--color-text-muted)] text-center">
                <FileCode size={32} className="mb-2 opacity-50" />
                <p className="text-xs m-0">{t('workspace.noPreview')}</p>
              </div>
            </div>
          ) : activeTab.includes('test') ? (
            <div className="p-4">
              <div className="flex items-center gap-2 mb-4 pb-3 border-b border-[var(--color-border)]">
                <FileCode size={14} />
                <span>{t('workspace.testRunner')}</span>
              </div>
              <div className="flex flex-col gap-2">
                <p className="text-sm text-[var(--color-text-muted)] text-center py-8 m-0">
                  {t('workspace.noTests')}
                </p>
              </div>
            </div>
          ) : (
            <div className="font-mono text-sm p-4 text-[var(--color-text-primary)] leading-[1.6] overflow-x-auto">
              <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)] mb-4">
                <FileCode size={12} />{' '}
                <span className="text-[var(--color-accent)]">Agent</span>{' '}
                {t('workspace.committedJustNow')}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between px-3 py-1.5 border-t border-[var(--color-border)] bg-[var(--color-surface-raised)] text-xs text-[var(--color-text-muted)] flex-shrink-0">
        <div className="flex items-center gap-2">
          <span>{t('workspace.noErrors')}</span>
        </div>
      </div>
    </aside>
  );
}
