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

function parseArgs() {
  const args = process.argv.slice(2);
  const options = {};
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === '--seed' && args[i + 1]) {
      options.seed = args[++i];
    } else if (arg === '--output' && args[i + 1]) {
      options.output = args[++i];
    } else if (arg === '--help') {
      console.log('Usage: node enrich_incomplete_master.js [--seed path] [--output path]');
      process.exit(0);
    }
  }
  return options;
}

const { seed, output } = parseArgs();

// Load your master stations (incomplete)
const masterFilePath = seed
  ? path.resolve(process.cwd(), seed)
  : path.join(__dirname, '../utils/stations_lookup_demo_fixed.json');
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
const outputFilePath = output
  ? path.resolve(process.cwd(), output)
  : path.join(__dirname, 'master_stations_enriched.json');
fs.writeFileSync(outputFilePath, JSON.stringify(enriched, null, 2));

console.log(`Enriched master list saved to ${outputFilePath}`);
