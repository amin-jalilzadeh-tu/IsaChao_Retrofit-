const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  const errors = [];
  page.on('pageerror', err => errors.push(err.message));
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
  });

  try {
    await page.goto('http://localhost:4200', { timeout: 30000, waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    // Take screenshot
    await page.screenshot({ path: 'frontend-state.png', fullPage: false });
    console.log('Screenshot saved: frontend-state.png');

    // Get page title
    const title = await page.title();
    console.log('Page title:', title);

    // Look for visible text content
    const bodyText = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button')).map(b => b.textContent?.trim()).filter(Boolean);
      const links = Array.from(document.querySelectorAll('a')).map(a => a.textContent?.trim()).filter(Boolean);
      return { buttons: buttons.slice(0, 10), links: links.slice(0, 10) };
    });
    console.log('Buttons found:', bodyText.buttons);
    console.log('Links found:', bodyText.links);

    if (errors.length > 0) {
      console.log('\nErrors:', errors.slice(0, 5));
    }

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
})();
