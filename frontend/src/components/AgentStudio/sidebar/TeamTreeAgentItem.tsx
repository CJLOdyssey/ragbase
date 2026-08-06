import { memo } from 'react';
import { createPortal } from 'react-dom';
import { MoreVertical, Pencil, Trash2, Settings, Lock } from 'lucide-react';
import type { Agent } from '../../../types/AgentStudio';
import type { TFunction } from 'i18next';
import type * as React from 'react';

interface TeamTreeAgentItemProps {
  agent: Agent;
  teamId: string;
  selectedAgentId: string | null;
  isAuthenticated: boolean;
  openLoginModal: () => void;
  editingAgent: string | null;
  editAgentName: string;
  openAgentMenu: string | null;
  menuPosition: { top: number; left: number };
  handleAgentClick: (agent: Agent) => void;
  onEditAgent?: (agent: Agent) => void;
  setOpenAgentMenu: (id: string | null) => void;
  setConfirmDelete: (val: { type: 'agent'; teamId: string; agentId: string } | null) => void;
  toggleAgentMenu: (agentId: string, event: React.MouseEvent) => void;
  startEditAgent: (agent: Agent) => void;
  saveAgentName: () => void;
  handleAgentBlur: () => void;
  onAgentNameChange: (value: string) => void;
  t: TFunction;
}

const TeamTreeAgentItem = memo(function TeamTreeAgentItem({
  agent,
  teamId,
  selectedAgentId,
  isAuthenticated,
  openLoginModal,
  editingAgent,
  editAgentName,
  openAgentMenu,
  menuPosition,
  handleAgentClick,
  onEditAgent,
  setOpenAgentMenu,
  setConfirmDelete,
  toggleAgentMenu,
  startEditAgent,
  saveAgentName,
  handleAgentBlur,
  onAgentNameChange,
  t,
}: TeamTreeAgentItemProps) {
  return (
    <div
      className={`group flex items-center pl-1${selectedAgentId === agent.id ? ' active' : ''}`}
    >
      {editingAgent === agent.id ? (
        <div className="flex-1 min-w-0">
          <input
            className="w-full py-1 px-1.5 border border-[var(--color-accent)] rounded text-sm text-[var(--color-text-primary)] bg-transparent outline-none font-[inherit]"
            value={editAgentName}
            onChange={(e) => onAgentNameChange(e.target.value)}
            onBlur={handleAgentBlur}
            onKeyDown={(e) => {
              if (e.key === 'Enter') saveAgentName();
            }}
            autoFocus
          />
        </div>
      ) : (
        <>
          <button
            className="flex items-center gap-1.5 py-2 px-1.5 rounded-md cursor-pointer transition-all duration-150 border-none bg-transparent flex-1 min-w-0 min-h-[34px] text-[var(--color-text-secondary)] text-base text-left hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
            onClick={() => handleAgentClick(agent)}
          >
            <span className="text-base font-normal overflow-hidden text-ellipsis whitespace-nowrap flex-1 min-w-0 leading-[1.3] tracking-[-0.01em]">{agent.name}</span>
            <span
              className="opacity-0 transition-all duration-150 flex items-center justify-center w-[24px] h-[24px] shrink-0 rounded cursor-pointer text-[var(--color-text-muted)] group-hover:opacity-50 hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] hover:opacity-100"
              onClick={(e) => {
                e.stopPropagation();
                toggleAgentMenu(agent.id, e);
              }}
            >
              <MoreVertical size={15} />
            </span>
          </button>

          {openAgentMenu === agent.id && createPortal(
            <div
              className="bg-[var(--color-surface-overlay)] rounded-xl p-1 min-w-[124px] z-[99999]"
              style={{ position: 'fixed', top: menuPosition.top, left: menuPosition.left, boxShadow: 'rgba(0,0,0,0.2) 0px 0px 1px 0px, rgba(0,0,0,0.02) 0px 0px 4px 0px, rgba(0,0,0,0.08) 0px 12px 32px 0px' }}
            >
              <button
                style={{ padding: "8px 10px", borderRadius: 'var(--radius-btn)' }}
                className="flex items-center gap-2 cursor-pointer transition-colors duration-150 border-none bg-transparent w-full text-base text-[var(--color-text-secondary)] text-left hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
                onClick={() => {
                  if (!isAuthenticated) { openLoginModal(); return; }
                  if (onEditAgent) onEditAgent(agent);
                  setOpenAgentMenu(null);
                }}
                title={!isAuthenticated ? '登录后解锁功能' : undefined}
              >
                {isAuthenticated ? <Settings size={15} /> : <Lock size={15} />}
                <span>{t('sidebar.edit')}</span>
              </button>
              <button
                style={{ padding: "8px 10px", borderRadius: 'var(--radius-btn)' }}
                className="flex items-center gap-2 cursor-pointer transition-colors duration-150 border-none bg-transparent w-full text-base text-[var(--color-text-secondary)] text-left hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
                onClick={() => {
                  if (!isAuthenticated) { openLoginModal(); return; }
                  startEditAgent(agent);
                }}
                title={!isAuthenticated ? '登录后解锁功能' : undefined}
              >
                {isAuthenticated ? <Pencil size={15} /> : <Lock size={15} />}
                <span>{t('sidebar.rename')}</span>
              </button>
              <button
                style={{ padding: "8px 10px", borderRadius: 'var(--radius-btn)' }}
                className="flex items-center gap-2 cursor-pointer transition-colors duration-150 border-none bg-transparent w-full text-base text-[var(--color-danger)] text-left hover:bg-[color-mix(in_srgb,var(--color-danger)_10%,transparent)]"
                onClick={() => {
                  if (!isAuthenticated) { openLoginModal(); return; }
                  setConfirmDelete({ type: 'agent', teamId, agentId: agent.id });
                  setOpenAgentMenu(null);
                }}
                title={!isAuthenticated ? '登录后解锁功能' : undefined}
              >
                {isAuthenticated ? <Trash2 size={15} /> : <Lock size={15} />}
                <span>{t('sidebar.delete')}</span>
              </button>
            </div>,
            document.body,
          )}
        </>
      )}
    </div>
  );
});

export default TeamTreeAgentItem;
