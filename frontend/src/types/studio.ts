// RagBase 类型定义（不含 Team 树相关类型）

// 消息类型
import type { RagSource } from '../types';
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
  /** 会话已产生的 run 数（后端 sessions 列表返回；列表消息恒空时用于判定是否已回复） */
  runCount?: number;
}

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
  /** 用户消息展示的附件（来自 run 绑定，下载 GET /api/attachments/{id}） */
  attachments?: { id: string; filename: string; size_bytes?: number }[];
  /** RAG 引用来源（模型消息展示引用区） */
  sources?: RagSource[];
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
