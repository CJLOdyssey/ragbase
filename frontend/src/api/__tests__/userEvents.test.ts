import {
  connectUserEvents,
  disconnectUserEvents,
  type UserEvent,
} from '../userEvents';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  static readonly OPEN = 1;
  static readonly CLOSED = 3;

  readyState = 0;
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  close(): void {
    this.readyState = FakeWebSocket.CLOSED;
  }
}

describe('userEvents', () => {
  beforeEach(() => {
    FakeWebSocket.instances = [];
    vi.stubGlobal('WebSocket', FakeWebSocket);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('opens the events channel and dispatches parsed events', () => {
    const handler = vi.fn();
    connectUserEvents(handler);
    const ws = FakeWebSocket.instances[0];
    expect(ws).toBeTruthy();
    expect(ws.url).toContain('/api/ws/events');
    ws.onopen?.();
    const event: UserEvent = {
      type: 'session.deleted',
      session_id: 's1',
      ts: 1,
    };
    ws.onmessage?.({ data: JSON.stringify(event) });
    expect(handler).toHaveBeenCalledWith(event);
    disconnectUserEvents(handler);
  });

  it('fires onReconnect when the channel (re)connects', () => {
    const handler = vi.fn();
    const onReconnect = vi.fn();
    connectUserEvents(handler, onReconnect);
    FakeWebSocket.instances[0].onopen?.();
    expect(onReconnect).toHaveBeenCalledTimes(1);
    disconnectUserEvents(handler, onReconnect);
  });

  it('ignores malformed frames', () => {
    const handler = vi.fn();
    connectUserEvents(handler);
    const ws = FakeWebSocket.instances[0];
    ws.onmessage?.({ data: 'not json' });
    ws.onmessage?.({ data: JSON.stringify({ foo: 1 }) });
    expect(handler).not.toHaveBeenCalled();
    disconnectUserEvents(handler);
  });
});
