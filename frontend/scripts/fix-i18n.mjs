import { readFileSync, writeFileSync } from 'fs';

const path = 'frontend/src/components/devagents/modals/SettingsModal.tsx';
let content = readFileSync(path, 'utf8');

const replacements = [
  ['通用', "{t('settings.general')}"],
  ['AI 对话', "{t('settings.aiChat')}"],
  ['代码', "{t('settings.editor')}"],
  ['快捷键', "{t('settings.shortcuts')}"],
  ['个人信息', "{t('settings.profile')}"],
  ['通知', "{t('settings.notificationTitle')}"],
  ['消息通知', "{t('settings.messageNotif')}"],
  ['邮件通知', "{t('settings.emailNotif')}"],
];

const lineReplacements = [
  ['<option value="zh-CN">简体中文</option>', '<option value="zh-CN">{t(\'settings.currentLang\')}</option>'],
  ['<option value="enter">Enter 发送</option>', '<option value="enter">{t(\'settings.enter\')}</option>'],
  ['<option value="ctrl-enter">Ctrl + Enter 发送</option>', '<option value="ctrl-enter">{t(\'settings.ctrlEnter\')}</option>'],
  ['<option value="2">2 空格</option>', '<option value="2">{t(\'settings.tab2\')}</option>'],
  ['<option value="4">4 空格</option>', '<option value="4">{t(\'settings.tab4\')}</option>'],
  ['<option value="never">不发送</option>', '<option value="never">{t(\'settings.never\')}</option>'],
  ['<option value="daily">每日</option>', '<option value="daily">{t(\'settings.daily\')}</option>'],
  ['<option value="weekly">每周</option>', '<option value="weekly">{t(\'settings.weekly\')}</option>'],
];

// Replace h4 tags
for (const [from, to] of replacements) {
  const h4Regex = new RegExp(`<h4>${from}</h4>`, 'g');
  content = content.replace(h4Regex, `<h4>${to}</h4>`);
}

// Replace option tags
for (const [from, to] of lineReplacements) {
  content = content.replaceAll(from, to);
}

// Replace specific label/desc patterns
content = content.replace('<label>发送方式</label>', "<label>{t('settings.sendMode')}</label>");
content = content.replace("<span className=\"settings-item-desc\">Enter 发送 / Ctrl+Enter 换行</span>", "<span className=\"settings-item-desc\">{t('settings.sendModeDesc')}</span>");
content = content.replace('<label>流式输出</label>', "<label>{t('settings.streamOutput')}</label>");
content = content.replace("<span className=\"settings-item-desc\">逐字显示 AI 回复，而非一次性输出</span>", "<span className=\"settings-item-desc\">{t('settings.streamOutputDesc')}</span>");
content = content.replace('<label>字体大小</label>', "<label>{t('settings.editorFontSize')}</label>");
content = content.replace("<span className=\"settings-item-desc\">代码区域的文字大小</span>", "<span className=\"settings-item-desc\">{t('settings.editorFontSizeDesc')}</span>");
content = content.replace('<label>Tab 大小</label>', "<label>{t('settings.tabSize')}</label>");
content = content.replace("<span className=\"settings-item-desc\">代码缩进使用的空格数</span>", "<span className=\"settings-item-desc\">{t('settings.tabSizeDesc')}</span>");
content = content.replace('<label>自动换行</label>', "<label>{t('settings.wordWrap')}</label>");
content = content.replace("<span className=\"settings-item-desc\">超出宽度时自动折行</span>", "<span className=\"settings-item-desc\">{t('settings.wordWrapDesc')}</span>");
content = content.replace('<label>行号</label>', "<label>{t('settings.lineNumber')}</label>");
content = content.replace("<span className=\"settings-item-desc\">编辑器左侧显示行号</span>", "<span className=\"settings-item-desc\">{t('settings.lineNumberDesc')}</span>");
content = content.replace('应用中可用的全局快捷键', "{t('settings.shortcutsDesc')}");
content = content.replace('<span className=\"settings-profile-role\">个人用户</span>', '<span className=\"settings-profile-role\">{t(\'settings.userRole\')}</span>');
content = content.replace('<label>用户名</label><span className=\"settings-item-desc\">你的显示名称</span>', "<label>{t('settings.username')}</label><span className=\"settings-item-desc\">{t('settings.usernameDesc')}</span>");
content = content.replace('<label>邮箱</label><span className=\"settings-item-desc\">用于登录和接收通知</span>', "<label>{t('settings.email')}</label><span className=\"settings-item-desc\">{t('settings.emailDesc')}</span>");
content = content.replace('<label>修改密码</label>\n                  <span className=\"settings-item-desc\">至少 8 位，包含字母和数字</span>', "<label>{t('settings.changePassword')}</label>\n                  <span className=\"settings-item-desc\">{t('settings.changePasswordDesc')}</span>");
content = content.replace('<button className=\"btn btn-sm btn-secondary\" onClick={() => {}}>修改</button>', '<button className=\"btn btn-sm btn-secondary\" onClick={() => {}}>{t(\'settings.changePassword\')}</button>');

// Notification items
content = content.replace(
  "{ label: '新消息', desc: '收到新消息时弹窗提醒', val: messageNotif, set: setMessageNotif },",
  "{ label: t('settings.newMessage'), desc: t('settings.newMessageDesc'), val: messageNotif, set: setMessageNotif },"
);
content = content.replace(
  "{ label: '任务提醒', desc: '任务完成或失败时通知', val: taskNotif, set: setTaskNotif },",
  "{ label: t('settings.taskReminder'), desc: t('settings.taskReminderDesc'), val: taskNotif, set: setTaskNotif },"
);
content = content.replace(
  "{ label: '@ 提及', desc: '有人提到你时通知', val: true, set: () => {} },",
  "{ label: t('settings.mention'), desc: t('settings.mentionDesc'), val: true, set: () => {} },"
);
content = content.replace('<label>邮件通知</label><span className=\"settings-item-desc\">将重要通知发送到邮箱</span>', "<label>{t('settings.emailNotif')}</label><span className=\"settings-item-desc\">{t('settings.emailNotifDesc')}</span>");
content = content.replace('<label>摘要频率</label>', "<label>{t('settings.digestFreq')}</label>");
content = content.replace("<span className=\"settings-item-desc\">未读消息的摘要发送频率</span>", "<span className=\"settings-item-desc\">{t('settings.digestFreqDesc')}</span>");

writeFileSync(path, content, 'utf8');
console.log('Done');
