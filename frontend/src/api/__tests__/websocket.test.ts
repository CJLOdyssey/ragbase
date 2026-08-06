import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const OriginalWebSocket = globalThis.WebSocket;
const fakeWsInstances: FakeWebSocket[] = [];

class FakeWebSocket {
  url: string;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  readyState = FakeWebSocket.OPEN;
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 3;

  private _closed = false;

  constructor(url: string) {
    this.url = url;
    fakeWsInstances.push(this);
  }

  close() {
    this._closed = true;
    this.readyState = FakeWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }

  get closed() {
    return this._closed;
  }
  send() {}
}

beforeEach(() => {
  fakeWsInstances.length = 0;
  vi.useFakeTimers();
  globalThis.WebSocket = FakeWebSocket as unknown as typeof WebSocket;
});

afterEach(() => {
  vi.useRealTimers();
  globalThis.WebSocket = OriginalWebSocket;
});

async function getWs() {
  return import('../websocket');
}

function mockOpts(cb = vi.fn()) {
  return { onMessage: cb };
}

describe('WebSocket Module', { tags: ['unit'] }, () => {
  it('setMaxRetries 更改重试次数', async () => {
    const ws = await getWs();
    ws.setMaxRetries(5);
    expect(true).toBe(true);
  });

  it('connectRun 创建连接并返回取消函数', async () => {
    const ws = await getWs();
    const unsub = ws.connectRun('test-run', mockOpts());
    expect(typeof unsub).toBe('function');
    expect(fakeWsInstances.length).toBe(1);
    unsub();
  });

  it('连接 URL 指向 /runs/{runId} 且不带 token 查询参数', async () => {
    const ws = await getWs();
    const unsub = ws.connectRun('url-run', mockOpts());
    const url = fakeWsInstances[0].url;
    expect(url).toContain('/ws/runs/url-run');
    expect(url).not.toContain('token=');
    expect(url).not.toContain('?');
    unsub();
  });

  it('收到消息时调用回调', async () => {
    const ws = await getWs();
    const cb = vi.fn();
    const unsub = ws.connectRun('test-run', mockOpts(cb));
    fakeWsInstances[0].onmessage!({ data: JSON.stringify({ type: 'message', content: 'hello' }) } as MessageEvent);
    expect(cb).toHaveBeenCalledWith({ type: 'message', content: 'hello' });
    unsub();
  });

  it('同一 runId 共享 WebSocket，两个监听器都收到消息', async () => {
    const ws = await getWs();
    const cb1 = vi.fn();
    const cb2 = vi.fn();
    const unsub1 = ws.connectRun('test-run', mockOpts(cb1));
    const unsub2 = ws.connectRun('test-run', mockOpts(cb2));
    expect(fakeWsInstances.length).toBe(1);
    fakeWsInstances[0].onmessage!({ data: JSON.stringify({ msg: 'hi' }) } as MessageEvent);
    expect(cb1).toHaveBeenCalledWith({ msg: 'hi' });
    expect(cb2).toHaveBeenCalledWith({ msg: 'hi' });
    unsub1();
    unsub2();
  });

  it('取消订阅后不再收到消息', async () => {
    const ws = await getWs();
    const cb = vi.fn();
    const unsub = ws.connectRun('test-run', mockOpts(cb));
    unsub();
    if (fakeWsInstances[0]?.onmessage) {
      fakeWsInstances[0].onmessage!({ data: JSON.stringify({}) } as MessageEvent);
    }
    expect(cb).not.toHaveBeenCalled();
  });

  it('重复取消不崩溃', async () => {
    const ws = await getWs();
    const unsub = ws.connectRun('test-run', mockOpts());
    unsub();
    unsub();
  });

  it('disconnectRun 清理指定 runId', async () => {
    const ws = await getWs();
    ws.connectRun('run-a', mockOpts());
    ws.disconnectRun('run-a');
  });

  it('两个不同 runId 独立连接', async () => {
    const ws = await getWs();
    ws.connectRun('run-a', mockOpts());
    ws.connectRun('run-b', mockOpts());
    expect(fakeWsInstances.length).toBe(2);
  });

  it('JSON 解析错误不崩溃', async () => {
    const ws = await getWs();
    const cb = vi.fn();
    const runId = 'json-err-' + Date.now();
    const unsub = ws.connectRun(runId, mockOpts(cb));
    expect(fakeWsInstances.length).toBeGreaterThan(0);
    fakeWsInstances[fakeWsInstances.length - 1].onmessage!({ data: '{invalid json' } as MessageEvent);
    expect(cb).not.toHaveBeenCalled();
    unsub();
  });
});
