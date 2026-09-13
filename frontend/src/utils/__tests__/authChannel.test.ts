import { afterEach, describe, expect, it, vi } from 'vitest';

type Listener = (e: MessageEvent) => void;

class FakeBroadcastChannel {
  static instances: FakeBroadcastChannel[] = [];
  listeners = new Set<Listener>();
  posted: unknown[] = [];

  constructor(public name: string) {
    FakeBroadcastChannel.instances.push(this);
  }

  addEventListener(type: string, listener: Listener) {
    if (type === 'message') this.listeners.add(listener);
  }

  removeEventListener(type: string, listener: Listener) {
    if (type === 'message') this.listeners.delete(listener);
  }

  postMessage(data: unknown) {
    this.posted.push(data);
  }

  emit(data: unknown) {
    this.listeners.forEach((l) => l({ data } as MessageEvent));
  }
}

describe('authChannel', { tags: ['unit'] }, () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.resetModules();
    FakeBroadcastChannel.instances = [];
  });

  it('broadcasts logout events through the channel', async () => {
    vi.stubGlobal('BroadcastChannel', FakeBroadcastChannel);
    const { broadcastAuthEvent } = await import('@/utils/authChannel');

    broadcastAuthEvent('logout');

    expect(FakeBroadcastChannel.instances).toHaveLength(1);
    expect(FakeBroadcastChannel.instances[0].posted).toEqual(['logout']);
  });

  it('delivers logout events to subscribers and supports unsubscribe', async () => {
    vi.stubGlobal('BroadcastChannel', FakeBroadcastChannel);
    const { subscribeAuthEvents } = await import('@/utils/authChannel');
    const handler = vi.fn();

    const unsubscribe = subscribeAuthEvents(handler);
    FakeBroadcastChannel.instances[0].emit('logout');
    expect(handler).toHaveBeenCalledWith('logout');

    unsubscribe();
    FakeBroadcastChannel.instances[0].emit('logout');
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it('ignores unrelated events', async () => {
    vi.stubGlobal('BroadcastChannel', FakeBroadcastChannel);
    const { subscribeAuthEvents } = await import('@/utils/authChannel');
    const handler = vi.fn();

    subscribeAuthEvents(handler);
    FakeBroadcastChannel.instances[0].emit('login');

    expect(handler).not.toHaveBeenCalled();
  });

  it('degrades gracefully when BroadcastChannel is unavailable', async () => {
    vi.stubGlobal('BroadcastChannel', undefined);
    const { broadcastAuthEvent, subscribeAuthEvents } =
      await import('@/utils/authChannel');

    expect(() => broadcastAuthEvent('logout')).not.toThrow();
    const unsubscribe = subscribeAuthEvents(vi.fn());
    expect(() => unsubscribe()).not.toThrow();
  });
});
