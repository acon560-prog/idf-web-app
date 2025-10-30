const fs = require('fs');
const path = require('path');

// Normalize function you used before for consistency
function normalizeName(name) {
  if (!name) return '';
  return name.toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9 ]/g, ' ')
    .replace(/\b(a|the|la|le|des|de|du|d)\b/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

// Load your master stations (incomplete)
const masterFilePath = path.join(__dirname, '../utils/stations_lookup_demo_fixed.json');
const masterStations = JSON.parse(fs.readFileSync(masterFilePath, 'utf8'));

// Load official ECCC stations (enriched)
const ecccFilePath = path.join(__dirname, 'eccc_climate_stations_full.json');
const ecccStations = JSON.parse(fs.readFileSync(ecccFilePath, 'utf8'));

// Build a quick lookup by normalized name for ECCC data
const ecccLookup = {};
for (const s of ecccStations) {
  ecccLookup[s.normalizedName] = s;
}

// Enrich master stations
const enriched = masterStations.map(station => {
  const normName = normalizeName(station.name || station.stationName || '');
  const ecccMatch = ecccLookup[normName];

  if (ecccMatch) {
    // Copy missing fields if they are empty/undefined in master
    station.stationId = station.stationId || ecccMatch.stationId;
    station.name = station.name || ecccMatch.name;
    station.provinceCode = station.provinceCode || ecccMatch.provinceCode;
    station.operatorEng = station.operatorEng || ecccMatch.operatorEng;
    station.lat = station.lat || ecccMatch.lat;
    station.lon = station.lon || ecccMatch.lon;
    // Add any other fields you want to enrich similarly
  }
  return station;
});

// Save enriched master list to new file
const outputFilePath = path.join(__dirname, 'master_stations_enriched.json');
fs.writeFileSync(outputFilePath, JSON.stringify(enriched, null, 2));

console.log(`Enriched master list saved to ${outputFilePath}`);
