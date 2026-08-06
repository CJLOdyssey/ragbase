type AgentRole = string;

export interface AgentConfig {
  id: string;
  name: string;
  role_identifier: string;
  system_prompt: string;
  output_constraints?: string | null;
  tools?: string | null;
  mcp?: string | null;
  skills?: string | null;
  model: string | null;
  temperature: number | null;
  order: number;
  is_active: boolean;
  is_approver: boolean;
  icon: string;
  created_at?: string | null;
}

export interface WsMessage {
  type:
    | 'message'
    | 'stream'
    | 'thinking_stream'
    | 'thinking_done'
    | 'status'
    | 'result'
    | 'error'
    | 'client_action';
  role?: AgentRole;
  agent_name?: string;
  content?: string;
  thinking?: string;
  round_number?: number;
  status?: string;
  error?: string;
  approved?: boolean;
  pm_document?: string;
  code?: string;
  review?: string;
  action?: { type: string; url?: string; [key: string]: unknown };
}

export interface RunResult {
  requirement: string;
  pm_document: string;
  code: string;
  review: string;
  approved: boolean;
  status: string;
}

export interface ChatMessage {
  id: string;
  role: AgentRole;
  agent_name: string;
  content: string;
  thinking?: string;
  thinkingDone?: boolean;
  round_number: number;
  created_at: string | null;
  versions?: string[];
  thinkingVersions?: string[];
  currentVersion?: number;
  /** User-message edit history (older edits first; content is the active one) */
  userVersions?: string[];
  currentUserVersion?: number;
  thumbsFeedback?: 'up' | 'down' | null;
  interrupted?: boolean;
}

export interface ProjectRun {
  id: string;
  session_id?: string | null;
  requirement: string;
  pm_document: string;
  code: string;
  review: string;
  approved: boolean;
  status: string;
  created_at: string | null;
  updated_at: string | null;
  messages?: ChatMessage[];
}

export interface SessionItem {
  id: string;
  title: string;
  kind: string;
  run_count: number;
  created_at: string | null;
  updated_at: string | null;
}

interface MemoryEntry {
  id: string;
  agent_role: string;
  content_type: string;
  summary: string;
  details: string;
  created_at: string | null;
}

export interface SessionDetail extends SessionItem {
  runs: ProjectRun[];
  memories: MemoryEntry[];
}

export type AppStatus = 'idle' | 'loading' | 'running' | 'completed' | 'error';

// Agent info is now dynamic from the API
export function getAgentInfo(
  agents: AgentConfig[],
  role: string,
): { icon: string; label: string; color: string } {
  const found = agents.find((a) => a.role_identifier === role);
  if (found) {
    return {
      icon: found.icon || '◆',
      label: found.name,
      color: getColorForRole(role),
    };
  }
  return { icon: '◆', label: role, color: '#666' };
}

const ROLE_COLORS = [
  '#4A90D9',
  '#00C853',
  '#FF6D00',
  '#9C27B0',
  '#00BCD4',
  '#FF5722',
  '#607D8B',
  '#E91E63',
];
function getColorForRole(role: string): string {
  let hash = 0;
  for (let i = 0; i < role.length; i++) {
    hash = role.charCodeAt(i) + ((hash << 5) - hash);
  }
  return ROLE_COLORS[Math.abs(hash) % ROLE_COLORS.length];
}
