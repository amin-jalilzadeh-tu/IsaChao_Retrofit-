const { chromium } = require('playwright');

const issues = [];
const screenshots = [];

function logIssue(category, severity, description, element = null) {
  issues.push({ category, severity, description, element, timestamp: Date.now() });
  console.log(`[${severity.toUpperCase()}] ${category}: ${description}`);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });
  page.on('pageerror', err => consoleErrors.push(err.message));

  try {
    console.log('=== COMPREHENSIVE RETROFIT TOOL AUDIT ===\n');

    // Load page
    console.log('Loading application...');
    await page.goto('http://localhost:4200', { timeout: 60000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    // Close intro modal
    const closeBtn = await page.locator('button:has-text("Sluiten")');
    if (await closeBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await closeBtn.click();
      await page.waitForTimeout(1000);
    }

    // Open Retrofit tool
    console.log('\n--- Opening Retrofit Tool ---');
    await page.mouse.click(16, 122);
    await page.waitForTimeout(3000);
    await page.waitForFunction(() => document.body.innerText.includes('Online'), { timeout: 15000 });

    await page.screenshot({ path: 'audit-01-initial.png' });
    screenshots.push('audit-01-initial.png');

    // ============================================
    // 1. TEST NAVIGATION TREE
    // ============================================
    console.log('\n=== 1. TESTING NAVIGATION TREE ===');

    const navItems = ['Optimization Path', 'Time Horizon', 'Design Variables', 'Scenarios', 'Run Analysis'];
    for (const item of navItems) {
      const navBtn = await page.locator(`button:has-text("${item}")`);
      if (await navBtn.count() > 0) {
        const isVisible = await navBtn.first().isVisible().catch(() => false);
        console.log(`  Nav item "${item}": ${isVisible ? 'OK' : 'NOT VISIBLE'}`);
        if (!isVisible) {
          logIssue('Navigation', 'medium', `Navigation item "${item}" not visible`);
        }
      } else {
        logIssue('Navigation', 'high', `Navigation item "${item}" not found`);
      }
    }

    // ============================================
    // 2. TEST OPTIMIZATION PATH OPTIONS
    // ============================================
    console.log('\n=== 2. TESTING OPTIMIZATION PATH ===');

    // Test User-Driven (should be default)
    const userDrivenRadio = await page.locator('text=User-Driven');
    const constraintRadio = await page.locator('text=Constraint-Based');

    if (await userDrivenRadio.count() > 0) {
      console.log('  User-Driven option: FOUND');
    } else {
      logIssue('Optimization Path', 'high', 'User-Driven option not found');
    }

    if (await constraintRadio.count() > 0) {
      console.log('  Constraint-Based option: FOUND');
    } else {
      logIssue('Optimization Path', 'high', 'Constraint-Based option not found');
    }

    // ============================================
    // 3. TEST SCENARIO TABS (A, B, C)
    // ============================================
    console.log('\n=== 3. TESTING SCENARIO TABS ===');

    for (const tab of ['A', 'B', 'C']) {
      const tabBtn = await page.locator(`button:has-text("${tab}")`).first();
      if (await tabBtn.isVisible().catch(() => false)) {
        await page.evaluate((t) => {
          const btns = document.querySelectorAll('button');
          const btn = Array.from(btns).find(b => b.textContent?.trim() === t);
          if (btn) btn.click();
        }, tab);
        await page.waitForTimeout(500);
        console.log(`  Scenario ${tab}: clicked`);
      }
    }

    // ============================================
    // 4. TEST TIME HORIZON OPTIONS
    // ============================================
    console.log('\n=== 4. TESTING TIME HORIZON ===');

    for (const year of ['2020', '2050', '2100']) {
      const yearBtn = await page.locator(`button:has-text("${year}")`);
      if (await yearBtn.count() > 0) {
        await page.evaluate((y) => {
          const btns = document.querySelectorAll('button');
          const btn = Array.from(btns).find(b => b.textContent?.trim() === y);
          if (btn) btn.click();
        }, year);
        await page.waitForTimeout(300);
        console.log(`  Time horizon ${year}: clicked`);
      } else {
        logIssue('Time Horizon', 'medium', `Time horizon ${year} button not found`);
      }
    }

    // ============================================
    // 5. TEST PRESET BUTTONS
    // ============================================
    console.log('\n=== 5. TESTING PRESETS ===');

    const presets = ['Baseline', 'Basic Retrofit', 'Standard Retrofit', 'Deep Retrofit', 'Passive House'];
    for (const preset of presets) {
      const presetBtn = await page.locator(`button:has-text("${preset}")`);
      if (await presetBtn.count() > 0) {
        console.log(`  Preset "${preset}": FOUND`);
      } else {
        logIssue('Presets', 'low', `Preset "${preset}" not found`);
      }
    }

    // ============================================
    // 6. RUN PREDICTIONS AND CHECK RESULTS
    // ============================================
    console.log('\n=== 6. RUNNING PREDICTIONS ===');

    await page.evaluate(() => {
      const btns = document.querySelectorAll('button');
      const runBtn = Array.from(btns).find(b => b.textContent?.includes('Run Predictions'));
      if (runBtn) runBtn.click();
    });

    await page.waitForTimeout(8000);
    await page.screenshot({ path: 'audit-02-after-predictions.png' });
    screenshots.push('audit-02-after-predictions.png');

    // Check if results appeared
    const pageText = await page.evaluate(() => document.body.innerText);
    if (pageText.includes('No Results Yet')) {
      logIssue('Predictions', 'critical', 'Predictions did not run - still showing "No Results Yet"');
    } else {
      console.log('  Predictions completed successfully');
    }

    // ============================================
    // 7. TEST RESULT TABS
    // ============================================
    console.log('\n=== 7. TESTING RESULT TABS ===');

    const resultTabs = ['Table', '2D Chart', '3D Chart', 'Parallel', 'MCDM'];
    for (const tab of resultTabs) {
      const tabBtn = await page.locator(`button:has-text("${tab}")`);
      if (await tabBtn.count() > 0) {
        await page.evaluate((t) => {
          const btns = document.querySelectorAll('button');
          const btn = Array.from(btns).find(b => b.textContent?.trim() === t || b.textContent?.includes(t));
          if (btn) btn.click();
        }, tab);
        await page.waitForTimeout(1000);

        const filename = `audit-03-tab-${tab.toLowerCase().replace(' ', '-')}.png`;
        await page.screenshot({ path: filename });
        screenshots.push(filename);
        console.log(`  Tab "${tab}": tested, screenshot saved`);

        // Check for errors in tab content
        const tabContent = await page.evaluate(() => document.body.innerText);
        if (tabContent.includes('Error') || tabContent.includes('undefined') || tabContent.includes('null')) {
          logIssue('Result Tabs', 'medium', `Tab "${tab}" may have rendering issues`);
        }
      } else {
        logIssue('Result Tabs', 'high', `Result tab "${tab}" not found`);
      }
    }

    // ============================================
    // 8. TEST CONSTRAINT-BASED PATH
    // ============================================
    console.log('\n=== 8. TESTING CONSTRAINT-BASED PATH ===');

    await page.evaluate(() => {
      const labels = document.querySelectorAll('label, div, span');
      const constraintLabel = Array.from(labels).find(l => l.textContent?.includes('Constraint-Based'));
      if (constraintLabel) constraintLabel.click();
    });
    await page.waitForTimeout(1000);

    await page.screenshot({ path: 'audit-04-constraint-based.png' });
    screenshots.push('audit-04-constraint-based.png');

    // Check for constraint bounds section
    const hasConstraintBounds = await page.evaluate(() =>
      document.body.innerText.includes('Bounds') || document.body.innerText.includes('bounds')
    );
    if (!hasConstraintBounds) {
      logIssue('Constraint Path', 'high', 'Constraint bounds section not visible when Constraint-Based is selected');
    }

    // Check for MCDM weights section
    const hasMCDMWeights = await page.evaluate(() =>
      document.body.innerText.includes('Weight') || document.body.innerText.includes('MCDM')
    );
    if (!hasMCDMWeights) {
      logIssue('Constraint Path', 'medium', 'MCDM weights section may not be visible');
    }

    // ============================================
    // 9. UI/UX AUDIT
    // ============================================
    console.log('\n=== 9. UI/UX AUDIT ===');

    // Check for overlapping elements (the map legend issue we found)
    const hasOverlap = await page.evaluate(() => {
      const legend = document.querySelector('[class*="map-legend"]');
      const sidebar = document.querySelector('[class*="sidebar"]');
      if (legend && sidebar) {
        const legendRect = legend.getBoundingClientRect();
        const sidebarRect = sidebar.getBoundingClientRect();
        return legendRect.left < sidebarRect.right && legendRect.right > sidebarRect.left;
      }
      return false;
    });
    if (hasOverlap) {
      logIssue('UI/UX', 'high', 'Map legend overlaps with sidebar - causes click interception');
    }

    // Check for scroll issues
    const needsScroll = await page.evaluate(() => {
      const sidebar = document.querySelector('[class*="sidebar-content"]');
      if (sidebar) {
        return sidebar.scrollHeight > sidebar.clientHeight;
      }
      return false;
    });
    if (needsScroll) {
      console.log('  Sidebar requires scrolling - check if all controls are accessible');
    }

    // Check button sizes
    const smallButtons = await page.evaluate(() => {
      const buttons = document.querySelectorAll('button');
      let small = 0;
      buttons.forEach(b => {
        const rect = b.getBoundingClientRect();
        if (rect.width < 32 || rect.height < 32) small++;
      });
      return small;
    });
    if (smallButtons > 0) {
      logIssue('UI/UX', 'low', `${smallButtons} buttons may be too small for touch targets (<32px)`);
    }

    // Check color contrast (basic check)
    const lowContrast = await page.evaluate(() => {
      const elements = document.querySelectorAll('span, label, p');
      let issues = 0;
      elements.forEach(el => {
        const style = window.getComputedStyle(el);
        const color = style.color;
        if (color.includes('rgb(200') || color.includes('rgb(180') || color.includes('#ccc')) {
          issues++;
        }
      });
      return issues;
    });
    if (lowContrast > 5) {
      logIssue('UI/UX', 'medium', `Potential low contrast text elements: ${lowContrast}`);
    }

    // ============================================
    // 10. CHECK CONSOLE ERRORS
    // ============================================
    console.log('\n=== 10. CONSOLE ERRORS ===');

    if (consoleErrors.length > 0) {
      console.log(`  Found ${consoleErrors.length} console errors:`);
      consoleErrors.slice(0, 10).forEach((err, i) => {
        console.log(`    ${i + 1}. ${err.substring(0, 100)}`);
        logIssue('Console', 'medium', err.substring(0, 200));
      });
    } else {
      console.log('  No JavaScript errors detected');
    }

    // ============================================
    // FINAL REPORT
    // ============================================
    console.log('\n\n========================================');
    console.log('         AUDIT SUMMARY REPORT');
    console.log('========================================\n');

    const critical = issues.filter(i => i.severity === 'critical');
    const high = issues.filter(i => i.severity === 'high');
    const medium = issues.filter(i => i.severity === 'medium');
    const low = issues.filter(i => i.severity === 'low');

    console.log(`CRITICAL Issues: ${critical.length}`);
    console.log(`HIGH Issues: ${high.length}`);
    console.log(`MEDIUM Issues: ${medium.length}`);
    console.log(`LOW Issues: ${low.length}`);
    console.log(`\nTotal Issues: ${issues.length}`);

    console.log('\n--- All Issues ---');
    issues.forEach((issue, i) => {
      console.log(`${i + 1}. [${issue.severity.toUpperCase()}] ${issue.category}: ${issue.description}`);
    });

    console.log('\n--- Screenshots Saved ---');
    screenshots.forEach(s => console.log(`  - ${s}`));

  } catch (error) {
    console.error('Audit error:', error.message);
  } finally {
    await browser.close();
  }
})();
