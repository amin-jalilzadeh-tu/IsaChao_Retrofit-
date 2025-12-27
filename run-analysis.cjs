const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  const logs = [];
  page.on('console', msg => {
    if (msg.type() === 'log' || msg.type() === 'info' || msg.type() === 'error') {
      logs.push(`[${msg.type()}] ${msg.text()}`);
    }
  });

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

    // Click Retrofit tool icon
    console.log('Opening Retrofit tool...');
    await page.mouse.click(16, 122);
    await page.waitForTimeout(3000);

    // Wait for backend to be online
    console.log('Waiting for backend...');
    await page.waitForFunction(() => document.body.innerText.includes('Online'), { timeout: 15000 });
    console.log('Backend is online!');

    // Take screenshot before run
    await page.screenshot({ path: 'analysis-1-before.png' });

    // Find and click the Run Analysis button in the sidebar
    console.log('Looking for Run Analysis...');

    // The "Run Analysis" section should be in the navigation tree
    // Let's click on it to expand/access run controls
    const runAnalysisLink = await page.locator('text=Run Analysis');
    if (await runAnalysisLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      console.log('Clicking Run Analysis...');
      await runAnalysisLink.click();
      await page.waitForTimeout(1000);
    }

    // Look for the Run button
    const runButton = await page.locator('button:has-text("Run Predictions"), button:has-text("Run"), button:has-text("Execute")');
    if (await runButton.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      console.log('Clicking Run button...');
      await runButton.first().click();
      await page.waitForTimeout(8000);  // Wait for predictions
    }

    // Take screenshot after run
    await page.screenshot({ path: 'analysis-2-after.png' });
    console.log('Screenshot saved: analysis-2-after.png');

    // Check for results
    const pageText = await page.evaluate(() => document.body.innerText);
    const hasPredictions = pageText.includes('GJ') || pageText.includes('EUR') || pageText.includes('kg') || pageText.includes('predictions');
    const hasResults = !pageText.includes('No Results Yet');

    console.log('Has predictions keywords:', hasPredictions);
    console.log('Has results (not "No Results Yet"):', hasResults);

    // Get console content
    const consoleText = await page.evaluate(() => {
      const consoleEl = document.querySelector('[class*="console"]');
      return consoleEl?.textContent || 'Console not found';
    });
    console.log('Console content:', consoleText.substring(0, 200));

    // Print browser console logs related to API
    const apiLogs = logs.filter(l => l.includes('inference') || l.includes('API') || l.includes('prediction') || l.includes('8000'));
    if (apiLogs.length > 0) {
      console.log('\nAPI-related browser logs:', apiLogs.slice(0, 5));
    }

  } catch (error) {
    console.error('Error:', error.message);
    await page.screenshot({ path: 'analysis-error.png' });
  } finally {
    await browser.close();
  }
})();
