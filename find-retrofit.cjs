const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  try {
    console.log('Loading page...');
    await page.goto('http://localhost:4200', { timeout: 30000, waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Close the intro modal by clicking "Sluiten" button
    console.log('Closing intro modal...');
    const closeBtn = await page.locator('button:has-text("Sluiten")');
    if (await closeBtn.isVisible()) {
      await closeBtn.click();
      await page.waitForTimeout(1000);
    }

    await page.screenshot({ path: 'after-close.png', fullPage: false });
    console.log('Screenshot 1 saved: after-close.png');

    // Look for sidebar or tool menus
    const allText = await page.evaluate(() => {
      const allElements = document.querySelectorAll('*');
      const texts = [];
      allElements.forEach(el => {
        const text = el.textContent?.trim();
        if (text && text.length < 50 && text.length > 0) {
          texts.push(text);
        }
      });
      return [...new Set(texts)].slice(0, 50);
    });
    console.log('Page text elements:', allText.filter(t => t.length > 2 && t.length < 30));

    // Try to find any element containing "Retrofit" or "Energy" or tool-related text
    const retrofitElement = await page.$('text=Retrofit');
    const energyElement = await page.$('text=Energy');

    if (retrofitElement) {
      console.log('Found Retrofit element!');
      await retrofitElement.click();
      await page.waitForTimeout(2000);
      await page.screenshot({ path: 'retrofit-found.png', fullPage: false });
    } else if (energyElement) {
      console.log('Found Energy element!');
    }

    // Look for sidebar nav items
    const navItems = await page.$$eval('nav a, .sidebar a, [class*="nav"] a, [class*="menu"] li', els =>
      els.map(el => el.textContent?.trim()).filter(Boolean)
    );
    console.log('Navigation items:', navItems.slice(0, 20));

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
})();
