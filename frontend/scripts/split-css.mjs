import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';

const ROOT = resolve(import.meta.dirname, '../src/styles');

const configs = [
  {
    file: 'legacy.css', dir: 'legacy',
    sections: [
      { name: 'layout.css',  start: '/* ── Layout ── */', end: '/* ── Main Chat Area ── */' },
      { name: 'chat.css',    start: '/* ── Main Chat Area ── */', end: '/* ── Process Indicator ── */' },
      { name: 'result.css',  start: '/* ── Process Indicator ── */', end: '/* ── Config Modal ── */' },
      { name: 'config.css',  start: '/* ── Config Modal ── */', end: '/* ── Error Banner ── */' },
      { name: 'status.css',  start: '/* ── Error Banner ── */', end: '/* ── History Page ── */' },
      { name: 'history.css', start: '/* ── History Page ── */', end: '/* ── Placeholder / Empty State ── */' },
      { name: 'empty.css',   start: '/* ── Placeholder / Empty State ── */', end: '/* ── Mobile Responsive ── */' },
      { name: 'responsive.css', start: '/* ── Mobile Responsive ── */', end: '/* ── Legacy form/icon classes ── */' },
      { name: 'forms.css',   start: '/* ── Legacy form/icon classes ── */', end: null },
    ]
  },
  {
    file: 'chat.css', dir: 'chat',
    sections: [
      { name: 'messages.css', start: '/* Messages */', end: '/* Process panel */' },
      { name: 'process.css',  start: '/* Process panel */', end: '/* Action labels */' },
      { name: 'artifacts.css', start: '/* Action labels */', end: '/* Artifact cards */' },
      { name: 'artifacts.css', start: '/* Artifact cards */', end: '/* Home page */' },
      { name: 'home.css',     start: '/* Home page */', end: '/* Typing cursor */' },
      { name: 'home.css',     start: '/* Typing cursor */', end: '/* Agent cards */' },
      { name: 'cards.css',    start: '/* Agent cards */', end: '/* Pagination */' },
      { name: 'pagination.css', start: '/* Pagination */', end: '/* Agent welcome */' },
      { name: 'welcome.css',  start: '/* Agent welcome */', end: '/* Sample buttons */' },
      { name: 'samples.css',  start: '/* Sample buttons */', end: '/* Input area */' },
      { name: 'input.css',    start: '/* Input area */', end: '/* Model selector */' },
      { name: 'models.css',   start: '/* Model selector */', end: '/* Scrollbar */' },
      { name: 'scrollbar.css', start: '/* Scrollbar */', end: '/* Utility classes */' },
      { name: 'utils.css',    start: '/* Utility classes */', end: null },
    ]
  },
  {
    file: 'modals.css', dir: 'modals',
    sections: [
      { name: 'base.css',      start: '/* Modal base */', end: '/* Agent Config Modal */' },
      { name: 'agent.css',     start: '/* Agent Config Modal */', end: '/* Settings Modal */' },
      { name: 'settings.css',  start: '/* Settings Modal */', end: '/* API Management Modal */' },
      { name: 'api.css',       start: '/* API Management Modal */', end: '/* Confirm Modal */' },
      { name: 'confirm.css',   start: '/* Confirm Modal */', end: '/* New Project Modal */' },
      { name: 'newproject.css', start: '/* New Project Modal */', end: '/* Legacy api-toggle */' },
      { name: 'legacy.css',    start: '/* Legacy api-toggle */', end: null },
    ]
  },
  {
    file: 'components.css', dir: 'components',
    sections: [
      { name: 'buttons.css',   start: '/* Buttons */', end: '/* Form elements */' },
      { name: 'forms.css',     start: '/* Form elements */', end: '/* Range Slider */' },
      { name: 'range.css',     start: '/* Range Slider */', end: '/* Toggle Switch */' },
      { name: 'toggle.css',    start: '/* Toggle Switch */', end: '/* File explorer */' },
      { name: 'workspace.css', start: '/* File explorer */', end: '/* Toast */' },
      { name: 'toast.css',     start: '/* Toast */', end: '/* Error Boundary */' },
      { name: 'misc.css',      start: '/* Error Boundary */', end: null },
    ]
  },
  {
    file: 'sidebar.css', dir: 'sidebar',
    sections: [
      { name: 'logo.css',       start: '.devagents-logo {', end: '.devagents-section-header' },
      { name: 'headers.css',    start: '.devagents-section-header', end: '.devagents-teams-list' },
      { name: 'teams.css',      start: '.devagents-teams-list', end: '.devagents-conversations-list' },
      { name: 'conversations.css', start: '.devagents-conversations-list', end: '.devagents-projects-list' },
      { name: 'projects.css',    start: '.devagents-projects-list', end: '.devagents-user-menu' },
      { name: 'usermenu.css',    start: '.devagents-user-menu', end: '.devagents-back-btn' },
      { name: 'misc.css',        start: '.devagents-back-btn', end: null },
    ]
  },
];

for (const cfg of configs) {
  const src = readFileSync(resolve(ROOT, cfg.file), 'utf-8');
  const outDir = resolve(ROOT, cfg.dir);
  mkdirSync(outDir, { recursive: true });

  const files = {};

  for (const sec of cfg.sections) {
    const startIdx = src.indexOf(sec.start);
    if (startIdx === -1) {
      console.warn(`Section "${sec.start}" not found in ${cfg.file}`);
      continue;
    }
    const endIdx = sec.end ? src.indexOf(sec.end, startIdx + sec.start.length) : src.length;
    const content = endIdx === -1 ? src.slice(startIdx) : src.slice(startIdx, endIdx).trim();
    if (!files[sec.name]) files[sec.name] = [];
    files[sec.name].push(content);
  }

  const imports = [];
  for (const [name, contents] of Object.entries(files)) {
    const code = contents.join('\n\n');
    writeFileSync(resolve(outDir, name), code + '\n');
    imports.push(`@import './${name}';`);
  }

  writeFileSync(resolve(outDir, 'index.css'), imports.join('\n') + '\n');
  console.log(`${cfg.file} → ${cfg.dir}/ (${Object.keys(files).length} files)`);
}
