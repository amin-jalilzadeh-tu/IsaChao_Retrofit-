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

    // Find all buttons and list them
    const buttons = await page.$$eval('button', btns =>
      btns.map(b => ({
        text: b.textContent?.trim(),
        disabled: b.disabled,
        visible: b.offsetHeight > 0
      })).filter(b => b.text)
    );
    console.log('All buttons:', buttons.filter(b => b.text && b.text.length < 30));

    // Look for "Run Predictions" button specifically
    console.log('\nLooking for Run Predictions button...');
    const runPredictionsBtn = await page.locator('button:has-text("Run Predictions")');

    if (await runPredictionsBtn.count() > 0) {
      console.log('Found Run Predictions button!');

      // Scroll it into view
      await runPredictionsBtn.scrollIntoViewIfNeeded();
      await page.waitForTimeout(500);

      // Take screenshot showing the button
      await page.screenshot({ path: 'run-button-visible.png' });
      console.log('Screenshot saved: run-button-visible.png');

      // Check if enabled
      const isDisabled = await runPredictionsBtn.isDisabled();
      console.log('Button disabled:', isDisabled);

      if (!isDisabled) {
        console.log('Clicking Run Predictions...');
        await runPredictionsBtn.click();
        await page.waitForTimeout(10000);  // Wait for inference

        await page.screenshot({ path: 'after-run-predictions.png' });
        console.log('Screenshot saved: after-run-predictions.png');

        // Check for results
        const pageText = await page.evaluate(() => document.body.innerText);
        const hasNoResults = pageText.includes('No Results Yet');
        console.log('Still showing "No Results Yet":', hasNoResults);

        // Check console for activity
        const consoleText = await page.evaluate(() => {
          const el = document.querySelector('[class*="console"]');
          return el?.innerText || '';
        });
        console.log('Console content:', consoleText.substring(0, 300));
      } else {
        console.log('Button is disabled - checking why...');
        const headerText = await page.evaluate(() => {
          const header = document.querySelector('[class*="header"]');
          return header?.innerText || '';
        });
        console.log('Header:', headerText);
      }
    } else {
      console.log('Run Predictions button not found!');

      // Take screenshot to see current state
      await page.screenshot({ path: 'no-run-button.png' });
    }

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
})();
