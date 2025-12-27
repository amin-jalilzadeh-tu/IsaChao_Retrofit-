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

    // Click Retrofit tool icon (3rd icon at y=122)
    console.log('Opening Retrofit tool...');
    await page.mouse.click(16, 122);
    await page.waitForTimeout(2000);

    // Monitor status for up to 30 seconds
    console.log('Monitoring backend status...');
    for (let i = 0; i < 10; i++) {
      const pageText = await page.evaluate(() => document.body.innerText);

      const hasOnline = pageText.includes('Online');
      const hasOffline = pageText.includes('Offline');
      const hasConnected = pageText.includes('CONNECTED');
      const hasDisconnected = pageText.includes('DISCONNECTED');

      console.log(`Check ${i + 1}: Online=${hasOnline}, Offline=${hasOffline}, Connected=${hasConnected}, Disconnected=${hasDisconnected}`);

      if (hasOnline || hasConnected) {
        console.log('Backend is ONLINE!');
        await page.screenshot({ path: 'retrofit-online.png' });
        console.log('Screenshot saved: retrofit-online.png');
        break;
      }

      await page.waitForTimeout(3000);
    }

    // Final screenshot
    await page.screenshot({ path: 'retrofit-final-status.png' });
    console.log('Final screenshot saved: retrofit-final-status.png');

    // Get full status area text
    const statusText = await page.evaluate(() => {
      // Try to find status elements
      const statusItems = document.querySelectorAll('[class*="status"]');
      return Array.from(statusItems).map(el => el.textContent?.trim()).filter(Boolean).join(' | ');
    });
    console.log('Status text:', statusText);

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
})();
