import Logger from '../utils/logger';

export type WsCallback = (data: Record<string, unknown>) => void;
export type WsConnectionStatus =
  'disconnected' | 'connecting' | 'connected' | 'reconnecting';

export interface ConnectOptions {
  onMessage: WsCallback;
  onStatusChange?: (status: WsConnectionStatus) => void;
}

const WS_BASE = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;

/** Build WS URL. Auth is cookie-based (httpOnly) — same-origin handshake carries it. */
function buildWsUrl(runId: string): string {
  return `${WS_BASE}/runs/${runId}`;
}

let maxRetries = 3;

interface ConnState {
  ws: WebSocket;
  listeners: Set<WsCallback>;
  statusListeners: Set<(status: WsConnectionStatus) => void>;
  runId: string;
  reconnectCount: number;
  reconnectTimer?: ReturnType<typeof setTimeout>;
}

const connections = new Map<string, ConnState>();

export function setMaxRetries(n: number): void {
  maxRetries = n;
}

function notifyStatus(state: ConnState, status: WsConnectionStatus) {
  state.statusListeners.forEach((cb) => cb(status));
}

function connect(runId: string, options: ConnectOptions): ConnState {
  const ws = new WebSocket(buildWsUrl(runId));
  const state: ConnState = {
    ws,
    listeners: new Set([options.onMessage]),
    statusListeners: new Set(
      options.onStatusChange ? [options.onStatusChange] : [],
    ),
    runId,
    reconnectCount: 0,
  };
  connections.set(runId, state);

  notifyStatus(state, 'connecting');

  ws.onopen = () => {
    // 成功建连说明此前断线已恢复——按「连续失败」计数而非累计，
    // 避免长会话中几次间隔很远的瞬时断线后永久放弃重连。
    state.reconnectCount = 0;
    notifyStatus(state, 'connected');
    Logger.info('[ws] run %s connected', runId);
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (
        data.type === 'thinking_stream' ||
        data.type === 'thinking_done' ||
        data.type === 'stream'
      ) {
        Logger.info(
          '[WS] %s content: %s thinking: %s | len: %d thinking_len: %d',
          data.type,
          (data.content || '').substring(0, 40),
          (data.thinking || '').substring(0, 40),
          (data.content || '').length,
          (data.thinking || '').length,
        );
      }
      state.listeners.forEach((cb) => cb(data));
    } catch {
      // ignore parse errors — malformed messages are logged but not fatal
    }
  };

  ws.onclose = () => {
    if (state.listeners.size > 0 && state.reconnectCount < maxRetries) {
      const delay = Math.min(1000 * Math.pow(2, state.reconnectCount), 8000);
      state.reconnectCount++;
      notifyStatus(state, 'reconnecting');
      Logger.warn(
        `[ws] run ${runId} disconnected, reconnecting (${state.reconnectCount}/${maxRetries}) in ${delay}ms...`,
      );
      state.reconnectTimer = setTimeout(() => {
        if (connections.has(runId)) {
          const newWs = new WebSocket(buildWsUrl(runId));
          newWs.onopen = ws.onopen;
          newWs.onmessage = ws.onmessage;
          newWs.onclose = ws.onclose;
          newWs.onerror = () => newWs.close();
          state.ws = newWs;
        }
      }, delay);
    } else if (state.listeners.size === 0) {
      // All listeners removed — intentional close
      connections.delete(runId);
    } else {
      Logger.warn(`[ws] run ${runId} max retries reached, giving up`);
      notifyStatus(state, 'disconnected');
      connections.delete(runId);
    }
  };

  ws.onerror = () => {
    ws.close();
  };

  return state;
}

/**
 * Subscribe to a run's WS stream. Sockets are shared per runId — multiple
 * callers attach as listeners. The returned function unsubscribes and closes
 * the socket once the last listener leaves.
 */
export function connectRun(
  runId: string,
  onMessageOrOptions: WsCallback | ConnectOptions,
): () => void {
  const options: ConnectOptions =
    typeof onMessageOrOptions === 'function'
      ? { onMessage: onMessageOrOptions }
      : onMessageOrOptions;

  const existing = connections.get(runId);
  if (existing) {
    // Shared connection — add to existing listener sets
    existing.listeners.add(options.onMessage);
    if (options.onStatusChange) {
      existing.statusListeners.add(options.onStatusChange);
    }
    return () => {
      existing.listeners.delete(options.onMessage);
      if (options.onStatusChange) {
        existing.statusListeners.delete(options.onStatusChange);
      }
      if (existing.listeners.size === 0) {
        if (existing.reconnectTimer) clearTimeout(existing.reconnectTimer);
        existing.ws.close();
        connections.delete(runId);
      }
    };
  }

  const state = connect(runId, options);

  return () => {
    state.listeners.delete(options.onMessage);
    if (options.onStatusChange) {
      state.statusListeners.delete(options.onStatusChange);
    }
    if (state.listeners.size === 0) {
      if (state.reconnectTimer) clearTimeout(state.reconnectTimer);
      notifyStatus(state, 'disconnected');
      state.ws.close();
      connections.delete(runId);
    }
  };
}

export function disconnectRun(runId: string): void {
  const conn = connections.get(runId);
  if (conn) {
    if (conn.reconnectTimer) clearTimeout(conn.reconnectTimer);
    conn.listeners.clear();
    conn.statusListeners.clear();
    conn.ws.close();
    connections.delete(runId);
  }
}
