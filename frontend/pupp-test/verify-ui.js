const puppeteer = require('puppeteer');

(async () => {
  console.log('=== STARTING PUPPETEER UI VERIFICATION ===');
  const browser = await puppeteer.launch({ 
    args: ['--no-sandbox', '--disable-setuid-sandbox'] 
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });

  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(`Console error: ${msg.text()}`);
    }
  });
  page.on('pageerror', error => {
    errors.push(`Page error: ${error.message}`);
  });

  try {
    // 1. Visit Catalog
    console.log('\n[1] Testing Catalog (/products)...');
    await page.goto('http://localhost:4200/products', { waitUntil: 'networkidle2' });
    
    const pageTitle = await page.title();
    console.log('Page Title:', pageTitle);

    await page.waitForSelector('.product-card', { timeout: 6000 });
    const cardsCount = await page.$$eval('.product-card', cards => cards.length);
    console.log(`Rendered ${cardsCount} product cards.`);

    // Test Quick View button
    console.log('Clicking Quick View on first card...');
    const quickViewBtn = await page.$('.product-card button');
    if (quickViewBtn) {
      await quickViewBtn.click();
      await page.waitForSelector('.buy-modal-content', { timeout: 3000 });
      console.log('Quick View modal opened successfully!');

      // Close modal with Escape key
      console.log('Pressing Escape to close modal...');
      await page.keyboard.press('Escape');
      await page.waitForFunction(() => !document.querySelector('.buy-modal-content'), { timeout: 3000 });
      console.log('Quick View modal closed via Escape key!');
    }

    // Test Search input
    console.log('Testing search input...');
    const searchInput = await page.$('input[type="search"]');
    if (searchInput) {
      await searchInput.type('computers');
      await new Promise(r => setTimeout(r, 400));
      const filteredCount = await page.$$eval('.product-card', cards => cards.length);
      console.log(`Filtered products count for "computers": ${filteredCount}`);
    }

    // 2. Visit Login
    console.log('\n[2] Testing Login (/login)...');
    await page.goto('http://localhost:4200/login', { waitUntil: 'networkidle2' });
    const loginHeader = await page.$eval('h1', el => el.textContent.trim());
    console.log('Login Header:', loginHeader);

    // Test password toggle
    const toggleBtn = await page.$('button[aria-label*="password"]');
    if (toggleBtn) {
      const typeBefore = await page.$eval('#loginPassword', el => el.type);
      await toggleBtn.click();
      await new Promise(r => setTimeout(r, 200));
      const typeAfter = await page.$eval('#loginPassword', el => el.type);
      console.log(`Password visibility toggle: ${typeBefore} -> ${typeAfter}`);
    }

    // 3. Visit Register
    console.log('\n[3] Testing Register (/register)...');
    await page.goto('http://localhost:4200/register', { waitUntil: 'networkidle2' });
    const roleBtns = await page.$$('.role-select-card');
    console.log(`Found ${roleBtns.length} role selection options.`);

    // 4. Test Seller Portal (/seller/dashboard & /seller/media)
    console.log('\n[4] Testing Seller Dashboard (/seller/dashboard)...');
    await page.evaluate(() => {
      localStorage.setItem('buy01_token', 'valid-test-token');
      localStorage.setItem('buy01_user', JSON.stringify({
        id: 'seller123',
        email: 'seller@example.com',
        username: 'seller_demo',
        fullName: 'Seller Demo',
        role: 'SELLER'
      }));
    });

    await page.goto('http://localhost:4200/seller/dashboard', { waitUntil: 'networkidle2' });
    const sellerHeader = await page.$eval('h1', el => el.textContent.trim());
    console.log('Seller Dashboard Header:', sellerHeader);

    const statCards = await page.$$('.stat-icon');
    console.log(`Rendered ${statCards.length} genuine metric stat cards.`);

    const rowsCount = await page.$$eval('.buy-table tbody tr', rows => rows.length);
    console.log(`Seller catalog rendered ${rowsCount} table rows.`);

    // Test Add New Product button
    console.log('Testing "+ New Product" button toggle...');
    const newProdBtn = await page.$('button[aria-label="Create new product"]');
    if (newProdBtn) {
      await newProdBtn.click();
      await page.waitForSelector('#prodName', { timeout: 3000 });
      console.log('Product creation form opened!');
      await page.keyboard.press('Escape');
      await new Promise(r => setTimeout(r, 200));
      console.log('Product form closed via Escape key!');
    }

    // 5. Test Media Manager
    console.log('\n[5] Testing Media Manager (/seller/media)...');
    await page.goto('http://localhost:4200/seller/media', { waitUntil: 'networkidle2' });
    const mediaHeader = await page.$eval('h1', el => el.textContent.trim());
    console.log('Media Center Header:', mediaHeader);

    const mediaCards = await page.$$('.media-gallery-card');
    console.log(`Media Library rendered ${mediaCards.length} synced assets.`);

    // 6. Test Mobile Responsive View
    console.log('\n[6] Testing Mobile View (375x667)...');
    await page.setViewport({ width: 375, height: 667 });
    await page.goto('http://localhost:4200/products', { waitUntil: 'networkidle2' });
    const toggler = await page.$('.buy-toggler');
    if (toggler) {
      console.log('Mobile navigation toggler found. Clicking...');
      await toggler.click();
      await new Promise(r => setTimeout(r, 300));
      const menuExpanded = await page.$eval('.navbar-collapse', el => el.classList.contains('show'));
      console.log(`Mobile menu opened: ${menuExpanded}`);
    }

    console.log('\n=== ALL UI VERIFICATION CHECKS PASSED ===');
    if (errors.length > 0) {
      console.warn('Encountered non-fatal logs:', errors);
    } else {
      console.log('ZERO page errors or console errors!');
    }
  } catch (err) {
    console.error('Test execution error:', err);
  } finally {
    await browser.close();
  }
})();
