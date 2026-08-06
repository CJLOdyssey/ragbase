#!/usr/bin/env node

/**
 * 文档自动生成脚本
 * 
 * 扫描代码结构，自动生成模块文档
 * 
 * 用法: node scripts/generate-docs.js
 */

import { readFileSync, writeFileSync, readdirSync, existsSync } from 'fs';
import { join, relative } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = new URL('.', import.meta.url).pathname;

const PROJECT_ROOT = join(__dirname, '..');
const WORKSTATION_DIR = join(PROJECT_ROOT, 'frontend/src/components/agentstudio/workstation');
const DOCS_DIR = join(PROJECT_ROOT, 'docs');

const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  cyan: '\x1b[36m',
};

function log(color, message) {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function getModuleInfo(moduleName) {
  const modulePath = join(WORKSTATION_DIR, moduleName);
  const files = readdirSync(modulePath);
  
  const info = {
    name: moduleName,
    path: relative(PROJECT_ROOT, modulePath),
    hasIndex: files.includes('index.ts'),
    hasTypes: files.some(f => f.endsWith('.types.ts')),
    hasConstants: files.some(f => f.endsWith('.constants.ts')),
    hasManagement: files.some(f => f.includes('Management.tsx')),
    hasFormModal: files.some(f => f.includes('FormModal.tsx')),
    files: files.filter(f => !f.startsWith('.') && !f.startsWith('__')),
  };
  
  return info;
}

function generateModuleTable(modules) {
  let table = '| 模块 | 路径 | 有索引 | 有类型 | 有常量 | 有管理页 | 有表单 |\n';
  table += '|------|------|--------|--------|--------|----------|--------|\n';
  
  for (const mod of modules) {
    const indexIcon = mod.hasIndex ? '✅' : '❌';
    const typesIcon = mod.hasTypes ? '✅' : '❌';
    const constantsIcon = mod.hasConstants ? '✅' : '❌';
    const managementIcon = mod.hasManagement ? '✅' : '❌';
    const formIcon = mod.hasFormModal ? '✅' : '❌';
    
    table += `| ${mod.name} | \`${mod.path}\` | ${indexIcon} | ${typesIcon} | ${constantsIcon} | ${managementIcon} | ${formIcon} |\n`;
  }
  
  return table;
}

function generateModuleDetails(modules) {
  let details = '';
  
  for (const mod of modules) {
    details += `### ${mod.name}\n\n`;
    details += `**路径**: \`${mod.path}\`\n\n`;
    details += '**文件列表**:\n\n';
    
    for (const file of mod.files) {
      const icon = file.endsWith('.tsx') ? '📄' : 
                   file.endsWith('.ts') ? '📜' : '📁';
      details += `- ${icon} ${file}\n`;
    }
    
    details += '\n';
  }
  
  return details;
}

function generateDocs() {
  log('cyan', '📚 开始生成文档...\n');
  
  if (!existsSync(WORKSTATION_DIR)) {
    log('yellow', '⚠️  工作台目录不存在，跳过生成');
    return;
  }
  
  const moduleNames = readdirSync(WORKSTATION_DIR, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .map(d => d.name);
  
  const modules = moduleNames.map(getModuleInfo);
  
  // 生成模块文档
  const moduleDoc = `# 📦 工作台模块文档

> 本文档由脚本自动生成，请勿手动编辑

---

## 模块概览

${generateModuleTable(modules)}

---

## 模块详情

${generateModuleDetails(modules)}

---

*生成时间: ${new Date().toISOString()}*
`;
  
  writeFileSync(join(DOCS_DIR, 'modules.md'), moduleDoc);
  log('green', '✅ 生成 docs/modules.md');
  
  // 生成模块列表 JSON（供其他脚本使用）
  const moduleList = modules.map(m => ({
    name: m.name,
    path: m.path,
    hasIndex: m.hasIndex,
  }));
  
  writeFileSync(join(DOCS_DIR, 'modules.json'), JSON.stringify(moduleList, null, 2));
  log('green', '✅ 生成 docs/modules.json');
  
  log('cyan', '\n📋 文档生成完成！');
}

generateDocs();
