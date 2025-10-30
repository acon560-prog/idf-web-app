const fs = require('fs');
const Fuse = require('fuse.js');

const masterPath = '../utils/stations_lookup_demo_fixed.json';
const officialPath = './all_official_stations.json';

// Simple name normalization function
function normalizeName(name) {
  return name.toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')  // remove accents
    .replace(/[^a-z0-9 ]/g, '')                       // remove punctuation
    .replace(/\b(a|the|la|le|des|de|du|d)\b/g, '')   // remove common articles
    .trim();
}

// Alias mapping: add known aliases here (partial station name -> official name)
const aliasMap = {
  'kuujjuaq a': 'Kuujjuaq',
  'matagami a': 'Matagami',
  'roberval a': 'Roberval',
  // add more as you discover them
};

// Load data
const masterStations = JSON.parse(fs.readFileSync(masterPath, 'utf8'));
const officialStationsRaw = JSON.parse(fs.readFileSync(officialPath, 'utf8'));
const officialStations = officialStationsRaw.features.map(f => {
  const p = f.properties;
  return { ...p, normalizedName: normalizeName(p.STATION_NAME) };
});

// Preprocess master stations: add normalizedName and apply aliases
masterStations.forEach(station => {
  if (station.name) {
    const lowerName = normalizeName(station.name);
    if (aliasMap[lowerName]) {
      station.lookupName = aliasMap[lowerName]; // use official alias for search
    } else {
      station.lookupName = station.name;
    }
    station.normalizedName = normalizeName(station.lookupName);
  }
});

// Setup Fuse.js for fuzzy search on normalized official names
const fuse = new Fuse(officialStations, {
  keys: ['normalizedName'],
  threshold: 0.45
});

const unmatchedStations = [];
let updatedCount = 0;

masterStations.forEach(station => {
  if (station.name && (!station.stationId || !station.lat || !station.lon)) {
    const results = fuse.search(station.normalizedName);
    if (results.length > 0) {
      const meta = results[0].item;
      station.province = meta.PROV_STATE_TERR_CODE;
      station.stationId = meta.CLIMATE_IDENTIFIER;
      station.lat = meta.LATITUDE / 1e6;
      station.lon = meta.LONGITUDE / 1e6;
      station.officialName = meta.STATION_NAME;
      updatedCount++;
      console.log(`Enriched "${station.name}" with official "${meta.STATION_NAME}"`);
    } else {
      unmatchedStations.push(station);
      console.log(`No match for "${station.name}"`);
    }
  }
});

console.log(`\nEnrichment done. ${updatedCount} stations updated, ${unmatchedStations.length} not matched.`);

// Save updated master list
fs.writeFileSync(masterPath, JSON.stringify(masterStations, null, 2), 'utf8');
console.log(`Master list saved to ${masterPath}`);

// Save unmatched stations for manual review
if (unmatchedStations.length > 0) {
  const unmatchedPath = './unmatched_stations.json';
  fs.writeFileSync(unmatchedPath, JSON.stringify(unmatchedStations, null, 2), 'utf8');
  console.log(`Unmatched stations saved to ${unmatchedPath}`);
}
