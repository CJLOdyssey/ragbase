import { readFileSync, writeFileSync } from 'fs';

const modalPath = 'frontend/src/components/devagents/modals/SettingsModal.tsx';
let modal = readFileSync(modalPath, 'utf8');

const replacements = [
  ["t('settings.language.desc')", "t('settings.languageDesc')"],
  ["t('settings.theme.desc')", "t('settings.themeDesc')"],
  ["t('settings.theme.dark')", "t('settings.dark')"],
  ["t('settings.theme.light')", "t('settings.light')"],
  ["t('settings.theme.system')", "t('settings.system')"],
  ["t('settings.fontSize.desc')", "t('settings.fontSizeDesc')"],
  ["t('settings.autoSave.desc')", "t('settings.autoSaveDesc')"],
  ["t('settings.autoComplete.desc')", "t('settings.autoCompleteDesc')"],
  ["t('settings.sound.desc')", "t('settings.soundDesc')"],
];

for (const [from, to] of replacements) {
  modal = modal.replaceAll(from, to);
}

writeFileSync(modalPath, modal, 'utf8');
console.log('SettingsModal updated');

// Restore JSON files to flat keys
const zh = JSON.parse(readFileSync('frontend/src/i18n/locales/zh-CN.json', 'utf8'));
zh.settings.language = '界面语言';
zh.settings.languageDesc = '选择系统显示语言';
zh.settings.theme = '主题模式';
zh.settings.themeDesc = '选择界面主题颜色';
zh.settings.dark = '深色模式';
zh.settings.light = '浅色模式';
zh.settings.system = '跟随系统';
zh.settings.fontSize = '字体大小';
zh.settings.fontSizeDesc = '调整界面文字大小';
zh.settings.autoSave = '自动保存';
zh.settings.autoSaveDesc = '编辑内容时自动保存';
zh.settings.autoComplete = '智能补全';
zh.settings.autoCompleteDesc = '输入时自动补全 Agent 指令';
zh.settings.sound = '提示音';
zh.settings.soundDesc = '收到消息时播放提示音';
writeFileSync('frontend/src/i18n/locales/zh-CN.json', JSON.stringify(zh, null, 2) + '\n');

const en = JSON.parse(readFileSync('frontend/src/i18n/locales/en-US.json', 'utf8'));
en.settings.language = 'Language';
en.settings.languageDesc = 'Select system display language';
en.settings.theme = 'Theme';
en.settings.themeDesc = 'Select interface theme';
en.settings.dark = 'Dark';
en.settings.light = 'Light';
en.settings.system = 'System';
en.settings.fontSize = 'Font Size';
en.settings.fontSizeDesc = 'Adjust interface font size';
en.settings.autoSave = 'Auto Save';
en.settings.autoSaveDesc = 'Auto save content when editing';
en.settings.autoComplete = 'Auto Complete';
en.settings.autoCompleteDesc = 'Auto complete Agent commands when typing';
en.settings.sound = 'Sound';
en.settings.soundDesc = 'Play sound on new messages';
writeFileSync('frontend/src/i18n/locales/en-US.json', JSON.stringify(en, null, 2) + '\n');

console.log('JSON files restored to flat keys');
