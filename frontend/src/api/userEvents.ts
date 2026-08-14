import Logger from '../utils/logger';

export type UserEventType =
  'session.created' | 'session.updated' | 'session.deleted';

export interface UserEvent {
  type: UserEventType;
  session_id: string;
  ts: number;
}

export type UserEventHandler = (event: UserEvent) => void;

const EVENTS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/ws/events`;

let ws: WebSocket | null = null;
const listeners = new Set<UserEventHandler>();
const reconnectHandlers = new Set<() => void>();
let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
let attempts = 0;

function open(): void {
  try {
    ws = new WebSocket(EVENTS_URL);
  } catch {
    return;
  }
  ws.onopen = () => {
    attempts = 0;
    reconnectHandlers.forEach((h) => h());
  };
  ws.onmessage = (raw) => {
    try {
      const data = JSON.parse(raw.data) as UserEvent;
      if (data && typeof data.type === 'string' && data.session_id) {
        listeners.forEach((l) => l(data));
      }
    } catch {
      // ignore malformed frames
    }
  };
  ws.onclose = () => {
    scheduleReconnect();
  };
  ws.onerror = () => {
    // onclose drives reconnection
  };
}

function scheduleReconnect(): void {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  attempts += 1;
  const delay = Math.min(1000 * 2 ** attempts, 30000);
  reconnectTimer = setTimeout(open, delay);
}

export function connectUserEvents(
  onEvent: UserEventHandler,
  onReconnect?: () => void,
): void {
  listeners.add(onEvent);
  if (onReconnect) reconnectHandlers.add(onReconnect);
  if (!ws || ws.readyState === WebSocket.CLOSED) {
    open();
  }
}

export function disconnectUserEvents(
  onEvent: UserEventHandler,
  onReconnect?: () => void,
): void {
  listeners.delete(onEvent);
  if (onReconnect) reconnectHandlers.delete(onReconnect);
  if (listeners.size === 0 && ws) {
    ws.close();
    ws = null;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    reconnectTimer = undefined;
  }
}

// Keep the module logger import referenced for consistent log discipline.
void Logger;
