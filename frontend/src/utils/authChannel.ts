/**
 * 跨标签页认证事件广播 —— 基于 BroadcastChannel。
 *
 * 场景：标签页 A 登出后，认证 cookie 由服务端清除，但其他标签页的 UI 仍
 * 显示已登录（直到其下一次请求 401）。本模块把登出事件即时广播给同源其他
 * 标签页，由其立即清理本地 UI 状态。
 *
 * 浏览器不支持 BroadcastChannel 时静默降级（不影响登录/登出主流程）。
 */

export type AuthChannelEvent = 'logout';

const CHANNEL_NAME = 'ragbase-auth';

let channel: BroadcastChannel | null = null;

function getChannel(): BroadcastChannel | null {
  if (typeof BroadcastChannel === 'undefined') return null;
  if (channel === null) {
    channel = new BroadcastChannel(CHANNEL_NAME);
  }
  return channel;
}

/** 广播认证事件给同源其他标签页。 */
export function broadcastAuthEvent(event: AuthChannelEvent): void {
  getChannel()?.postMessage(event);
}

/** 订阅同源其他标签页的认证事件；返回取消订阅函数。 */
export function subscribeAuthEvents(
  handler: (event: AuthChannelEvent) => void,
): () => void {
  const ch = getChannel();
  if (ch === null) return () => {};
  const listener = (e: MessageEvent) => {
    if (e.data === 'logout') handler(e.data);
  };
  ch.addEventListener('message', listener);
  return () => ch.removeEventListener('message', listener);
}
