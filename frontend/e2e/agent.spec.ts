import { test, expect } from '@playwright/test';

const PROMPT_NAME = process.env.E2E_PROMPT_NAME ?? '2222';

let seq = 0;
function uid(prefix: string): string {
  return `${prefix}-${++seq}-${Date.now().toString(36).slice(-4)}`;
}

/** 进入 Agent 管理工作台 Tab */
async function gotoAgentTab(page: import('@playwright/test').Page) {
  await page.goto('/');
  await page.getByRole('button', { name: /在线状态/ }).waitFor({ timeout: 15000 });
  await page.getByRole('button', { name: /在线状态/ }).click();
  await page.getByRole('button', { name: '管理工作台', exact: true }).click();
  await page.getByRole('button', { name: 'Agent 管理', exact: true }).click();
  await expect(page.getByRole('button', { name: '新建 Agent', exact: true })).toBeVisible();
}

/** 打开新建 Agent 弹窗并返回 dialog 定位器 */
async function openCreateAgentForm(page: import('@playwright/test').Page) {
  await page.getByRole('button', { name: '新建 Agent', exact: true }).first().click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByPlaceholder('2-30 个字符')).toBeVisible();
  return dialog;
}

/** 关闭当前弹窗（点右上角关闭按钮，比 Escape 可靠） */
async function closeAnyDialog(page: import('@playwright/test').Page) {
  const closeBtn = page.getByRole('dialog').getByRole('button', { name: '关闭', exact: true });
  if (await closeBtn.isVisible().catch(() => false)) {
    await closeBtn.first().click({ timeout: 3000 }).catch(() => {});
    await page.waitForTimeout(300);
  }
}

/** 在弹窗中选择系统提示词（表单必选） */
async function pickPrompt(page: import('@playwright/test').Page) {
  await page.getByText('选择提示词', { exact: true }).click();
  await page.getByText(PROMPT_NAME, { exact: true }).click();
  await page.getByRole('button', { name: '确认', exact: true }).click();
}

/** 创建 Agent（默认提示词，状态默认已停止） */
async function createAgent(page: import('@playwright/test').Page, name: string) {
  const dialog = await openCreateAgentForm(page);
  await dialog.getByPlaceholder('2-30 个字符').fill(name);
  await pickPrompt(page);
  await dialog.getByRole('button', { name: '新建 Agent', exact: true }).click();
  await expect(page.getByText('Agent 已创建').first()).toBeVisible();
  await expect(dialog).not.toBeVisible();
}

/** 点击表格行操作菜单 */
async function clickRowAction(page: import('@playwright/test').Page, name: string) {
  const row = page.locator('tr', { hasText: name }).first();
  await expect(row).toBeVisible({ timeout: 10000 });
  await row.hover();
  await row.getByRole('button').click();
}

/** 搜索并等待该 Agent 行出现 */
async function searchForAgent(page: import('@playwright/test').Page, name: string) {
  await page.getByPlaceholder('搜索 Agent 名称、团队、模型...').fill(name);
  await expect(page.locator('tr', { hasText: name }).first()).toBeVisible({ timeout: 10000 });
}

/** 重置搜索 + 团队筛选 + 状态筛选 */
async function resetFilters(page: import('@playwright/test').Page) {
  await page.getByPlaceholder('搜索 Agent 名称、团队、模型...').fill('');
  const selects = page.getByRole('toolbar').locator('.ant-select');
  await selects.nth(0).click();
  await page.locator('.ant-select-item-option').filter({ hasText: '全部团队' }).click();
  await selects.nth(1).click();
  await page.locator('.ant-select-item-option').filter({ hasText: '全部状态' }).click();
  await page.waitForTimeout(300);
}

/** 批量删除当前页全部已停止 Agent（运行中不可删，自动跳过） */
async function deleteAllAgents(page: import('@playwright/test').Page) {
  for (let i = 0; i < 10; i++) {
    const cb = page.getByRole('checkbox', { name: '全选本页', exact: true });
    if (!(await cb.isVisible().catch(() => false))) break;
    await cb.check();
    const runningRows = page.locator('tr', { hasText: '运行中' });
    const runningCount = await runningRows.count();
    for (let r = 0; r < runningCount; r++) {
      await runningRows.nth(r).locator('input[type="checkbox"]').uncheck();
    }
    const btn = page.getByRole('button', { name: /批量删除/ });
    if (!(await btn.isVisible().catch(() => false))) break;
    await btn.click();
    await page.getByRole('button', { name: '确认删除', exact: true }).click();
    await page.waitForTimeout(500);
  }
}

test('Agent 管理 E2E', async ({ page }) => {
  page.on('pageerror', (err) => console.log(`[JS错误] ${err.message}`));

  await gotoAgentTab(page);

  // ═══ E1-01 创建 Agent 并验证 ═══
  await test.step('E1-01 创建 Agent', async () => {
    const name = uid('E2E-Agent-创建');
    await createAgent(page, name);
    await searchForAgent(page, name);
    await page.getByPlaceholder('搜索 Agent 名称、团队、模型...').fill('');
  });

  // ═══ E1-02 编辑基本信息 ═══
  await test.step('E1-02 编辑 Agent', async () => {
    const name = uid('E2E-Agent-编辑');
    await createAgent(page, name);
    await searchForAgent(page, name);

    await clickRowAction(page, name);
    await page.getByRole('menuitem', { name: '编辑 Agent' }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog.getByPlaceholder('2-30 个字符')).toBeVisible();

    await dialog.getByPlaceholder('2-30 个字符').fill(uid('E2E-Agent-已重命名'));
    // 后端未持久化 systemPromptId，编辑时必须重选提示词
    await pickPrompt(page);
    const modelSelect = dialog.getByRole('combobox').nth(1);
    const modelLabels = await modelSelect.locator('option').allTextContents();
    if (modelLabels.length > 2) {
      await modelSelect.selectOption({ label: modelLabels[2] });
    }
    await dialog.getByRole('button', { name: '保存修改', exact: true }).click();
    await expect(page.getByText('Agent 已更新').first()).toBeVisible();
  });

  // ═══ E1-03 删除 Agent ═══
  await test.step('E1-03 删除 Agent', async () => {
    const name = uid('E2E-Agent-删除');
    await createAgent(page, name);
    await searchForAgent(page, name);

    await clickRowAction(page, name);
    await page.getByRole('menuitem', { name: '删除' }).click();
    await page.getByRole('button', { name: '确认删除', exact: true }).click();
    await expect(page.getByText('Agent 已删除').first()).toBeVisible();
    await expect(page.locator('tr', { hasText: name })).not.toBeVisible();
  });

  // ═══ E1-07 搜索筛选 ═══
  await test.step('E1-07 搜索筛选', async () => {
    await resetFilters(page);
    const name = uid('搜索');
    await createAgent(page, name);
    await page.getByPlaceholder('搜索 Agent 名称、团队、模型...').fill('搜索');
    await expect(page.locator('tr', { hasText: name })).toBeVisible({ timeout: 5000 });
    await page.getByPlaceholder('搜索 Agent 名称、团队、模型...').fill('');
  });

  // ═══ E1-08 状态筛选 + 状态徽标 ═══
  await test.step('E1-08 状态筛选', async () => {
    await resetFilters(page);
    const name = uid('E2E-停用');
    await createAgent(page, name);
    await searchForAgent(page, name);
    await expect(page.locator('tr', { hasText: name }).getByText('已停止')).toBeVisible();

    // 搜索已命中该 Agent，叠加状态筛选确认未被排除
    const toolbar = page.getByRole('toolbar');
    await toolbar.locator('.ant-select').nth(1).click();
    await page.locator('.ant-select-item-option').filter({ hasText: '已停止' }).click();
    await expect(page.locator('tr', { hasText: name })).toBeVisible();
  });

  // ═══ E1-10 批量删除 ═══
  await test.step('E1-10 批量删除', async () => {
    await resetFilters(page);
    const a = uid('E2E-批量A');
    const b = uid('E2E-批量B');
    await createAgent(page, a);
    await createAgent(page, b);
    // 用公共前缀搜索，把两行固定在同一页
    await page.getByPlaceholder('搜索 Agent 名称、团队、模型...').fill('E2E-批量');
    await page.getByRole('checkbox', { name: `选择 ${a}` }).check();
    await page.getByRole('checkbox', { name: `选择 ${b}` }).check();
    await page.getByRole('button', { name: /批量删除/ }).click();
    await page.getByRole('button', { name: '确认删除', exact: true }).click();
    await expect(page.getByText(/已删除 \d+ 个 Agent/)).toBeVisible();
  });

  // ═══ E1-12 空状态 ═══
  await test.step('E1-12 空状态', async () => {
    await resetFilters(page);
    await deleteAllAgents(page);
    await expect(page.getByText('暂无 Agent')).toBeVisible();
  });

  // ═══ E1-13 搜索空状态 ═══
  await test.step('E1-13 搜索空状态', async () => {
    await page.getByPlaceholder('搜索 Agent 名称、团队、模型...').fill('__NONEXISTENT__');
    await expect(page.getByText('暂无 Agent')).toBeVisible({ timeout: 5000 });
    await page.getByPlaceholder('搜索 Agent 名称、团队、模型...').fill('');
  });

  // ═══ E1-14 分页 ═══
  await test.step('E1-14 分页', async () => {
    await resetFilters(page);
    for (let i = 0; i < 8; i++) {
      await createAgent(page, uid('E2E-分页'));
    }
    await expect(page.locator('.ant-pagination')).toBeVisible();
  });

  // ═══ E1-17 错误处理 - 创建接口 500 ═══
  await test.step('E1-17 错误处理', async () => {
    await gotoAgentTab(page);
    await page.route('**/api/agents', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: '模拟服务端错误' }),
        });
      } else {
        await route.continue();
      }
    });

    const dialog = await openCreateAgentForm(page);
    await dialog.getByPlaceholder('2-30 个字符').fill(uid('E2E-错误'));
    await pickPrompt(page);
    await dialog.getByRole('button', { name: '新建 Agent', exact: true }).click();

    await expect(page.getByRole('button', { name: '重试', exact: true })).toBeVisible({ timeout: 10000 });
    await expect(dialog).toBeVisible();
    await closeAnyDialog(page);
    await page.unroute('**/api/agents');
  });

  // ═══ E1-18 表单验证 - 名称为空 ═══
  await test.step('E1-18 表单验证', async () => {
    await gotoAgentTab(page);
    const dialog = await openCreateAgentForm(page);
    await dialog.getByRole('button', { name: '新建 Agent', exact: true }).click();
    await expect(dialog.getByText('Agent 名称不能为空')).toBeVisible();
    await expect(dialog).toBeVisible();
    await closeAnyDialog(page);
  });
});
