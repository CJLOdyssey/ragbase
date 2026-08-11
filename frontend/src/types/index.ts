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
  sources?: RagSource[];
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
  /** User-message edit history (older edits first; content is the active one) */
  userVersions?: string[];
  /** 版本 → runId 映射（userVersions[i] 对应 versionRunIds[i] 的 run turn） */
  versionRunIds?: string[];
  /** 本消息对应 run 的 parent_run_id（编辑产生兄弟分支时使用） */
  parentRunId?: string | null;
  /** 配对的用户消息 id（模型消息分页切换时归一化到用户消息） */
  userMsgId?: string;
  currentUserVersion?: number;
  /** 模型消息答案分页（重新生成链）：与用户版本（userVersions）解耦的独立字段 */
  answerVersions?: string[];
  /** 答案分页 → runId 映射（answerVersions[i] 对应 answerRunIds[i] 的 run turn） */
  answerRunIds?: string[];
  currentAnswerVersion?: number;
  thumbsFeedback?: 'up' | 'down' | null;
  interrupted?: boolean;
  runId?: string;
  /** 本消息对应 run 绑定的附件（用户消息展示下载入口） */
  attachments?: AttachmentInfo[];
  /** RAG 引用来源（模型消息展示引用区） */
  sources?: RagSource[];
}

export interface AttachmentInfo {
  id: string;
  filename: string;
  content_type?: string;
  size_bytes?: number;
  has_extracted_text?: boolean;
}

/** RAG 引用来源（结构化 citation，服务端检索结果） */
export interface RagSource {
  asset_id?: string | null;
  asset_name?: string | null;
  text: string;
  similarity?: number;
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
  parent_run_id?: string | null;
  requirement_versions?: string[] | null;
  messages?: ChatMessage[];
  attachments?: AttachmentInfo[];
}

export interface SessionItem {
  id: string;
  title: string;
  kind: string;
  run_count: number;
  is_pinned?: boolean;
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
