const https = require('https');
const fs = require('fs');
const path = require('path');

const apiBaseURL = 'https://api.weather.gc.ca/collections/climate-stations/items';
const outputFilePath = path.join(__dirname, 'eccc_climate_stations_full.json');

async function fetchJSON(url) {
  return new Promise((resolve, reject) => {
    https.get(url, res => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(JSON.parse(data)));
    }).on('error', reject);
  });
}

async function fetchAllStations() {
  let stations = [];
  let offset = 0;
  const limit = 100; // max items per page

  while (true) {
    const url = `${apiBaseURL}?lang=en&limit=${limit}&offset=${offset}`;
    console.log(`Fetching stations offset=${offset}...`);
    let response = await fetchJSON(url);

    if (!response.features || response.features.length === 0) break;
    console.log('Sample feature:', JSON.stringify(response.features[0], null, 2));
    stations = stations.concat(response.features);

    if (response.features.length < limit) {
      // Last page reached if fewer items than limit
      break;
    }

    offset += response.features.length;
  }

  return stations;
}

function normalizeName(name) {
  if (!name) return '';
  return name.toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9 ]/g, ' ')
    .replace(/\b(a|the|la|le|des|de|du|d)\b/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

async function main() {
  try {
    let features = await fetchAllStations();
    console.log(`Fetched ${features.length} stations in total.`);

    // Prepare simplified list with normalized names for easy matching
    const simplifiedStations = features.map(station => {
    const p = station.properties || {};
    const coords = station.geometry?.coordinates || [null, null]; // [lon, lat]

    return {
        stationId: p.CLIMATE_IDENTIFIER || String(p.STN_ID) || '',
        name: p.STATION_NAME || '',
        provinceCode: p.PROV_STATE_TERR_CODE || '',
        provinceNameEng: p.ENG_PROV_NAME || '',
        provinceNameFre: p.FRE_PROV_NAME || '',
        status: p.STATION_TYPE || '',
        operatorEng: p.ENG_STN_OPERATOR_NAME || '',
        operatorFre: p.FRE_STN_OPERATOR_NAME || '',
        wmoId: p.WMO_IDENTIFIER || null,
        elevation: p.ELEVATION || null,
        lat: coords[1],
        lon: coords[0],
        firstDate: p.FIRST_DATE || null,
        lastDate: p.LAST_DATE || null,
        normalizedName: normalizeName(p.STATION_NAME || '')
    };
});




    fs.writeFileSync(outputFilePath, JSON.stringify(simplifiedStations, null, 2));
    console.log(`All station data saved to ${outputFilePath}`);
  } catch (error) {
    console.error('Error fetching station data:', error);
  }
}

main();
