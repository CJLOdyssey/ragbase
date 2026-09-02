import type { ManageView } from './RagBaseWorkstation';

/**
 * URL path ↔ ManageView 双向映射。
 *
 * 设计原则：
 * - SRP：只负责路由映射，不含业务逻辑
 * - OCP：新增页面只需在此添加一行，不改已有代码
 * - 单一数据源：viewToPath 为正向映射，pathToView 为反向查找
 */
const VIEW_PATH_MAP: Record<ManageView, string> = {
  chat: '/',
  prompts: '/prompts',
  assets: '/assets',
  monitoring: '/monitoring',
  'retrieval-logs': '/retrieval-logs',
  'admin-users': '/admin-users',
  'knowledge-bases': '/knowledge-bases',
};

/** ManageView → URL path */
export function viewToPath(view: ManageView): string {
  return VIEW_PATH_MAP[view];
}

/** URL path → ManageView（找不到时返回 'chat' 作为兜底） */
export function pathToView(pathname: string): ManageView {
  const entry = Object.entries(VIEW_PATH_MAP).find(
    ([, p]) => p === pathname,
  );
  if (entry) return entry[0] as ManageView;

  // /chat/:sessionId → chat
  if (pathname.startsWith('/chat/')) return 'chat';

  return 'chat';
}
