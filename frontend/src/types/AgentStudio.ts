// AgentStudio 类型定义（content-studio 裁剪版：不含 Team 树相关类型）
import type { LucideIcon } from 'lucide-react';

// Agent 工具配置
export interface AgentTool {
  id: string;
  name: string;
  description: string;
  type?: string;
  enabled: boolean;
  parameters?: string;
  archived?: boolean;
}

// Agent MCP 配置
export interface AgentMCP {
  id: string;
  name: string;
  description: string;
  serverUrl: string;
  type?: string;
  enabled: boolean;
  archived?: boolean;
}

// Agent Skills 配置
export interface AgentSkill {
  id: string;
  name: string;
  description: string;
  type?: string;
  enabled: boolean;
  archived?: boolean;
}

// Agent 配置
export interface Agent {
  id: string;
  name: string;
  role: string;
  agentConfigId?: string;
  icon: LucideIcon;
  color: string;
  bg: string;
  border: string;
  systemPrompt?: string;
  outputConstraints?: string;
  responseFormat?: Record<string, unknown>;
  tools?: AgentTool[];
  mcp?: AgentMCP[];
  skills?: AgentSkill[];
  isConfigured?: boolean;
}

// 对话历史记录
export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: string;
  updatedAt: string;
  kind?: 'normal' | 'agent';
  agentId?: string;
  sessionId?: string;
}

// 消息类型
export interface Message {
  id: string;
  role: 'user' | 'agent';
  agentId?: string;
  content: string;
  thinking?: string;
  answer?: string;
  timestamp?: number;
  type?: 'process';
  thinkingDone?: boolean;
  plan?: PlanStep[];
  action?: MessageAction;
  hasArtifact?: boolean;
  artifactType?: string;
  artifactTitle?: string;
  isTyping?: boolean;
  versions?: string[];
  thinkingVersions?: string[];
  currentVersion?: number;
  userVersions?: string[];
  currentUserVersion?: number;
  thumbsFeedback?: 'up' | 'down' | null;
  interrupted?: boolean;
}

// 计划步骤
interface PlanStep {
  step: string;
  status: 'completed' | 'running' | 'pending';
}

// 消息动作
interface MessageAction {
  type: string;
  label: string;
}

// 工作区标签
export type WorkspaceTab =
  | 'code'
  | 'preview'
  | 'ui-code'
  | 'ui-preview'
  | 'frontend-code'
  | 'frontend-test'
  | 'frontend-preview'
  | 'backend-code'
  | 'backend-test';

// Agent 类型
export type AgentType = 'ui' | 'frontend' | 'backend';
