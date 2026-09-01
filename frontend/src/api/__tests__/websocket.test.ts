import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

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
    // 与真实浏览器一致：onclose 异步派发（避免掩盖重连时序 bug）
    if (this.onclose) {
      Promise.resolve().then(() => this.onclose?.(new CloseEvent('close')));
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
  it('setMaxRetries(1) 限制只重连一次后放弃', async () => {
    const ws = await getWs();
    ws.setMaxRetries(1);
    const runId = 'max-retries-1';
    const unsub = ws.connectRun(runId, mockOpts());
    // maxRetries=1 → 断线 1 次后重连，第 2 次断线放弃（共 2 个实例）
    fakeWsInstances[0].close();
    await vi.advanceTimersByTimeAsync(1000);
    expect(fakeWsInstances.length).toBe(2);
    fakeWsInstances[1].close();
    await vi.advanceTimersByTimeAsync(8000);
    expect(fakeWsInstances.length).toBe(2);
    unsub();
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
    fakeWsInstances[0].onmessage!({
      data: JSON.stringify({ type: 'message', content: 'hello' }),
    } as MessageEvent);
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
    fakeWsInstances[0].onmessage!({
      data: JSON.stringify({ msg: 'hi' }),
    } as MessageEvent);
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
      fakeWsInstances[0].onmessage!({
        data: JSON.stringify({}),
      } as MessageEvent);
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
    fakeWsInstances[fakeWsInstances.length - 1].onmessage!({
      data: '{invalid json',
    } as MessageEvent);
    expect(cb).not.toHaveBeenCalled();
    unsub();
  });

  it('断线后按退避重连，成功建连后重连计数归零', async () => {
    const ws = await getWs();
    const runId = 'rc-reset-run';
    const unsub = ws.connectRun(runId, mockOpts());
    const first = fakeWsInstances[0];

    // 第一次断线 → 1s 后重连（async close）
    first.close();
    await vi.advanceTimersByTimeAsync(1000);
    expect(fakeWsInstances.length).toBe(2);

    // 重连成功（onopen）→ 计数归零
    fakeWsInstances[1].onopen?.(new Event('open'));

    // 再次断线 → 若计数未归零，退避应为 2000ms；归零后仍是 1000ms
    fakeWsInstances[1].close();
    await vi.advanceTimersByTimeAsync(1000);
    expect(fakeWsInstances.length).toBe(3);
    unsub();
  });

  it('连续失败达到上限后放弃重连', async () => {
    const ws = await getWs();
    // 第一个用例 setMaxRetries(1) 污染了模块级状态，这里显式复位契约。
    ws.setMaxRetries(3);
    const runId = 'rc-giveup-run';
    const unsub = ws.connectRun(runId, mockOpts());
    // maxRetries=3 → 可重连 3 次（共 4 个连接实例）
    for (let i = 0; i < 4; i++) {
      fakeWsInstances[i].close();
      await vi.advanceTimersByTimeAsync(8000);
    }
    expect(fakeWsInstances.length).toBe(4);
    // 第 4 次断线后不再新建连接，且连接已从注册表移除
    const last = fakeWsInstances[3];
    expect(last.readyState).toBe(FakeWebSocket.CLOSED);
    unsub();
  });
});
