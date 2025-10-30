const axios = require('axios');
const unzipper = require('unzipper');
const csv = require('csv-parser');
const fs = require('fs');
const path = require('path');

// Map bounding boxes for each Atlas 14 region (expanded)
const regions = [
  {
    name: 'Colorado',
    bounds: { minLat: 36.9, maxLat: 41.0, minLon: -109.1, maxLon: -102.0 },
    url: 'https://hdsc.nws.noaa.gov/pub/data/atlas14/volume8/CSV/CO_TP.zip'
  },
  {
    name: 'Illinois',
    bounds: { minLat: 36.9, maxLat: 42.5, minLon: -91.5, maxLon: -86.0 },
    //url: 'https://hdsc.nws.noaa.gov/pub/data/atlas14/volume9/CSV/IL_TP.zip'
    url: 'https://hdsc.nws.noaa.gov/pub/data/atlas14/volume9/IL_TP.zip'
  },
  {
    name: 'Midwest (Generic)',
    bounds: { minLat: 36.0, maxLat: 49.0, minLon: -105.0, maxLon: -80.0 },
    url: 'https://hdsc.nws.noaa.gov/pub/data/atlas14/volume8/CSV/MW_TP.zip'
  }
];

function getRegionForCoordinates(lat, lon) {
  console.log(`📍 Looking for NOAA region for lat: ${lat}, lon: ${lon}`);

  for (const r of regions) {
    if (
      lat >= r.bounds.minLat && lat <= r.bounds.maxLat &&
      lon >= r.bounds.minLon && lon <= r.bounds.maxLon
    ) {
      console.log(`✅ Matched NOAA region: ${r.name}`);
      return r;
    }
  }

  console.warn(`❌ No match for lat: ${lat}, lon: ${lon}`);
  console.warn(`🔍 Tried bounds:`);
  for (const r of regions) {
    console.warn(
      ` - ${r.name}: lat[${r.bounds.minLat}, ${r.bounds.maxLat}], lon[${r.bounds.minLon}, ${r.bounds.maxLon}]`
    );
  }

  return null;
}

async function fetchNoaaCsv( unitSystem = 'metric', lat, lon, region) {
  console.log(`🔍 Looking for NOAA region for lat: ${lat}, lon: ${lon}, unit: ${unitSystem}, region: ${region}`);
  if (!region) throw new Error('No NOAA region matches coordinates');

  const zipUrl = region.url;
  const zipPath = path.join(__dirname, 'cache', `${region.name}.zip`);
  const extractDir = path.join(__dirname, 'cache', region.name);

  // Create cache directory if missing
  fs.mkdirSync(path.join(__dirname, 'cache'), { recursive: true });

  // Download ZIP if not already cached
  if (!fs.existsSync(zipPath)) {
    const response = await axios({ url: zipUrl, method: 'GET', responseType: 'stream' });
    const writer = fs.createWriteStream(zipPath);
    response.data.pipe(writer);
    await new Promise(resolve => writer.on('finish', resolve));
  }

  // Extract ZIP if needed
  if (!fs.existsSync(extractDir)) {
    await fs.createReadStream(zipPath).pipe(unzipper.Extract({ path: extractDir })).promise();
  }

  // Find precipitation CSV (simplified)
  const csvFile = fs.readdirSync(extractDir).find(f => f.toLowerCase().includes('precip') && f.endsWith('.csv'));
  if (!csvFile) throw new Error('No precipitation CSV found');

  const csvPath = path.join(extractDir, csvFile);

  // Parse the CSV
  const result = {};
  const returnPeriods = ['2', '5', '10', '25', '50', '100'];

  await new Promise((resolve, reject) => {
    fs.createReadStream(csvPath)
      .pipe(csv())
      .on('data', row => {
        const duration = row['Duration']?.trim();
        if (!duration) return;

        result[duration] = {};
        returnPeriods.forEach(rp => {
          let value = parseFloat(row[`${rp}-yr`] || row[`${rp}yr`] || row[rp]);
          if (isNaN(value)) return;
          result[duration][`${rp}yr`] = unitSystem === 'imperial' ? value : +(value * 25.4).toFixed(1);
        });
      })
      .on('end', resolve)
      .on('error', reject);
  });

  return {
    source: 'NOAA Atlas 14',
    region: region.name,
    rainfall_intensity: result,
  };
}

module.exports = fetchNoaaCsv;
