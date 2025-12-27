const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  const logs = [];
  page.on('console', msg => logs.push(`[${msg.type()}] ${msg.text()}`));

  try {
    console.log('Loading page...');
    await page.goto('http://localhost:4200', { timeout: 60000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    // Close intro modal
    const closeBtn = await page.locator('button:has-text("Sluiten")');
    if (await closeBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await closeBtn.click();
      await page.waitForTimeout(1000);
    }

    // Click Retrofit tool icon (3rd icon at y=122)
    console.log('Opening Retrofit tool...');
    await page.mouse.click(16, 122);
    await page.waitForTimeout(3000);

    // Take screenshot after opening
    await page.screenshot({ path: 'retrofit-test-1.png' });
    console.log('Screenshot 1: retrofit-test-1.png');

    // Check backend status
    const statusText = await page.evaluate(() => {
      const el = document.body.innerText;
      if (el.includes('CONNECTED')) return 'CONNECTED';
      if (el.includes('DISCONNECTED')) return 'DISCONNECTED';
      return 'UNKNOWN';
    });
    console.log('Backend status:', statusText);

    // Wait a few seconds for backend check
    await page.waitForTimeout(3000);

    // Check status again
    const statusText2 = await page.evaluate(() => {
      const el = document.body.innerText;
      if (el.includes('CONNECTED')) return 'CONNECTED';
      if (el.includes('DISCONNECTED')) return 'DISCONNECTED';
      return 'UNKNOWN';
    });
    console.log('Backend status after wait:', statusText2);

    // Try to click "Run" button
    console.log('Looking for Run button...');
    const runButton = await page.locator('button:has-text("Run")');
    if (await runButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      console.log('Clicking Run button...');
      await runButton.click();
      await page.waitForTimeout(5000);

      await page.screenshot({ path: 'retrofit-test-2-after-run.png' });
      console.log('Screenshot 2: retrofit-test-2-after-run.png');
    } else {
      console.log('Run button not found or not visible');
    }

    // Check console logs for API calls
    const apiLogs = logs.filter(l =>
      l.includes('localhost:8000') ||
      l.includes('inference') ||
      l.includes('API') ||
      l.includes('Error') ||
      l.includes('predictions')
    );
    console.log('\nRelevant logs:', apiLogs.slice(0, 10));

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
})();
