const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });

  try {
    console.log('Loading page...');
    await page.goto('http://localhost:4200', { timeout: 60000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    // Close the intro modal
    const closeBtn = await page.locator('button:has-text("Sluiten")');
    if (await closeBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      console.log('Closing intro modal...');
      await closeBtn.click();
      await page.waitForTimeout(1000);
    }

    // Find the sidebar buttons - look for the Renew/sync icon
    console.log('Looking for Retrofit Analysis tool in sidebar...');

    // Get all buttons in the left sidebar area
    const sidebarButtons = await page.$$('button');
    console.log(`Found ${sidebarButtons.length} total buttons`);

    // Try clicking buttons until we find the Retrofit tool
    // The Retrofit tool has the Renew icon
    for (let i = 0; i < Math.min(sidebarButtons.length, 10); i++) {
      const btn = sidebarButtons[i];
      const isVisible = await btn.isVisible().catch(() => false);
      if (isVisible) {
        const ariaLabel = await btn.getAttribute('aria-label') || '';
        const title = await btn.getAttribute('title') || '';
        console.log(`Button ${i}: aria-label="${ariaLabel}", title="${title}"`);
      }
    }

    // Take initial screenshot
    await page.screenshot({ path: 'retrofit-1-initial.png', fullPage: false });
    console.log('Screenshot 1 saved');

    // Click button index 1 (typically the second tool)
    if (sidebarButtons.length > 1) {
      const btn = sidebarButtons[1];
      if (await btn.isVisible().catch(() => false)) {
        console.log('Clicking button 1...');
        await btn.click();
        await page.waitForTimeout(3000);
        await page.screenshot({ path: 'retrofit-2-after-click.png', fullPage: false });
        console.log('Screenshot 2 saved');
      }
    }

    // Get text content
    const pageText = await page.evaluate(() => {
      const text = document.body.innerText;
      return text.substring(0, 1000);
    });
    console.log('\nPage text (first 1000 chars):\n', pageText.substring(0, 500));

    if (consoleErrors.length > 0) {
      console.log('\nConsole errors:', consoleErrors.slice(0, 5));
    }

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
})();
