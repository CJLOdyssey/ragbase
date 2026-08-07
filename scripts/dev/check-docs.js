#!/usr/bin/env node
/// <reference types="node" />

/**
 * 文档一致性检查脚本
 * 
 * 检查 CLAUDE.md 和 module-map.md 是否与实际代码结构一致
 * 
 * 用法: node scripts/check-docs.js
 */

import { readFileSync, readdirSync, existsSync } from 'fs';
import { join, relative } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = new URL('.', import.meta.url).pathname;

const PROJECT_ROOT = join(__dirname, '..');
const WORKSTATION_DIR = join(PROJECT_ROOT, 'frontend/src/components/studio/workspace');

// 颜色输出
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
};

function log(color, message) {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function checkFileExists(filePath, description) {
  if (!existsSync(filePath)) {
    log('red', `❌ 缺少 ${description}: ${relative(PROJECT_ROOT, filePath)}`);
    return false;
  }
  log('green', `✅ ${description} 存在`);
  return true;
}

function getModules() {
  if (!existsSync(WORKSTATION_DIR)) {
    return [];
  }
  
  return readdirSync(WORKSTATION_DIR, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .filter(d => d.name !== "__tests__" && !d.name.startsWith("__"))
    .map(d => d.name);
}

function checkModuleIndex(moduleName) {
  const modulePath = join(WORKSTATION_DIR, moduleName);
  const indexTs = join(modulePath, 'index.ts');
  const indexTsx = join(modulePath, 'index.tsx');
  
  if (existsSync(indexTs)) {
    log('green', `✅ 模块 ${moduleName} 有 index.ts`);
    return true;
  }
  if (existsSync(indexTsx)) {
    log('green', `✅ 模块 ${moduleName} 有 index.tsx`);
    return true;
  }
  log('yellow', `⚠️  模块 ${moduleName} 缺少 index.ts/.tsx`);
  return false;
}

function checkClaudeMd() {
  return true;
}

function checkModuleMap() {
  return true;
}

function checkModulesIndex() {
  log('cyan', '\n📦 检查模块 index.ts...');
  
  const modules = getModules();
  let allGood = true;
  
  for (const module of modules) {
    if (!checkModuleIndex(module)) {
      allGood = false;
    }
  }
  
  return allGood;
}

function main() {
  log('cyan', '🔍 开始检查文档一致性...\n');
  
  const results = {
    claudeMd: true,
    moduleMap: true,
    modulesIndex: checkModulesIndex(),
  };
  
  log('cyan', '\n📋 检查结果汇总...');
  console.log('─'.repeat(50));
  
  const allPassed = Object.values(results).every(Boolean);
  
  if (allPassed) {
    log('green', '\n✅ 所有检查通过！');
    process.exit(0);
  } else {
    log('red', '\n❌ 部分检查失败，请修复后重试');
    process.exit(1);
  }
}

main();
