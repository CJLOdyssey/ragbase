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
    // 与真实浏览器一致：onclose 异步派发
    if (this.onclose) {
      Promise.resolve().then(() => this.onclose?.());
    }
  }
}

describe('userEvents', () => {
  beforeEach(() => {
    FakeWebSocket.instances = [];
    vi.stubGlobal('WebSocket', FakeWebSocket);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
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

  it('断开后自动重连（指数退避）', async () => {
    vi.useFakeTimers();
    const handler = vi.fn();
    connectUserEvents(handler);
    const ws = FakeWebSocket.instances[0];
    ws.onopen?.();
    ws.close();
    await vi.advanceTimersByTimeAsync(2000);
    expect(FakeWebSocket.instances.length).toBe(2);
    disconnectUserEvents(handler);
  });

  it('最后一个监听器离开后不再重连（异步 onclose 不复活连接）', async () => {
    vi.useFakeTimers();
    const handler = vi.fn();
    connectUserEvents(handler);
    const ws = FakeWebSocket.instances[0];
    ws.onopen?.();
    disconnectUserEvents(handler);
    // 真实浏览器中 close() 的 onclose 异步派发；即使如此也不能
    // 重新武装重连定时器（历史缺陷：无监听器 socket 无限重连）。
    await vi.advanceTimersByTimeAsync(60000);
    expect(FakeWebSocket.instances.length).toBe(1);
  });

  it('重新连接后 attempts 归零、可再次重连', async () => {
    vi.useFakeTimers();
    const handler = vi.fn();
    const onReconnect = vi.fn();
    connectUserEvents(handler, onReconnect);
    const first = FakeWebSocket.instances[0];
    first.onopen?.();
    first.close();
    await vi.advanceTimersByTimeAsync(2000);
    expect(FakeWebSocket.instances.length).toBe(2);
    const second = FakeWebSocket.instances[1];
    second.onopen?.();
    expect(onReconnect).toHaveBeenCalledTimes(2);
    disconnectUserEvents(handler, onReconnect);
  });
});
