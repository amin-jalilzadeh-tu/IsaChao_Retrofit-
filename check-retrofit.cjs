const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  // Collect console messages
  const consoleMessages = [];
  page.on('console', msg => {
    consoleMessages.push(`[${msg.type()}] ${msg.text()}`);
  });

  // Collect errors
  const errors = [];
  page.on('pageerror', err => {
    errors.push(err.message);
  });

  try {
    console.log('Navigating to localhost:4200...');
    await page.goto('http://localhost:4200', { timeout: 30000, waitUntil: 'networkidle' });

    // Wait a bit for any modals
    await page.waitForTimeout(2000);

    // Try to close any intro modal
    const closeButton = await page.$('button:has-text("Close")');
    if (closeButton) {
      console.log('Closing modal...');
      await closeButton.click();
      await page.waitForTimeout(1000);
    }

    // Look for the Tools menu or RetrofitDetailed link
    console.log('Looking for Tools menu...');

    // Take a screenshot of the current state
    await page.screenshot({ path: 'retrofit-check-1.png', fullPage: false });
    console.log('Screenshot 1 saved: retrofit-check-1.png');

    // Try to find and click on the Tools button/menu
    const toolsButton = await page.$('button:has-text("Tools"), [aria-label*="Tool"], .tool-menu, .tools-panel');
    if (toolsButton) {
      console.log('Found tools button, clicking...');
      await toolsButton.click();
      await page.waitForTimeout(1000);
    }

    // Look for RetrofitDetailed
    const retrofitLink = await page.$('text=Retrofit, text=Energy, a:has-text("Retrofit")');
    if (retrofitLink) {
      console.log('Found Retrofit link, clicking...');
      await retrofitLink.click();
      await page.waitForTimeout(2000);
    }

    // Take another screenshot
    await page.screenshot({ path: 'retrofit-check-2.png', fullPage: false });
    console.log('Screenshot 2 saved: retrofit-check-2.png');

    // Print collected console messages
    console.log('\n--- Console Messages ---');
    consoleMessages.slice(-20).forEach(msg => console.log(msg));

    // Print errors
    if (errors.length > 0) {
      console.log('\n--- Page Errors ---');
      errors.forEach(err => console.log(err));
    }

    // Get the page HTML structure to understand the UI
    const toolsList = await page.$$eval('[class*="tool"], [class*="menu"], nav a, .sidebar a', els =>
      els.slice(0, 20).map(el => ({ text: el.textContent?.trim(), class: el.className }))
    );
    console.log('\n--- Found UI Elements ---');
    toolsList.forEach(el => console.log(`  ${el.text}: ${el.class}`));

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
})();
