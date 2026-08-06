import { memo, useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Users, Plus, ChevronDown, MoreVertical, Pencil, Trash2, Pin, PinOff, Lock } from 'lucide-react';
import type { Team, Agent } from '../../../types/AgentStudio';
import { useTranslation } from 'react-i18next';
import { validateName } from '../../../utils/validation';
import TeamTreeAgentItem from './TeamTreeAgentItem';
import ConfirmDialog from '@/components/shared/ConfirmDialog';
import type * as React from 'react';

interface TeamTreeProps {
  teams: Team[];
  selectedAgentId: string | null;
  isAuthenticated: boolean;
  openLoginModal: () => void;
  toggleTeam: (teamId: string) => void;
  handleAddTeam: () => void;
  handleAddAgent: (teamId: string) => void;
  handleDeleteTeam: (teamId: string) => void;
  handleDeleteAgent: (teamId: string, agentId: string) => void;
  handleRenameTeam: (teamId: string, name: string) => void;
  handleRenameAgent: (agentId: string, name: string) => void;
  handleTogglePinTeam: (teamId: string) => void;
  handleAgentClick: (agent: Agent) => void;
  onEditAgent?: (agent: Agent) => void;
  onTeamChat?: (teamId: string) => void;
}

const TeamTree = memo(function TeamTree({
  teams,
  selectedAgentId,
  isAuthenticated,
  openLoginModal,
  toggleTeam,
  handleAddTeam,
  handleAddAgent,
  handleDeleteTeam,
  handleDeleteAgent,
  handleRenameTeam,
  handleRenameAgent,
  handleTogglePinTeam,
  handleAgentClick,
  onEditAgent,
  onTeamChat,
}: TeamTreeProps) {
  const { t } = useTranslation();
  const [openTeamMenu, setOpenTeamMenu] = useState<string | null>(null);
  const [openAgentMenu, setOpenAgentMenu] = useState<string | null>(null);
  const [menuPosition, setMenuPosition] = useState<{ top: number; left: number }>({ top: 0, left: 0 });
  const [editingTeam, setEditingTeam] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [confirmDelete, setConfirmDelete] = useState<{ type: 'team' | 'agent'; teamId: string; agentId?: string } | null>(null);
  const [validationWarning, setValidationWarning] = useState<{ message: string; onConfirm?: () => void } | null>(null);
  const [editingAgent, setEditingAgent] = useState<string | null>(null);
  const [editAgentName, setEditAgentName] = useState('');

  useEffect(() => {
    if (!openTeamMenu && !openAgentMenu) return;
    const handleClickOutside = () => {
      setOpenTeamMenu(null);
      setOpenAgentMenu(null);
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [openTeamMenu, openAgentMenu]);

  const startEditTeam = (team: Team) => {
    setEditingTeam(team.id);
    setEditName(team.name);
    setOpenTeamMenu(null);
  };

  const saveTeamName = (teamId: string) => {
    const name = editName.trim();
    if (!name) {
      setValidationWarning({ message: t('sidebar.nameNotEmpty') });
      return;
    }
    const existingNames = teams.filter((t) => t.id !== teamId).map((t) => t.name);
    const validation = validateName(name, existingNames);
    if (!validation.valid) {
      setValidationWarning({ message: validation.error! });
      return;
    }
    handleRenameTeam(teamId, name);
    setEditingTeam(null);
    setEditName('');
  };

  const handleTeamBlur = (teamId: string) => {
    setTimeout(() => {
      if (editingTeam === teamId) {
        saveTeamName(teamId);
      }
    }, 100);
  };

  const onTeamNameChange = (value: string) => {
    setEditName(value);
  };

  const startEditAgent = (agent: Agent) => {
    setEditingAgent(agent.id);
    setEditAgentName(agent.name);
    setOpenAgentMenu(null);
  };

  const saveAgentName = () => {
    const name = editAgentName.trim();
    if (!name) {
      setValidationWarning({ message: t('sidebar.nameNotEmpty') });
      return;
    }
    if (!editingAgent) return;
    let existingNames: string[] = [];
    teams.forEach((team) => {
      if (team.agents.some((a) => a.id === editingAgent)) {
        existingNames = team.agents.filter((a) => a.id !== editingAgent).map((a) => a.name);
      }
    });
    const validation = validateName(name, existingNames);
    if (!validation.valid) {
      setValidationWarning({ message: validation.error! });
      return;
    }
    handleRenameAgent(editingAgent, name);
    setEditingAgent(null);
    setEditAgentName('');
  };

  const handleAgentBlur = () => {
    setTimeout(() => {
      if (editingAgent) {
        saveAgentName();
      }
    }, 100);
  };

  const onAgentNameChange = (value: string) => {
    setEditAgentName(value);
  };

  const confirmDeleteAction = () => {
    if (!confirmDelete) return;
    if (confirmDelete.type === 'team') {
      handleDeleteTeam(confirmDelete.teamId);
    } else if (confirmDelete.agentId) {
      handleDeleteAgent(confirmDelete.teamId, confirmDelete.agentId);
    }
    setConfirmDelete(null);
  };

  const toggleTeamMenu = (teamId: string, event: React.MouseEvent) => {
    if (openTeamMenu === teamId) {
      setOpenTeamMenu(null);
    } else {
      const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
      setMenuPosition({ top: rect.bottom + 4, left: rect.right - 124 });
      setOpenTeamMenu(teamId);
      setOpenAgentMenu(null);
    }
  };

  const toggleAgentMenu = (agentId: string, event: React.MouseEvent) => {
    if (openAgentMenu === agentId) {
      setOpenAgentMenu(null);
    } else {
      const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
      setMenuPosition({ top: rect.bottom + 4, left: rect.right - 124 });
      setOpenAgentMenu(agentId);
      setOpenTeamMenu(null);
    }
  };

  return (
    <div className="flex flex-col">
      <div className="flex items-center justify-between py-0.5 shrink-0" style={{ paddingLeft: 8, paddingRight: 9 }}>
        <div className="text-sm font-medium leading-[22px] text-[var(--color-text-tertiary)]">
          {t('sidebar.myTeams')}
        </div>
        <button
          className={`bg-transparent border-none p-1 rounded cursor-pointer text-[var(--color-text-tertiary)] flex items-center justify-center transition-colors duration-150 hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-accent)]${!isAuthenticated ? ' opacity-35' : ' opacity-50'}`}
          onClick={isAuthenticated ? handleAddTeam : () => openLoginModal()}
          title={isAuthenticated ? t('sidebar.createTeam') : '登录后解锁功能'}
        >
          {isAuthenticated ? <Plus size={14} /> : <Lock size={14} />}
        </button>
      </div>
      <div className="p-0 flex flex-col gap-0.5 shrink-0 max-h-[35vh] overflow-y-auto overflow-x-hidden">
        {teams.length === 0 && (
            <div className="flex flex-col items-center justify-center text-center py-8 px-4">
            <p className="text-sm text-[var(--color-text-muted)] m-0">
              {t('sidebar.noTeams', '暂无团队，点击 + 创建')}
            </p>
          </div>
        )}
        {teams.map((team) => (
          <div key={team.id} className="mb-px rounded-md overflow-visible">
            <div className="group flex items-center gap-1 py-2 pl-2 pr-2 cursor-pointer transition-colors duration-150 bg-transparent min-h-[36px] rounded-md hover:bg-[var(--color-surface-hover)]" onClick={() => toggleTeam(team.id)}>
              <button
                className="bg-transparent border-none p-0.5 rounded cursor-pointer text-[var(--color-text-muted)] flex items-center justify-center transition-[color,background,opacity] duration-150 flex-shrink-0 w-[24px] h-[24px] opacity-60 hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] hover:opacity-100"
              >
                <ChevronDown
                  size={15}
                  className={`transition-transform duration-200 ${team.isExpanded ? '' : '-rotate-90'}`}
                />
              </button>

              {team.isPinned && (
                <Pin size={13} className="text-[var(--color-accent-soft)] flex-shrink-0 mr-[-2px]" />
              )}

              {editingTeam === team.id ? (
                <div className="flex-1 min-w-0">
                  <input
                    className="w-full py-1 px-1.5 border border-[var(--color-accent)] rounded text-base font-medium text-[var(--color-text-primary)] bg-transparent outline-none font-[inherit]"
                    value={editName}
                    onChange={(e) => onTeamNameChange(e.target.value)}
                    onBlur={() => handleTeamBlur(team.id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') saveTeamName(team.id);
                    }}
                    autoFocus
                  />
                </div>
              ) : (
                <>
                  <span className="text-base font-medium text-[var(--color-text-primary)] overflow-hidden text-ellipsis whitespace-nowrap flex-1 min-w-0 leading-[1] tracking-[-0.01em]">{team.name}</span>
                  <span className="text-sm text-[var(--color-text-tertiary)] shrink-0 font-normal opacity-70 min-w-[16px] text-center">{team.agents.length}</span>
                  {onTeamChat && (
                    <button
                      className="bg-transparent border-none p-1 rounded cursor-pointer text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-accent)] flex items-center justify-center w-[24px] h-[24px] shrink-0 transition-all duration-150"
                      onClick={(e) => { e.stopPropagation(); onTeamChat(team.id); }}
                      title="团队对话"
                    >
                      <Users size={15} />
                    </button>
                  )}
                  <button
                    className="bg-transparent border-none p-1 rounded cursor-pointer text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)] flex items-center justify-center w-[24px] h-[24px] shrink-0 transition-all duration-150"
                    onClick={(e) => { e.stopPropagation(); toggleTeamMenu(team.id, e); }}
                    title={t('sidebar.moreOptions')}
                  >
                    <MoreVertical size={15} />
                  </button>
                </>
              )}
            </div>

            {openTeamMenu === team.id && createPortal(
              <div
                className="bg-[var(--color-surface-overlay)] rounded-xl p-1 min-w-[124px] z-[99999]"
                style={{ position: 'fixed', top: menuPosition.top, left: menuPosition.left, boxShadow: 'rgba(0,0,0,0.2) 0px 0px 1px 0px, rgba(0,0,0,0.02) 0px 0px 4px 0px, rgba(0,0,0,0.08) 0px 12px 32px 0px' }}
              >
                <button
                  className="flex items-center gap-2 cursor-pointer transition-colors duration-150 border-none bg-transparent w-full text-base text-[var(--color-text-secondary)] text-left hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
                  style={{ padding: '8px 10px', borderRadius: 'var(--radius-btn)' }}
                  onClick={() => {
                    if (!isAuthenticated) { openLoginModal(); return; }
                    handleAddAgent(team.id);
                    setOpenTeamMenu(null);
                  }}
                  title={!isAuthenticated ? '登录后解锁功能' : undefined}
                >
                  {isAuthenticated ? <Plus size={15} /> : <Lock size={15} />}
                  <span>{t('sidebar.addAgent')}</span>
                </button>
                <button
                  style={{ padding: "8px 10px", borderRadius: 'var(--radius-btn)' }}
                  className="flex items-center gap-2 cursor-pointer transition-colors duration-150 border-none bg-transparent w-full text-base text-[var(--color-text-secondary)] text-left hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
                  onClick={() => {
                    if (!isAuthenticated) { openLoginModal(); return; }
                    startEditTeam(team);
                  }}
                  title={!isAuthenticated ? '登录后解锁功能' : undefined}
                >
                  {isAuthenticated ? <Pencil size={15} /> : <Lock size={15} />}
                  <span>{t('workstation.rename')}</span>
                </button>
                <button
                  style={{ padding: "8px 10px", borderRadius: 'var(--radius-btn)' }}
                  className="flex items-center gap-2 cursor-pointer transition-colors duration-150 border-none bg-transparent w-full text-base text-[var(--color-text-secondary)] text-left hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
                  onClick={() => {
                    if (!isAuthenticated) { openLoginModal(); return; }
                    handleTogglePinTeam(team.id);
                    setOpenTeamMenu(null);
                  }}
                  title={!isAuthenticated ? '登录后解锁功能' : undefined}
                >
                  {isAuthenticated ? (team.isPinned ? <PinOff size={15} /> : <Pin size={15} />) : <Lock size={15} />}
                  <span>{team.isPinned ? t('sidebar.unpin') : t('sidebar.pin')}</span>
                </button>
                <button
                  style={{ padding: "8px 10px", borderRadius: 'var(--radius-btn)' }}
                  className="flex items-center gap-2 cursor-pointer transition-colors duration-150 border-none bg-transparent w-full text-base text-[var(--color-danger)] text-left hover:bg-[color-mix(in_srgb,var(--color-danger)_10%,transparent)]"
                  onClick={() => {
                    if (!isAuthenticated) { openLoginModal(); return; }
                    setConfirmDelete({ type: 'team', teamId: team.id });
                    setOpenTeamMenu(null);
                  }}
                  title={!isAuthenticated ? '登录后解锁功能' : undefined}
                >
                  {isAuthenticated ? <Trash2 size={15} /> : <Lock size={15} />}
                  <span>{t('workstation.delete')}</span>
                </button>
              </div>,
              document.body,
            )}

            {team.isExpanded && (
              <div className="py-px" style={{ marginLeft: 26 }}>
                {team.agents.map((agent) => (
                  <TeamTreeAgentItem
                    key={agent.id}
                    agent={agent}
                    teamId={team.id}
                    selectedAgentId={selectedAgentId}
                    isAuthenticated={isAuthenticated}
                    openLoginModal={openLoginModal}
                    editingAgent={editingAgent}
                    editAgentName={editAgentName}
                    openAgentMenu={openAgentMenu}
                    menuPosition={menuPosition}
                    handleAgentClick={handleAgentClick}
                    onEditAgent={onEditAgent}
                    setOpenAgentMenu={setOpenAgentMenu}
                    setConfirmDelete={setConfirmDelete}
                    toggleAgentMenu={toggleAgentMenu}
                    startEditAgent={startEditAgent}
                    saveAgentName={saveAgentName}
                    handleAgentBlur={handleAgentBlur}
                    onAgentNameChange={onAgentNameChange}
                    t={t}
                  />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {confirmDelete && (
        <ConfirmDialog
          title={t('confirm.title')}
          message={
            confirmDelete.type === 'team'
              ? t('confirm.deleteTeamConfirm')
              : t('confirm.deleteAgentConfirm')
          }
          confirmLabel={t('sidebar.delete')}
          cancelLabel={t('common.cancel')}
          danger
          onConfirm={confirmDeleteAction}
          onCancel={() => setConfirmDelete(null)}
        />
      )}

      {validationWarning && (
        <ConfirmDialog
          title={t('confirm.tip')}
          message={validationWarning.message}
          confirmLabel={t('confirm.confirm')}
          danger
          onConfirm={() => setValidationWarning(null)}
          onCancel={() => setValidationWarning(null)}
        />
      )}
    </div>
  );
});

export default TeamTree;
