// File: scripts/download_noaa_csvs.js
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const cities = [
  { name: 'New York, NY', lat: 40.7128, lon: -74.0060 },
  { name: 'Los Angeles, CA', lat: 34.0522, lon: -118.2437 },
  { name: 'Chicago, IL', lat: 41.8781, lon: -87.6298 },
  { name: 'Montreal, QC', lat: 45.5017, lon: -73.5673 }, // Even though NOAA doesn't cover Canada, can fall back or skip
  // Add more as needed
];

const outputDir = path.resolve(__dirname, '../data/noaa_cached_curves');
if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

(async () => {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  const lookup = [];

  for (const city of cities) {
    console.log(`Fetching IDF data for ${city.name}`);

    const url = `https://hdsc.nws.noaa.gov/hdsc/pfds/pfds_map_cont.html?bkmrk=${city.lat},${city.lon}`;
    await page.goto(url, { waitUntil: 'domcontentloaded' });

    // Wait for iframe to load
    await page.waitForSelector('#frm', { timeout: 10000 });

    const frameHandle = await page.$('#frm');
    const frame = await frameHandle.contentFrame();

    await frame.waitForSelector('input[value="Download CSV"]', { timeout: 10000 });
    await frame.click('input[value="Download CSV"]');

    await page.waitForTimeout(5000); // wait for download to complete

    const downloadsPath = path.resolve(process.env.HOME || process.env.USERPROFILE, 'Downloads');
    const files = fs.readdirSync(downloadsPath).filter(f => f.endsWith('.csv'));
    const newest = files.map(f => ({ name: f, time: fs.statSync(path.join(downloadsPath, f)).mtime }))
                        .sort((a, b) => b.time - a.time)[0];

    if (newest) {
      const newName = `station_${city.name.replace(/[^a-z0-9]/gi, '_')}.csv`;
      fs.renameSync(path.join(downloadsPath, newest.name), path.join(outputDir, newName));
      lookup.push({ name: city.name, lat: city.lat, lon: city.lon, file: newName });
      console.log(`Saved CSV as ${newName}`);
    }
  }

  await browser.close();

  fs.writeFileSync(path.resolve(__dirname, '../data/stations_lookup.json'), JSON.stringify(lookup, null, 2));
  console.log("Done. All files downloaded and mapped.");
})();
