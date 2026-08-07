import { expect, test as setup } from '@playwright/test';

const authFile = '.auth/user.json';

const API_BASE = process.env.E2E_API_BASE ?? 'http://localhost:8081';
const USER = {
  email: process.env.E2E_USER_EMAIL ?? 'e2e-user@example.com',
  password: process.env.E2E_USER_PASSWORD ?? 'Test1234!',
};

const PROMPT_NAME = process.env.E2E_PROMPT_NAME ?? '2222';

setup('登录并保存认证状态', async ({ page }) => {
  // 登录响应 Set-Cookie（httpOnly access/refresh token）自动落入 page context
  const res = await page.request.post(`${API_BASE}/api/auth/login`, {
    data: { email: USER.email, password: USER.password },
  });
  expect(res.ok()).toBeTruthy();

  await page.goto('/');
  await page
    .getByRole('button', { name: /在线状态/ })
    .waitFor({ timeout: 10000 });

  // Agent 表单必选提示词，CI 空库需预置一个，幂等
  const existing = await page.request.get(`${API_BASE}/api/prompts`);
  const prompts: { name: string }[] = await existing.json();
  if (!prompts.some((p) => p.name === PROMPT_NAME)) {
    await page.request.post(`${API_BASE}/api/prompts`, {
      data: {
        name: PROMPT_NAME,
        category: 'system',
        content: 'E2E 系统提示词',
        status: 'active',
      },
    });
  }

  await page.context().storageState({ path: authFile });
});
