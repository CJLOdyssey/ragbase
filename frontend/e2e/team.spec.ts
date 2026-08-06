import { test, expect } from '@playwright/test';

let seq = 0;
function uid(prefix: string): string {
  return `${prefix}-${++seq}-${Date.now().toString(36).slice(-4)}`;
}

type TeamStatus = 'active' | 'disabled';

/** 进入团队管理工作台 Tab */
async function gotoTeamTab(page: import('@playwright/test').Page) {
  await page.goto('/');
  await page.getByRole('button', { name: /在线状态/ }).waitFor({ timeout: 15000 });
  await page.getByRole('button', { name: /在线状态/ }).click();
  await page.getByRole('button', { name: '管理工作台', exact: true }).click();
  await page.getByRole('button', { name: '团队管理', exact: true }).click();
  await expect(page.getByRole('button', { name: '新建团队', exact: true })).toBeVisible();
}

/** 打开新建团队弹窗并返回 dialog 定位器 */
async function openCreateTeamForm(page: import('@playwright/test').Page) {
  await page.getByRole('button', { name: '新建团队', exact: true }).first().click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByPlaceholder('输入团队名称')).toBeVisible();
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

/** 创建团队：分类为文本输入，状态为表单内唯一 select */
async function createTeam(
  page: import('@playwright/test').Page,
  name: string,
  opts: { category?: string; status?: TeamStatus } = {},
) {
  const dialog = await openCreateTeamForm(page);
  await dialog.getByPlaceholder('输入团队名称').fill(name);
  if (opts.category) await dialog.getByPlaceholder('例如：业务、技术、数据').fill(opts.category);
  if (opts.status) await dialog.getByRole('combobox').selectOption(opts.status);
  await dialog.getByRole('button', { name: '创建团队', exact: true }).click();
  await expect(page.getByText('团队已创建').first()).toBeVisible();
  await expect(dialog).not.toBeVisible();
}

/** 点击表格行操作菜单 */
async function clickRowAction(page: import('@playwright/test').Page, name: string) {
  const row = page.locator('tr', { hasText: name }).first();
  await expect(row).toBeVisible({ timeout: 10000 });
  await row.hover();
  await row.getByRole('button').click();
}

/** 搜索并等待该团队行出现 */
async function searchForTeam(page: import('@playwright/test').Page, name: string) {
  await page.getByPlaceholder('搜索团队名称、描述').fill(name);
  await expect(page.locator('tr', { hasText: name }).first()).toBeVisible({ timeout: 10000 });
}

/** 重置搜索 + 分类筛选 + 状态筛选 */
async function resetFilters(page: import('@playwright/test').Page) {
  await page.getByPlaceholder('搜索团队名称、描述').fill('');
  const selects = page.getByRole('toolbar').locator('.ant-select');
  await selects.nth(0).click();
  await page.locator('.ant-select-item-option').filter({ hasText: '全部分类' }).click();
  await selects.nth(1).click();
  await page.locator('.ant-select-item-option').filter({ hasText: '全部状态' }).click();
  await page.waitForTimeout(300);
}

/** 批量删除当前页全部团队（清空数据） */
async function deleteAllTeams(page: import('@playwright/test').Page) {
  for (let i = 0; i < 10; i++) {
    const cb = page.getByRole('checkbox', { name: '全选本页', exact: true });
    if (!(await cb.isVisible().catch(() => false))) break;
    await cb.check();
    const btn = page.getByRole('button', { name: /批量删除/ });
    if (!(await btn.isVisible().catch(() => false))) break;
    await btn.click();
    await page.getByRole('button', { name: '确认删除', exact: true }).click();
    await page.waitForTimeout(500);
  }
}

test('团队管理 E2E', async ({ page }) => {
  page.on('pageerror', (err) => console.log(`[JS错误] ${err.message}`));

  await gotoTeamTab(page);

  // ═══ E1-01 创建团队 ═══
  await test.step('E1-01 创建团队', async () => {
    const name = uid('E2E-创建');
    await createTeam(page, name);
    await searchForTeam(page, name);
  });

  // ═══ E1-04 删除团队 ═══
  await test.step('E1-04 删除团队', async () => {
    const name = uid('E2E-删除');
    await createTeam(page, name);
    await searchForTeam(page, name);
    await clickRowAction(page, name);
    await page.getByRole('menuitem', { name: '删除' }).click();
    await page.getByRole('button', { name: '确认删除', exact: true }).click();
    await expect(page.getByText('团队已删除').first()).toBeVisible();
  });

  // ═══ E1-02 编辑名称 ═══
  await test.step('E1-02 编辑名称', async () => {
    const name = uid('E2E-待编辑');
    await createTeam(page, name);
    await searchForTeam(page, name);
    await clickRowAction(page, name);
    await page.getByRole('menuitem', { name: '编辑团队' }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog.getByPlaceholder('输入团队名称')).toBeVisible();
    await dialog.getByPlaceholder('输入团队名称').fill(uid('E2E-已重命名'));
    await dialog.getByRole('button', { name: '保存修改', exact: true }).click();
    await expect(page.getByText('团队已更新').first()).toBeVisible();
  });

  // ═══ E1-03 编辑分类/状态 ═══
  await test.step('E1-03 编辑分类/状态', async () => {
    const name = uid('E2E-待修改');
    await createTeam(page, name);
    await searchForTeam(page, name);
    await clickRowAction(page, name);
    await page.getByRole('menuitem', { name: '编辑团队' }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog.getByPlaceholder('输入团队名称')).toBeVisible();
    await dialog.getByPlaceholder('例如：业务、技术、数据').fill('test');
    await dialog.getByRole('combobox').selectOption('disabled');
    await dialog.getByRole('button', { name: '保存修改', exact: true }).click();
    await expect(page.getByText('团队已更新').first()).toBeVisible();
    await expect(page.locator('tr', { hasText: name }).getByText('已停用')).toBeVisible();
  });

  // ═══ E1-06 分类筛选 ═══
  await test.step('E1-06 分类筛选', async () => {
    await resetFilters(page);
    const devName = uid('E2E-开发');
    await createTeam(page, devName, { category: '开发' });
    await createTeam(page, uid('E2E-运维'), { category: '运维' });

    const toolbar = page.getByRole('toolbar');
    await toolbar.locator('.ant-select').nth(0).click();
    await page.locator('.ant-select-item-option').filter({ hasText: '开发' }).click();
    await page.getByPlaceholder('搜索团队名称、描述').fill(devName);
    await expect(page.locator('tr', { hasText: devName })).toBeVisible();
    await page.getByPlaceholder('搜索团队名称、描述').fill('');
    await expect(page.locator('tr', { hasText: 'E2E-运维' })).not.toBeVisible();
  });

  // ═══ E1-07 状态筛选 ═══
  await test.step('E1-07 状态筛选', async () => {
    await resetFilters(page);
    const inactiveName = uid('E2E-停用');
    await createTeam(page, inactiveName, { status: 'disabled' });
    await createTeam(page, uid('E2E-启用'), { status: 'active' });

    const toolbar = page.getByRole('toolbar');
    await toolbar.locator('.ant-select').nth(1).click();
    await page.locator('.ant-select-item-option').filter({ hasText: '已停用' }).click();
    await page.getByPlaceholder('搜索团队名称、描述').fill(inactiveName);
    await expect(page.locator('tr', { hasText: inactiveName })).toBeVisible();
    await page.getByPlaceholder('搜索团队名称、描述').fill('');
    await expect(page.locator('tr', { hasText: 'E2E-启用' })).not.toBeVisible();
  });

  // ═══ E1-08 批量删除 ═══
  await test.step('E1-08 批量删除', async () => {
    await resetFilters(page);
    const a = uid('E2E-批量A');
    const b = uid('E2E-批量B');
    await createTeam(page, a);
    await createTeam(page, b);
    // 用公共前缀搜索，把两行固定在同一页
    await page.getByPlaceholder('搜索团队名称、描述').fill('E2E-批量');
    await page.getByRole('checkbox', { name: `选择 ${a}` }).check();
    await page.getByRole('checkbox', { name: `选择 ${b}` }).check();
    await page.getByRole('button', { name: /批量删除/ }).click();
    await page.getByRole('button', { name: '确认删除', exact: true }).click();
    await expect(page.getByText(/已删除 \d+ 个团队/)).toBeVisible();
  });

  // ═══ E1-09 全选 ═══
  await test.step('E1-09 全选', async () => {
    await resetFilters(page);
    for (let i = 0; i < 3; i++) await createTeam(page, uid('E2E-全选'));
    // 固定在同一页后全选
    await page.getByPlaceholder('搜索团队名称、描述').fill('E2E-全选');
    await page.getByRole('checkbox', { name: '全选本页', exact: true }).check();
    await expect(page.getByRole('button', { name: '批量删除 (3)' })).toBeVisible();
  });

  // ═══ E1-10 空状态 ═══
  await test.step('E1-10 空状态', async () => {
    await resetFilters(page);
    await deleteAllTeams(page);
    await expect(page.getByText('暂无团队', { exact: true })).toBeVisible();
  });

  // ═══ E1-05 搜索筛选 ═══
  await test.step('E1-05 搜索筛选', async () => {
    const name = uid('搜索');
    await createTeam(page, name);
    await page.getByPlaceholder('搜索团队名称、描述').fill('搜索');
    await expect(page.locator('tr', { hasText: name })).toBeVisible();
    await page.getByPlaceholder('搜索团队名称、描述').fill('');
  });

  // ═══ E1-14 成员管理弹窗 ═══
  await test.step('E1-14 成员管理弹窗', async () => {
    await resetFilters(page);
    const name = uid('E2E-成员');
    await createTeam(page, name);
    await searchForTeam(page, name);
    await clickRowAction(page, name);
    await page.getByRole('menuitem', { name: '管理成员' }).click();
    await expect(page.getByRole('heading', { name: '管理成员' })).toBeVisible();
    await closeAnyDialog(page);
  });

  // ═══ E1-15 表单验证 - 名称为空 ═══
  await test.step('E1-15 表单验证', async () => {
    await gotoTeamTab(page);
    const dialog = await openCreateTeamForm(page);
    await dialog.getByRole('button', { name: '创建团队', exact: true }).click();
    await expect(dialog.getByText('团队名称不能为空')).toBeVisible();
    await expect(dialog).toBeVisible();
    await closeAnyDialog(page);
  });

  // ═══ E1-11 搜索空状态 ═══
  await test.step('E1-11 搜索空状态', async () => {
    await gotoTeamTab(page);
    await resetFilters(page);
    await page.getByPlaceholder('搜索团队名称、描述').fill('__NONEXISTENT__');
    await expect(page.getByText('暂无团队', { exact: true })).toBeVisible({ timeout: 5000 });
    await page.getByPlaceholder('搜索团队名称、描述').fill('');
  });

  // ═══ E1-12 分页 ═══
  await test.step('E1-12 分页', async () => {
    await resetFilters(page);
    for (let i = 0; i < 8; i++) await createTeam(page, uid('E2E-分页'));
    await expect(page.locator('.ant-pagination')).toBeVisible();
  });

  // ═══ E1-16 错误处理 - 创建接口 500 ═══
  await test.step('E1-16 错误处理', async () => {
    await gotoTeamTab(page);
    await page.route('**/api/teams', async (route) => {
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

    const dialog = await openCreateTeamForm(page);
    await dialog.getByPlaceholder('输入团队名称').fill(uid('E2E-错误'));
    await dialog.getByRole('button', { name: '创建团队', exact: true }).click();

    await expect(page.getByRole('button', { name: '重试', exact: true })).toBeVisible({ timeout: 10000 });
    await expect(dialog).toBeVisible();
    await closeAnyDialog(page);
    await page.unroute('**/api/teams');
  });
});
