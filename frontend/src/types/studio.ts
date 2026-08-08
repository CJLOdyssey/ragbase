// RagBase 类型定义（不含 Team 树相关类型）
import type { LucideIcon } from 'lucide-react';

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
  isPinned?: boolean;
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
  userVersions?: string[];
  currentUserVersion?: number;
  /** 模型消息答案分页（重新生成链），与用户版本字段解耦 */
  answerVersions?: string[];
  currentAnswerVersion?: number;
  /** 配对的用户消息 id（模型消息分页切换时归一化到用户消息） */
  userMsgId?: string;
  thumbsFeedback?: 'up' | 'down' | null;
  interrupted?: boolean;
  runId?: string;
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
