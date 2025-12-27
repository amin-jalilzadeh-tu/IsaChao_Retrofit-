const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  try {
    console.log('Loading page...');
    await page.goto('http://localhost:4200', { timeout: 60000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    // Close the intro modal
    const closeBtn = await page.locator('button:has-text("Sluiten")');
    if (await closeBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await closeBtn.click();
      await page.waitForTimeout(1000);
    }

    // The sidebar icons are stacked vertically, starting around y=50
    // Each icon is approximately 36px tall
    const iconYPositions = [50, 86, 122, 158, 194, 230, 266];
    const xPosition = 16;

    for (let i = 0; i < iconYPositions.length; i++) {
      console.log(`\n--- Testing icon ${i + 1} at y=${iconYPositions[i]} ---`);

      // Close any open panel first by pressing Escape
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);

      // Click on the icon
      await page.mouse.click(xPosition, iconYPositions[i]);
      await page.waitForTimeout(2000);

      // Check for Retrofit-related content
      const pageText = await page.evaluate(() => document.body.innerText);
      const hasRetrofit = pageText.toLowerCase().includes('retrofit');
      const hasOptimization = pageText.toLowerCase().includes('optimization');
      const hasNSGA = pageText.toLowerCase().includes('nsga');
      const hasPareto = pageText.toLowerCase().includes('pareto');

      console.log(`Contains Retrofit: ${hasRetrofit}`);
      console.log(`Contains Optimization: ${hasOptimization}`);
      console.log(`Contains NSGA: ${hasNSGA}`);
      console.log(`Contains Pareto: ${hasPareto}`);

      // Get first heading
      const headings = await page.$$eval('h1, h2, h3, h4', els =>
        els.map(el => el.textContent?.trim()).filter(Boolean).slice(0, 3)
      );
      console.log(`Headings: ${headings.join(', ')}`);

      if (hasRetrofit || hasOptimization || hasNSGA || hasPareto) {
        console.log('\n*** FOUND RETROFIT TOOL! ***');
        await page.screenshot({ path: 'retrofit-tool-found.png', fullPage: false });
        console.log('Screenshot saved: retrofit-tool-found.png');
        break;
      }
    }

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
})();
