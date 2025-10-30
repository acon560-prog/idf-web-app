// File: download_verified_debug_dump.js
const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer");
const stations = require("./stations_lookup_verified_sample.json"); // Make sure this is correct

(async () => {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  for (const station of stations) {
    const { name, province, stationId } = station;
    const url = `https://climate.weather.gc.ca/climate_normals/results_1991_2020_e.html?searchType=stnProv&lstProvince=${province}&stnID=${stationId}`;

    console.log(`\n🔎 Visiting: ${name} (${province})`);
    console.log(`🌐 URL: ${url}`);

    try {
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });

      // Save HTML to inspect the structure
      const html = await page.content();
      const dumpPath = path.join(__dirname, `debug_html/${stationId}_${province}.html`);
      fs.mkdirSync(path.dirname(dumpPath), { recursive: true });
      fs.writeFileSync(dumpPath, html);

      // Try common selectors
      const selectorsToTry = [
        'a[title="Download CSV"]',
        'a[href$=".csv"]',
        'a.btn[href*="csv"]',
        'a[href*="observations"]',
      ];

      let linkFound = false;

      for (const selector of selectorsToTry) {
        try {
          await page.waitForSelector(selector, { timeout: 5000 });
          const downloadLink = await page.$eval(selector, el => el.href);

          if (downloadLink) {
            console.log(`✅ Found download link using selector '${selector}':\n   ${downloadLink}`);
            linkFound = true;
            break;
          }
        } catch (e) {
          console.log(`❌ Selector '${selector}' failed.`);
        }
      }

      if (!linkFound) {
        console.log(`❌ No working selector found for ${name}`);
      }
    } catch (err) {
      console.error(`❌ Error visiting ${name}:`, err.message);
    }
  }

  await browser.close();
  console.log("\n✅ Debug run complete. Check the debug_html/ folder.");
})();
