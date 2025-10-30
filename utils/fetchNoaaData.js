// fetchNoaaData.js (enhanced version)
const axios = require('axios');
const csv = require('csv-parser');
const { parse } = require('path');
const { Readable } = require('stream');

// NOAA Region URLs
const regionUrls = {
  northeast: 'https://hdsc.nws.noaa.gov/pub/data/atlas14/csvs/NE_CSV',
  southeast: 'https://hdsc.nws.noaa.gov/pub/data/atlas14/csvs/SE_CSV',
  midwest: 'https://hdsc.nws.noaa.gov/pub/data/atlas14/csvs/MW_CSV',
  california: 'https://hdsc.nws.noaa.gov/pub/data/atlas14/csvs/CA_CSV',
  northwest: 'https://hdsc.nws.noaa.gov/pub/data/atlas14/csvs/NW_CSV',
};

function parseCsv(csvData) {
  return new Promise((resolve, reject) => {
    const results = [];
    Readable.from(csvData).pipe(csv())
      .on('data', (data) => results.push(data))
      .on('end', () => resolve(results))
      .on('error', (err) => reject(err));
  });
}

async function fetchNoaaData(unitSystem, lat, lon, region = 'northeast') {
  const url = `${regionUrls[region]}/point_data.csv`; // adjust if using different file per city
  console.log(`📥 Fetching NOAA CSV for region: ${region}`);

  try {
    const res = await axios.get(url);
    const rawData = res.data;
    const parsed = await parseCsv(rawData);

    // Simplify & return intensity data per duration/return period
    const durations = ['5-min', '10-min', '15-min', '30-min', '1-hr', '6-hr', '12-hr', '24-hr'];
    const returnPeriods = ['2', '5', '10', '25', '50', '100'];
    const rainfall_intensity = {};

    for (const duration of durations) {
      const found = parsed.find(row => row['Duration'] === duration);
      if (!found) continue;
      rainfall_intensity[duration] = {};
      for (const rp of returnPeriods) {
        let mmhr = parseFloat(found[`${rp}-yr`] || 0);
        rainfall_intensity[duration][`${rp}yr`] = unitSystem === 'imperial' ? +(mmhr / 25.4).toFixed(2) : +mmhr.toFixed(1);
      }
    }

    return {
      source: url,
      region,
      rainfall_intensity,
      frost_depth: unitSystem === 'imperial' ? 60 : 1.5,
      snow_load_zone: 'n/a',
      setback_min: unitSystem === 'imperial' ? 4 : 1.2
    };

  } catch (err) {
    console.error('❌ NOAA CSV download failed:', err.message);
    throw new Error('NOAA data download or parse error');
  }
}

module.exports = fetchNoaaData;
