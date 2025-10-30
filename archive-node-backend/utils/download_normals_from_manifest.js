
// File: utils/download_normals_from_manifest.js

const fs = require('fs');
const path = require('path');
const https = require('https');

const manifestPath = path.join(__dirname, 'stations_lookup_verified.json');
const outputDir = path.join(__dirname, 'cache');

if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir);
}

const stations = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));

function downloadCsv(station) {
  return new Promise((resolve, reject) => {
    const fileName = `${station.province}_${station.stationId}.csv`;
    const filePath = path.join(outputDir, fileName);

    const file = fs.createWriteStream(filePath);
    https.get(station.normalsCsvUrl, (response) => {
      if (response.statusCode !== 200) {
        fs.unlinkSync(filePath);
        return reject(
          new Error(`Failed to download ${fileName}: ${response.statusCode}`)
        );
      }

      response.pipe(file);
      file.on('finish', () => {
        file.close();
        console.log(`✅ Downloaded: ${fileName}`);
        resolve();
      });
    }).on('error', (err) => {
      fs.unlinkSync(filePath);
      reject(err);
    });
  });
}

(async () => {
  for (const station of stations) {
    try {
      await downloadCsv(station);
    } catch (err) {
      console.error(`❌ Error downloading ${station.stationId}: ${err.message}`);
    }
  }

  console.log('\n✅ All downloads complete.');
})();
