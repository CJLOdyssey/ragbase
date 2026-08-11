/** WebSocket event types for chat streaming */

import type { RagSource } from '../types';

export interface WsStreamEvent {
  type: 'stream';
  content?: string;
  thinking?: string;
  agent_name?: string;
}

export interface WsThinkingStreamEvent {
  type: 'thinking_stream';
  content?: string;
  thinking?: string;
  agent_name?: string;
}

export interface WsMessageEvent {
  type: 'message';
  content?: string;
  thinking?: string;
  role?: string;
  agent_name?: string;
  round_number?: number;
  sources?: RagSource[];
}

export interface WsThinkingDoneEvent {
  type: 'thinking_done';
  thinking?: string;
  agent_name?: string;
}

export interface WsInfoEvent {
  type: 'info';
  content?: string;
  data?: string;
}

export interface WsErrorEvent {
  type: 'error';
  content?: string;
}

export interface WsBalanceWarningEvent {
  type: 'balance_warning';
  content?: string;
}

export interface WsOpenUrlEvent {
  type: 'open_url';
  url?: string;
}

export interface WsBrowserFrameEvent {
  type: 'browser_frame';
  data: string;
}

export interface WsResultEvent {
  type: 'result';
  run_id?: string;
  [key: string]: unknown;
}

/** Per-role verdict from the N1 team backend (contract-N1). */
export interface TeamVerdict {
  role: string;
  approved: boolean;
  reason?: string;
  rounds: number;
}

export interface WsTeamResultEvent {
  type: 'team_result';
  artifacts?: Record<string, unknown>;
  display?: string;
  verdicts?: Record<string, TeamVerdict>;
  rounds?: number;
  [key: string]: unknown;
}

export interface WsApprovalRequestEvent {
  type: 'approval_request';
  run_id?: string;
  node?: string;
}

export interface WsThumbsEvent {
  type: 'thumbs';
  [key: string]: unknown;
}

export type WsEvent =
  | WsStreamEvent
  | WsThinkingStreamEvent
  | WsMessageEvent
  | WsThinkingDoneEvent
  | WsInfoEvent
  | WsErrorEvent
  | WsBalanceWarningEvent
  | WsOpenUrlEvent
  | WsBrowserFrameEvent
  | WsResultEvent
  | WsTeamResultEvent
  | WsApprovalRequestEvent
  | WsThumbsEvent;
