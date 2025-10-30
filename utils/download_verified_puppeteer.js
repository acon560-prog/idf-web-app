const puppeteer = require('puppeteer');
const axios = require('axios');
const fs = require('fs');
const path = require('path');

const manifestPath = path.resolve(__dirname, 'stations_lookup_verified_sample.json');
const cacheDir = path.resolve(__dirname, 'cache');
if (!fs.existsSync(cacheDir)) fs.mkdirSync(cacheDir);

async function downloadCSVFromStation(pageUrl, province, stationId) {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();

  try {
    await page.goto(pageUrl, { waitUntil: 'networkidle2', timeout: 60000 });
    console.log(`🔍 Looking for download link on: ${pageUrl}`);

    // Wait and click the "Download CSV" tab if needed
    await page.waitForSelector('a.btn[href$=".csv"]', { timeout: 15000 });
    const csvUrl = await page.$eval('a.btn[href$=".csv"]', el => el.href);

    const filename = `${province}_${stationId}.csv`;
    const outputPath = path.join(cacheDir, filename);
    console.log(`⬇️  Downloading: ${csvUrl} → ${filename}`);

    const response = await axios.get(csvUrl, { responseType: 'stream' });
    const writer = fs.createWriteStream(outputPath);
    response.data.pipe(writer);

    await new Promise((resolve, reject) => {
      writer.on('finish', resolve);
      writer.on('error', reject);
    });

    console.log(`✅ Saved: ${filename}`);
  } catch (err) {
    console.error(`❌ Failed to download from ${pageUrl}: ${err.message}`);
  } finally {
    await browser.close();
  }
}

(async () => {
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));

  for (const entry of manifest) {
    const { province, stationId, stationUrl } = entry;
    if (!province || !stationId || !stationUrl) {
      console.warn(`⚠️ Skipping invalid entry: ${JSON.stringify(entry)}`);
      continue;
    }

    await downloadCSVFromStation(stationUrl, province, stationId);
  }

  console.log('\n🎉 All downloads complete.');
})();
