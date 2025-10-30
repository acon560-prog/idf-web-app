const fs = require('fs');
const path = require('path');
const Fuse = require('fuse.js');

// Normalize function (consistent with previous usage)
function normalizeName(name) {
  if (!name) return '';
  return name.toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9 ]/g, ' ')
    .replace(/\b(a|the|la|le|des|de|du|d)\b/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

// Haversine formula to calculate distance in km between two lat/lon points
function haversineDistance(lat1, lon1, lat2, lon2) {
  const toRad = angle => (angle * Math.PI) / 180;
  const R = 6371; // Earth radius in km
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// Load master stations (your incomplete list)
const masterFilePath = path.join(__dirname, 'master_stations_enriched.json');
const masterStations = JSON.parse(fs.readFileSync(masterFilePath, 'utf8'));

// Load official ECCC stations (enriched)
const ecccFilePath = path.join(__dirname, 'eccc_climate_stations_full.json');
const ecccStations = JSON.parse(fs.readFileSync(ecccFilePath, 'utf8'));

// Normalize names in both datasets for matching convenience and add normalizedName if missing
masterStations.forEach(s => {
  s.normalizedName = normalizeName(s.name || s.stationName || '');
});
ecccStations.forEach(s => {
  if (!s.normalizedName) {
    s.normalizedName = normalizeName(s.name || '');
  }
});

// Prepare Fuse.js fuzzy search on official stations by normalizedName
const fuse = new Fuse(ecccStations, {
  keys: ['normalizedName'],
  threshold: 0.3 // Adjust threshold for sensitivity
});

// Enrich master stations
const enriched = masterStations.map(station => {
  const normName = station.normalizedName;

  // Try exact normalized name match first
  let ecccMatch = ecccStations.find(s => s.normalizedName === normName);

  // If no exact match, do fuzzy search
  if (!ecccMatch) {
    const results = fuse.search(normName);
    if (results.length > 0) {
      const candidate = results[0].item;

      // Geographic distance check if coordinates available
      if (
        station.lat !== undefined && station.lon !== undefined &&
        candidate.lat !== undefined && candidate.lon !== undefined
      ) {
        const dist = haversineDistance(station.lat, station.lon, candidate.lat, candidate.lon);
        if (dist < 5) { // Accept if within 5 km
          ecccMatch = candidate;
        }
      } else {
        // Accept fuzzy match without geo check if coordinates missing
        ecccMatch = candidate;
      }
    }
  }

  // Merge data if matched found
  if (ecccMatch) {
    station.stationId = station.stationId || ecccMatch.stationId;
    station.name = station.name || ecccMatch.name;
    station.provinceCode = ecccMatch.provinceCode || station.provinceCode;
    station.operatorEng = station.operatorEng || ecccMatch.operatorEng;
    station.lat = station.lat || ecccMatch.lat;
    station.lon = station.lon || ecccMatch.lon;
  }

  return station;
});

// Save enriched master list
const outputFilePath = path.join(__dirname, 'master_stations_enriched_fuzzy.json');
fs.writeFileSync(outputFilePath, JSON.stringify(enriched, null, 2));

console.log(`Enriched master stations saved to ${outputFilePath}`);
