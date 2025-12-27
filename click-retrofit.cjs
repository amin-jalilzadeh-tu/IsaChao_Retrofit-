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
      console.log('Closing intro modal...');
      await closeBtn.click();
      await page.waitForTimeout(1000);
    }

    // Click on the sidebar at position where the 2nd icon is
    // Based on the screenshot, the icons are at approximately x=16 (middle of 32px sidebar)
    // The 2nd icon (Retrofit/Renew) is at approximately y=65
    console.log('Clicking on Retrofit icon position...');
    await page.mouse.click(16, 65);
    await page.waitForTimeout(3000);

    await page.screenshot({ path: 'retrofit-clicked.png', fullPage: false });
    console.log('Screenshot saved: retrofit-clicked.png');

    // Check page content
    const pageText = await page.evaluate(() => document.body.innerText);
    const hasRetrofit = pageText.includes('Retrofit') || pageText.includes('retrofit');
    const hasOptimization = pageText.includes('Optimization') || pageText.includes('NSGA');
    const hasScenario = pageText.includes('Scenario') || pageText.includes('scenario');
    const hasBackend = pageText.includes('Backend') || pageText.includes('API');

    console.log('Page contains "Retrofit":', hasRetrofit);
    console.log('Page contains "Optimization":', hasOptimization);
    console.log('Page contains "Scenario":', hasScenario);
    console.log('Page contains "Backend/API":', hasBackend);

    // Get headings
    const headings = await page.$$eval('h1, h2, h3, h4', els =>
      els.map(el => el.textContent?.trim()).filter(Boolean)
    );
    console.log('Headings:', headings.slice(0, 10));

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
})();
