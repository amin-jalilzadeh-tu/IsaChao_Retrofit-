const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

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
    await page.waitForFunction(() => document.body.innerText.includes('Online'), { timeout: 15000 });
    console.log('Backend is online!');

    // Take screenshot before
    await page.screenshot({ path: 'before-run.png' });

    // Use JavaScript to click the button directly (bypass z-index issues)
    console.log('Clicking Run Predictions via JavaScript...');
    const clicked = await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const runBtn = btns.find(b => b.textContent?.includes('Run Predictions'));
      if (runBtn) {
        runBtn.click();
        return true;
      }
      return false;
    });

    console.log('Button clicked:', clicked);

    // Wait for the API call to complete
    console.log('Waiting for predictions...');
    await page.waitForTimeout(10000);

    // Take screenshot after
    await page.screenshot({ path: 'after-run.png' });
    console.log('Screenshot saved: after-run.png');

    // Check results
    const pageText = await page.evaluate(() => document.body.innerText);
    const hasNoResults = pageText.includes('No Results Yet');
    const hasGJ = pageText.includes('GJ');
    const hasComplete = pageText.includes('Complete') || pageText.includes('completed');

    console.log('Still "No Results Yet":', hasNoResults);
    console.log('Contains GJ:', hasGJ);
    console.log('Contains Complete:', hasComplete);

    // Get console log content
    const consoleContent = await page.evaluate(() => {
      const consolePre = document.querySelector('pre');
      if (consolePre) return consolePre.textContent || '';
      const consoleDiv = document.querySelector('[class*="console-content"]');
      return consoleDiv?.textContent || 'Console not found';
    });
    console.log('Console content:', consoleContent.substring(0, 500));

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
})();
