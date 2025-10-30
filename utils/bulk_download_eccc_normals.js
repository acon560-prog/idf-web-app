const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const BASE_URL = 'https://climate.weather.gc.ca/climate_normals/index_e.html';
const OUTPUT_DIR = path.resolve(__dirname, 'cache');

(async () => {
  if (!fs.existsSync(OUTPUT_DIR)) fs.mkdirSync(OUTPUT_DIR);

  const browser = await puppeteer.launch({
    headless: false,
    defaultViewport: null,
    args: ['--window-size=1200,800'],
  });

  const page = await browser.newPage();

  // Setup download behavior
  const client = await page.target().createCDPSession();
  await client.send('Page.setDownloadBehavior', {
    behavior: 'allow',
    downloadPath: OUTPUT_DIR,
  });

  console.log('Navigating to Climate Normals page...');
  await page.goto(BASE_URL, { waitUntil: 'networkidle2' });

  const provinces = await page.$$eval('#lstProvince option', opts =>
    opts
      .map(opt => ({ value: opt.value, label: opt.textContent.trim() }))
      .filter(opt => opt.value !== '')
  );

  for (const { value, label } of provinces) {
    console.log(`\n➡️ Province: ${label}`);
    await page.select('#lstProvince', value);
    await Promise.all([
      page.click('#btnSubmitProvince'),
      page.waitForNavigation({ waitUntil: 'networkidle2' })
    ]);

    const stationPageLinks = await page.$$eval('a', links =>
      links
        .filter(a => a.textContent.includes('Normals Data HTML'))
        .map(a => a.href)
    );

    console.log(`🔎 Found ${stationPageLinks.length} stations for ${label}`);

    for (let i = 0; i < stationPageLinks.length; i++) {
      const stationUrl = stationPageLinks[i];
      const stationIdMatch = stationUrl.match(/stnID=(\d+)/);
      const stationId = stationIdMatch ? stationIdMatch[1] : `station_${i}`;

      const newPage = await browser.newPage();
      await newPage._client.send('Page.setDownloadBehavior', {
        behavior: 'allow',
        downloadPath: OUTPUT_DIR,
      });

      try {
        await newPage.goto(stationUrl, { waitUntil: 'networkidle2' });

        // Click the actual CSV download link
        const csvLink = await newPage.$('a:has-text("Download Data (CSV)")');
        if (!csvLink) {
          console.log(`⚠️ CSV link not found for station ${stationId}`);
        } else {
          await csvLink.click();
          console.log(`⬇️ Downloading CSV for station ${stationId}`);
          await newPage.waitForTimeout(3000); // Give time for download
        }
      } catch (err) {
        console.error(`❌ Failed for station ${stationId}:`, err.message);
      } finally {
        await newPage.close();
      }
    }

    // Return to province selector
    await page.goto(BASE_URL, { waitUntil: 'networkidle2' });
  }

  await browser.close();
  console.log('\n✅ All downloads attempted.');
})();
