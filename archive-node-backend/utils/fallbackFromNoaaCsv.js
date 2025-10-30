const fs = require('fs');
const path = require('path');
const AdmZip = require('adm-zip');
const csvParser = require('csv-parser');

// 🧠 Compute haversine distance between coordinates
function haversineDistance(lat1, lon1, lat2, lon2) {
  const toRad = deg => deg * Math.PI / 180;
  const R = 6371; // Earth radius in km
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat/2)**2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon/2)**2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

// 📍 Find closest station if stationId is not matched
function findClosestStationInRegion(regionName, targetLat, targetLon) {
  const lookupPath = path.join(__dirname, '../data/stations_lookup.json');
  if (!fs.existsSync(lookupPath)) throw new Error('stations_lookup.json not found');

  const stations = JSON.parse(fs.readFileSync(lookupPath));
  const regionalStations = stations.filter(s => s.region === regionName);

  if (regionalStations.length === 0) {
    throw new Error(`No fallback stations found for region: ${regionName}`);
  }

  let minDist = Infinity;
  let closest = null;

  for (const station of regionalStations) {
    const dist = haversineDistance(targetLat, targetLon, station.lat, station.lon);
    if (dist < minDist) {
      minDist = dist;
      closest = station;
    }
  }

  return closest;
}

async function fallbackFromNoaaCsv(regionName, stationId = '', lat = null, lon = null) {
  const regionFile = `${regionName.replace(/\s+/g, '_')}_TP.zip`;
  const zipPath = path.join(__dirname, '../cache/noaa', regionFile);

  if (!fs.existsSync(zipPath)) {
    throw new Error(`❌ Cached NOAA ZIP not found for region: ${regionName}`);
  }

  const zip = new AdmZip(zipPath);
  const zipEntries = zip.getEntries();

  // Try to match stationId
  let targetEntry = stationId
    ? zipEntries.find(entry => entry.entryName.toLowerCase().includes(stationId.toLowerCase()))
    : null;

  // If no match by ID, try by lat/lon and lookup
  if (!targetEntry && lat !== null && lon !== null) {
    const closestStation = findClosestStationInRegion(regionName, lat, lon);
    console.warn(`⚠️ Falling back to nearest station: ${closestStation.name} (${closestStation.file})`);
    targetEntry = zipEntries.find(e => e.entryName.includes(closestStation.file));
  }

  // Still fallback to first .csv if nothing found
  if (!targetEntry && zipEntries.length > 0) {
    console.warn('⚠️ No match found, falling back to first available CSV in ZIP');
    targetEntry = zipEntries.find(e => e.entryName.endsWith('.csv'));
  }

  if (!targetEntry) {
    throw new Error(`❌ No CSV found in cached ZIP for region: ${regionName}`);
  }

  const csvData = targetEntry.getData().toString('utf8');
  const results = await parseIdfCsv(csvData);
  return results;
}

function parseIdfCsv(csvText) {
  return new Promise((resolve, reject) => {
    const curves = {};
    const stream = require('stream');
    const readable = new stream.Readable();
    readable._read = () => {};
    readable.push(csvText);
    readable.push(null);

    readable
      .pipe(csvParser())
      .on('data', (row) => {
        const duration = row['Duration'] || row['duration'] || row['DURATION'];
        for (const key of Object.keys(row)) {
          if (/\d+/.test(key)) {
            const returnPeriod = key.trim();
            if (!curves[returnPeriod]) curves[returnPeriod] = {};
            curves[returnPeriod][duration] = parseFloat(row[key]);
          }
        }
      })
      .on('end', () => {
        console.log('✅ Parsed fallback NOAA CSV successfully');
        resolve(curves);
      })
      .on('error', reject);
  });
}

module.exports = fallbackFromNoaaCsv;
