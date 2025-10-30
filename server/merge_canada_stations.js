const fs = require('fs');
const path = require('path');

// Load files - adjust paths if needed
const ecccFilePath = path.join(__dirname, 'eccc_climate_stations_full.json');
const masterFilePath = path.join(__dirname, 'master_stations_cleaned.json');
const outputFilePath = path.join(__dirname, 'canada_stations_merged.json');
const logFilePath = path.join(__dirname, 'merge_conflicts_log.json');

// Utility: safe normalization function (same as before)
function normalizeName(name) {
  if (!name) return '';
  return name.toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9 ]/g, ' ')
    .replace(/\b(a|the|la|le|des|de|du|d)\b/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

// Read input JSON files
const ecccStations = JSON.parse(fs.readFileSync(ecccFilePath, 'utf8'));
const masterStations = JSON.parse(fs.readFileSync(masterFilePath, 'utf8'));

// Create lookup by stationId and normalizedName from your master list
const masterById = {};
const masterByName = {};
masterStations.forEach(s => {
  if (s.stationId) masterById[s.stationId] = s;
  const norm = s.normalizedName || normalizeName(s.name || '');
  masterByName[norm] = s;
});

const conflictLogs = [];

const merged = ecccStations.map(ecccStation => {
  const { stationId, name, provinceCode, lat, lon, operatorEng } = ecccStation;
  let masterStation = null;

  // Try to find the master record by stationId or normalizedName
  if (stationId && masterById[stationId]) {
    masterStation = masterById[stationId];
  } else {
    const normName = normalizeName(name);
    masterStation = masterByName[normName];
  }

  if (masterStation) {
    // Merge fields carefully
    // Log any conflicts, e.g. differing province codes
    if (masterStation.provinceCode && masterStation.provinceCode !== provinceCode) {
      conflictLogs.push({
        stationId,
        name,
        field: 'provinceCode',
        masterValue: masterStation.provinceCode,
        officialValue: provinceCode,
        note: 'Using official provinceCode'
      });
    }

    // Construct merged record, prioritizing official data for critical fields
    const mergedRecord = {
      ...masterStation,             // preserve all master custom fields
      stationId: stationId || masterStation.stationId,
      name: name || masterStation.name,
      provinceCode: provinceCode || masterStation.provinceCode,
      lat: lat || masterStation.lat,
      lon: lon || masterStation.lon,
      operatorEng: operatorEng || masterStation.operatorEng,
    };

    return mergedRecord;
  } else {
    // No match found in master, return official record as is
    return ecccStation;
  }
});

// Write outputs
fs.writeFileSync(outputFilePath, JSON.stringify(merged, null, 2), 'utf8');
fs.writeFileSync(logFilePath, JSON.stringify(conflictLogs, null, 2), 'utf8');

console.log(`Merged station file saved to: ${outputFilePath}`);
console.log(`Conflict logs saved to: ${logFilePath}`);
console.log(`Merged total stations: ${merged.length}`);
