import { readFileSync } from 'fs';

const files = {
  modal: readFileSync('frontend/src/components/devagents/modals/SettingsModal.tsx', 'utf8'),
  ctx: readFileSync('frontend/src/contexts/SettingsContext.tsx', 'utf8'),
  workstation: readFileSync('frontend/src/components/devagents/DevAgentsWorkstation.tsx', 'utf8'),
  conversation: readFileSync('frontend/src/hooks/useConversation.ts', 'utf8'),
  chatInput: readFileSync('frontend/src/components/devagents/ChatInputArea.tsx', 'utf8'),
  teamMessage: readFileSync('frontend/src/components/devagents/TeamMessage.tsx', 'utf8'),
  toast: readFileSync('frontend/src/utils/useToast.tsx', 'utf8'),
};

const checks = [
  { name: '语言切换 → changeLanguage()', file: files.ctx, pattern: 'changeLanguage', pass: false },
  { name: '语言切换 → 导入 i18n/index', file: files.modal, pattern: 'changeLanguage', pass: false },
  { name: '主题切换 → classList', file: files.ctx, pattern: 'classList', pass: false },
  { name: '字号 → --da-font-size-base', file: files.ctx, pattern: '--da-font-size-base', pass: false },
  { name: '发送模式 → workstation Enter 处理', file: files.workstation, pattern: 'sendMode', pass: false },
  { name: '发送模式 → ChatInput Enter 处理', file: files.chatInput, pattern: 'sendMode', pass: false },
  { name: '自动保存 → 条件写入 localStorage', file: files.conversation, pattern: 'settings.autoSave', pass: false },
  { name: '流式输出 → toggle 绑定', file: files.modal, pattern: 'streamOutput', pass: false },
  { name: '提示音 → playBeep()', file: files.ctx, pattern: 'playBeep', pass: false },
  { name: '提示音 → useNotificationSound 导出', file: files.ctx, pattern: 'useNotificationSound', pass: false },
  { name: '提示音 → 发送时调用 notify()', file: files.workstation, pattern: 'notify()', pass: false },
  { name: '智能补全 → toggle 绑定', file: files.modal, pattern: 'autoComplete', pass: false },
];

for (const c of checks) {
  c.pass = c.file.includes(c.pattern);
  console.log(`${c.pass ? '✅' : '❌'} ${c.name}`);
}
