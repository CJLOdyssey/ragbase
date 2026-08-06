const { chromium } = require('playwright');

const CHROME_PATH = '/home/odyssey/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome';

async function main() {
  const browser = await chromium.launch({
    executablePath: CHROME_PATH,
    headless: true,
    args: ['--no-sandbox'],
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  console.log('=== Page loaded ===');
  await page.screenshot({ path: '/tmp/homepage.png', fullPage: false });

  const buttons = await page.locator('button, a, [role="button"]').all();
  console.log(`Found ${buttons.length} interactive elements`);

  for (const btn of buttons.slice(0, 50)) {
    const text = await btn.textContent();
    const tag = await btn.evaluate(el => el.tagName);
    const cls = await btn.evaluate(el => el.className);
    const visible = await btn.isVisible();
    if (visible) {
      console.log(`  ${tag} .${(cls || '').substring(0, 50)} : "${(text || '').trim().substring(0, 80)}"`);
    }
  }

  await browser.close();
  console.log('Done');
}

main().catch(e => { console.error(e); process.exit(1); });
