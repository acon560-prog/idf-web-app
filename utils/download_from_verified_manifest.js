// File: utils/download_from_verified_manifest.js

const puppeteer = require('puppeteer');
const axios = require('axios');
const fs = require('fs');
const path = require('path');

const MANIFEST_PATH = path.join(__dirname, 'stations_lookup_verified.json');
const OUTPUT_DIR = path.join(__dirname, 'cache');

(async () => {
  if (!fs.existsSync(OUTPUT_DIR)) fs.mkdirSync(OUTPUT_DIR);

  const manifest = JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf-8'));
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();

  for (const station of manifest) {
    const { province, stationId, name } = station;
    const url = `https://climate.weather.gc.ca/climate_normals/results_1991_2020_e.html?searchType=stnProv&lstProvince=${province}&stnID=${stationId}&tgt=1`;

    console.log(`🌐 Visiting: ${name} (${province})`);

    try {
      await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });

      const downloadUrl = await page.$$eval('a', (anchors) => {
        const link = anchors.find(a => a.textContent.includes('CSV'));
        return link ? link.href : null;
      });

      if (!downloadUrl) {
        console.warn(`⚠️ No CSV link found for ${name} (${stationId})`);
        continue;
      }

      const filename = `${province}_${stationId}.csv`;
      const filepath = path.join(OUTPUT_DIR, filename);

      const response = await axios.get(downloadUrl, { responseType: 'arraybuffer' });
      fs.writeFileSync(filepath, response.data);
      console.log(`✅ Saved: ${filename}`);
    } catch (err) {
      console.error(`❌ Failed for ${name}:`, err.message);
    }
  }

  await browser.close();
  console.log('\n🎉 All downloads completed.');
})();
