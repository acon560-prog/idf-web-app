const fs = require('fs');
const path = require('path');
const Fuse = require('fuse.js');

// ---- CONFIGURE THESE PATHS if needed ----
const masterStationsPath = path.join(__dirname, '../utils/stations_lookup_demo_fixed.json');
const aliasMapPath = path.join(__dirname, 'alias_map_cleaned.json');
const incompletePath = path.join(__dirname, '../utils/incomplete_stations_to_review.json');
const unmatchedOutputPath = path.join(__dirname, 'unmatched_stations.json');

// ---- Filtering patterns ----
const excludePatterns = [
  /\b\d{4}(-\d{4})?\b/,  // years or year ranges
  /\bprecip\b/i,
  /\brain\b/i,
  /\btemp\b/i,
  /\bsolar\b/i,
  /\bwind\b/i,
];

function isValidAliasKey(key) {
  for (const pattern of excludePatterns) {
    if (pattern.test(key)) {
      if (key === '2 lb1') return true;
      return false;
    }
  }
  return true;
}

function loadCleanedAliasMap(filePath) {
  if (!fs.existsSync(filePath)) return {};
  const raw = fs.readFileSync(filePath, 'utf8');
  const map = JSON.parse(raw);
  const cleaned = {};
  for (const key in map) {
    if (isValidAliasKey(key)) cleaned[key] = map[key];
  }
  return cleaned;
}

function normalizeName(name) {
  if (!name) return ''; // safely handle undefined, null, or empty
  return name.toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9 ]/g, ' ')
    .replace(/\b(a|the|la|le|des|de|du|d)\b/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

console.log('\nLoading files...');
const masterStations = JSON.parse(fs.readFileSync(masterStationsPath, 'utf8'));
const aliasMap = loadCleanedAliasMap(aliasMapPath);
const incompleteStations = JSON.parse(fs.readFileSync(incompletePath, 'utf8'));

const officialStations = masterStations.map(st => ({
  ...st,
  normalizedName: normalizeName(st.STATION_NAME)
}));

const fuse = new Fuse(officialStations, {
  keys: ['normalizedName'],
  threshold: 0.45
});

// ---- ENRICHMENT LOGIC ----
console.log('Processing enrichment...');
let updatedCount = 0;
let unmatchedStations = [];

incompleteStations.forEach(station => {
  if (!station.stationId || !station.lat || !station.lon) {
    let lookupName = normalizeName(station.name || '');
    // Use alias map if exists
    if (aliasMap[lookupName]) {
      lookupName = normalizeName(aliasMap[lookupName]);
    }
    const results = fuse.search(lookupName);
    if (results.length > 0) {
      const matched = results[0].item;
      station.province = matched.PROV_STATE_TERR_CODE;
      station.stationId = matched.CLIMATE_IDENTIFIER;
      station.lat = matched.LATITUDE / 1e6;
      station.lon = matched.LONGITUDE / 1e6;
      station.officialName = matched.STATION_NAME;
      updatedCount++;
    } else {
      unmatchedStations.push(station);
    }
  }
});

// ---- SAVE RESULTS ----
fs.writeFileSync(incompletePath, JSON.stringify(incompleteStations, null, 2), 'utf8');
fs.writeFileSync(unmatchedOutputPath, JSON.stringify(unmatchedStations, null, 2), 'utf8');
console.log(`Done! Updated ${updatedCount} stations.`);
if (unmatchedStations.length) {
  console.log(`Check unmatched stations in ${unmatchedOutputPath}`);
} else {
  console.log('All stations matched and enriched.');
}
