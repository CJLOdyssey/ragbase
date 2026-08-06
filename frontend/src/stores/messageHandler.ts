import type { ChatState } from './chatTypes';
import type { WsMessageEvent, WsInfoEvent, WsErrorEvent, WsBalanceWarningEvent, WsOpenUrlEvent, WsBrowserFrameEvent } from './wsEvents';
import { uid } from './uid';
import Logger from '../utils/logger';

type SetFn = (fn: (state: ChatState) => Partial<ChatState>) => void;

export function handleMessageEvent(set: SetFn, msg: WsMessageEvent): void {
  set((s) => {
    if (s.streamingId) {
      return {
        messages: s.messages.map((m) => {
          if (m.id !== s.streamingId) return m;
          const newThinking = msg.thinking ?? m.thinking;
          const cv = m.currentVersion ?? 0;
          const tvBase = m.thinkingVersions?.length ? m.thinkingVersions : (m.thinking ? [m.thinking] : []);
          const newTV = [...tvBase];
          if (newTV[cv] !== undefined) {
            newTV[cv] = newThinking ?? '';
          }
          return { ...m, content: msg.content!, thinking: newThinking, thinkingVersions: newTV };
        }),
        currentRole: msg.role!,
        wsStatus: 'connected' as ChatState['wsStatus'],
      };
    }
    Logger.warn('[chat] message event with no streamingId — creating new msg');
    const m = {
      id: crypto.randomUUID?.() || uid(),
      role: msg.role!,
      agent_name: msg.agent_name!,
      content: msg.content!,
      thinking: msg.thinking,
      round_number: msg.round_number ?? 0,
      created_at: new Date().toISOString(),
    };
    return {
      messages: [...s.messages, m],
      currentRole: msg.role!,
      wsStatus: 'connected' as ChatState['wsStatus'],
    };
  });
}

export function handleInfoEvent(set: SetFn, msg: WsInfoEvent): void {
  set((s) => {
    const infoContent = msg.content || typeof msg.data === 'string' ? msg.data : '';
    if (s.streamingId) {
      return {
        messages: s.messages.map((m) =>
          m.id === s.streamingId
            ? { ...m, content: m.content + (infoContent ? `\n[${infoContent}]` : '') }
            : m,
        ),
      };
    }
    return {};
  });
}

export function handleErrorEvent(set: SetFn, msg: WsErrorEvent): void {
  Logger.error('[chat] error event:', msg.content);
  set((_s) => ({
    status: 'error' as ChatState['status'],
    error: msg.content || 'Unknown error',
    streamingId: null,
    wsStatus: 'connected' as ChatState['wsStatus'],
  }));
}

export function handleBalanceWarningEvent(set: SetFn, msg: WsBalanceWarningEvent): void {
  Logger.error('[chat] balance warning:', msg.content);
  set((_s) => ({
    status: 'error' as ChatState['status'],
    error: msg.content || '模型余额不足',
    streamingId: null,
    wsStatus: 'connected' as ChatState['wsStatus'],
  }));
}

let _lastBrowserFrame = '';

export function getLastBrowserFrame(): string {
  return _lastBrowserFrame;
}

let _pendingBrowserUrl = '';

export function getPendingBrowserUrl(): string {
  return _pendingBrowserUrl;
}

export function clearPendingBrowserUrl(): void {
  _pendingBrowserUrl = '';
}

export function handleOpenUrlEvent(msg: WsOpenUrlEvent): void {
  const targetUrl: string = msg.url || '';
  if (!targetUrl) return;
  Logger.info('[chat] open_url: %s', targetUrl);
  _pendingBrowserUrl = targetUrl;
  window.dispatchEvent(new CustomEvent('browser-open-url', { detail: targetUrl }));
}

export function handleBrowserFrameEvent(msg: WsBrowserFrameEvent): void {
  _lastBrowserFrame = msg.data;
  window.dispatchEvent(new CustomEvent('browser-frame', { detail: msg.data }));
}
