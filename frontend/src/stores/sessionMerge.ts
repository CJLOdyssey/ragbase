import type { SessionItem } from '../types';

/**
 * 正式模式的会话列表归并（幂等核心）：
 * - 乐观占位（temp）保留在列（发送中，未获 server 确认）
 * - server 会话若匹配 temp 占位（同标题 + 15s 内创建）则原位替换（不新增，
 *   消除 WS 事件先于 run 响应时的发送中暂态双条）
 * - 其余 server 会话按原样输出（唯一，server 权威）
 * - 已确认但不在 server 的会话被删除（DB 权威）
 */
export function mergeSessions(
  prev: SessionItem[],
  server: SessionItem[],
): SessionItem[] {
  const temp = prev.filter((s) => s.temp);
  const matches = (t: SessionItem, s: SessionItem) =>
    t.title === s.title &&
    Date.now() - new Date(t.created_at ?? 0).getTime() < 15000;
  const result: SessionItem[] = [];
  for (const t of temp) {
    if (!server.some((s) => matches(t, s))) result.push(t);
  }
  for (const s of server) {
    const tmp = temp.find((t) => matches(t, s));
    result.push(tmp ? { ...s, temp: false } : s);
  }
  return result;
}

/** 生成乐观占位会话项（temp 标记，id=temp-*）。 */
export function makeTempSession(title: string): SessionItem {
  const now = new Date().toISOString();
  return {
    id: `temp-${crypto.randomUUID?.() ?? String(Date.now())}`,
    temp: true,
    title: title.length > 36 ? title.slice(0, 36) + '...' : title,
    kind: 'normal',
    run_count: 0,
    is_pinned: false,
    created_at: now,
    updated_at: now,
  };
}

/** 是否乐观占位（未获 server 确认）。 */
export function isTempSession(s: SessionItem): boolean {
  return !!s.temp;
}
