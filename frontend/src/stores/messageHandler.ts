import i18n from '../i18n';
import Logger from '../utils/logger';
import type { ChatState } from './chatTypes';
import { uid } from './uid';
import type {
  WsBalanceWarningEvent,
  WsBrowserFrameEvent,
  WsErrorEvent,
  WsInfoEvent,
  WsMessageEvent,
  WsOpenUrlEvent,
} from './wsEvents';

type SetFn = (fn: (state: ChatState) => Partial<ChatState>) => void;

export function handleMessageEvent(set: SetFn, msg: WsMessageEvent): void {
  set((s) => {
    // Run finished (result → status idle): WS reconnect replays buffered events.
    // Ignore them — appending would duplicate the completed conversation.
    if (s.status !== 'running') return {};
    if (s.streamingId) {
      return {
        messages: s.messages.map((m) => {
          if (m.id !== s.streamingId) return m;
          return {
            ...m,
            content: msg.content!,
            thinking: msg.thinking ?? m.thinking,
            sources: msg.sources ?? m.sources,
          };
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
      sources: msg.sources,
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
    // content 优先；data 仅在 content 缺失时兜底（运算符优先级：先求值
    // typeof 分支再参与 ||，否则 content 有值而 data 缺失时会追加 undefined）。
    const infoContent =
      msg.content || (typeof msg.data === 'string' ? msg.data : '');
    if (s.streamingId) {
      return {
        messages: s.messages.map((m) =>
          m.id === s.streamingId
            ? {
                ...m,
                content: m.content + (infoContent ? `\n[${infoContent}]` : ''),
              }
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
    // 失败即终止流程：清理续写/编辑挂起状态，避免 UI 卡在「继续生成中…」。
    continuingId: null,
    editTargetId: null,
    pendingVersions: null,
    pendingThinkingVersions: null,
    wsStatus: 'connected' as ChatState['wsStatus'],
  }));
}

export function handleBalanceWarningEvent(
  set: SetFn,
  msg: WsBalanceWarningEvent,
): void {
  Logger.error('[chat] balance warning:', msg.content);
  set((_s) => ({
    status: 'error' as ChatState['status'],
    error: msg.content || i18n.t('chat.insufficientBalance'),
    streamingId: null,
    continuingId: null,
    editTargetId: null,
    pendingVersions: null,
    pendingThinkingVersions: null,
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
  window.dispatchEvent(
    new CustomEvent('browser-open-url', { detail: targetUrl }),
  );
}

export function handleBrowserFrameEvent(msg: WsBrowserFrameEvent): void {
  _lastBrowserFrame = msg.data;
  window.dispatchEvent(new CustomEvent('browser-frame', { detail: msg.data }));
}
