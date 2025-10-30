// File: download_verified_puppeteer_fixed.js
// Description: Uses Puppeteer to find real download button and axios to download verified CSVs

const puppeteer = require('puppeteer');
const axios = require('axios');
const fs = require('fs');
const path = require('path');

const manifest = require('./stations_lookup_verified_sample.json');
const OUTPUT_DIR = path.resolve(__dirname, 'cache');

(async () => {
  if (!fs.existsSync(OUTPUT_DIR)) fs.mkdirSync(OUTPUT_DIR);

  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();

  for (const entry of manifest) {
    const { province, stationId, name } = entry;
    const url = `https://climate.weather.gc.ca/climate_normals/results_1991_2020_e.html?searchType=stnProv&lstProvince=${province}&stnID=${stationId}`;
    const outputPath = path.join(OUTPUT_DIR, `${province}_${stationId}.csv`);

    console.log(`🔍 Visiting: ${name} (${province})`);
    try {
      await page.goto(url, { timeout: 30000, waitUntil: 'domcontentloaded' });
      await page.waitForSelector('a[title="Download CSV"]', { timeout: 15000 });

      const downloadUrl = await page.$eval('a[title="Download CSV"]', a => a.href);
      const response = await axios.get(downloadUrl, { responseType: 'arraybuffer' });

      fs.writeFileSync(outputPath, response.data);
      console.log(`✅ Saved: ${outputPath}`);
    } catch (err) {
      console.error(`❌ Failed for ${name} (${stationId}): ${err.message}`);
    }
  }

  await browser.close();
  console.log('\n✅ All downloads attempted.');
})();
