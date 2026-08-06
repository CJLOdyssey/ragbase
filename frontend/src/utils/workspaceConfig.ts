import { Code2, Play, Folder, TestTube2 } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { AgentType, WorkspaceTab } from '../types/AgentStudio';

export const getAgentType = (agentId: string): AgentType => {
  if (agentId === 'ui') return 'ui';
  if (agentId === 'frontend') return 'frontend';
  if (agentId === 'backend') return 'backend';
  return 'frontend';
};

export const getWorkspaceTabs = (agentType: AgentType): { id: WorkspaceTab; labelKey: string; icon: LucideIcon }[] => {
  switch (agentType) {
    case 'ui':
      return [
        { id: 'ui-code', labelKey: 'workspace.tab.uiCode', icon: Code2 },
        { id: 'ui-preview', labelKey: 'workspace.tab.uiPreview', icon: Play },
      ];
    case 'frontend':
      return [
        { id: 'frontend-code', labelKey: 'workspace.tab.frontendCode', icon: Folder },
        { id: 'frontend-test', labelKey: 'workspace.tab.frontendTest', icon: TestTube2 },
        { id: 'frontend-preview', labelKey: 'workspace.tab.frontendPreview', icon: Play },
      ];
    case 'backend':
      return [
        { id: 'backend-code', labelKey: 'workspace.tab.backendCode', icon: Folder },
        { id: 'backend-test', labelKey: 'workspace.tab.backendTest', icon: TestTube2 },
      ];
    default:
      return [
        { id: 'code', labelKey: 'workspace.tab.code', icon: Code2 },
        { id: 'preview', labelKey: 'workspace.tab.preview', icon: Play },
      ];
  }
};
