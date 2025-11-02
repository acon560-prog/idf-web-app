const fs = require('fs');
const path = require('path');
const Fuse = require('fuse.js');

function normalizeName(name) {
  if (!name) return '';
  return name.toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9 ]/g, ' ')
    .replace(/\b(a|the|la|le|des|de|du|d)\b/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function haversineDistance(lat1, lon1, lat2, lon2) {
  const toRad = angle => (angle * Math.PI) / 180;
  const R = 6371; // Earth radius in kilometers
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function isValidLatLon(lat, lon) {
  return (
    typeof lat === 'number' &&
    typeof lon === 'number' &&
    lat >= -90 && lat <= 90 &&
    lon >= -180 && lon <= 180
  );
}

function parseArgs() {
  const args = process.argv.slice(2);
  const options = {};
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === '--master' && args[i + 1]) {
      options.master = args[++i];
    } else if (arg === '--output' && args[i + 1]) {
      options.output = args[++i];
    } else if (arg === '--log' && args[i + 1]) {
      options.log = args[++i];
    } else if (arg === '--help') {
      console.log('Usage: node enrich_stations_fuzzy_validated.js [--master path] [--output path] [--log path]');
      process.exit(0);
    }
  }
  return options;
}

const { master, output, log } = parseArgs();

const masterFilePath = master
  ? path.resolve(process.cwd(), master)
  : path.join(__dirname, 'master_stations_enriched.json');
const masterStations = JSON.parse(fs.readFileSync(masterFilePath, 'utf8'));

const ecccFilePath = path.join(__dirname, 'eccc_climate_stations_full.json');
const ecccStations = JSON.parse(fs.readFileSync(ecccFilePath, 'utf8'));

// Normalize names in both datasets
masterStations.forEach(s => {
  s.normalizedName = normalizeName(s.name || s.stationName || '');
});
ecccStations.forEach(s => {
  if (!s.normalizedName) {
    s.normalizedName = normalizeName(s.name || '');
  }
});

const fuse = new Fuse(ecccStations, {
  keys: ['normalizedName'],
  threshold: 0.3 // Adjust threshold if needed
});

const matchLogs = [];

const enriched = masterStations.map(station => {
  const normName = station.normalizedName;
  let ecccMatch = ecccStations.find(s => s.normalizedName === normName);

  if (!ecccMatch) {
    const results = fuse.search(normName);
    if (results.length > 0) {
      const candidate = results[0].item;

      if (
        isValidLatLon(station.lat, station.lon) &&
        isValidLatLon(candidate.lat, candidate.lon)
      ) {
        const dist = haversineDistance(station.lat, station.lon, candidate.lat, candidate.lon);
        if (dist < 2) { // Stricter geographic threshold
          ecccMatch = candidate;
          matchLogs.push({
            stationName: station.name,
            matchedName: candidate.name,
            distanceKm: dist.toFixed(2),
            note: 'Accepted fuzzy match with geo proximity'
          });
        } else {
          matchLogs.push({
            stationName: station.name,
            matchedName: candidate.name,
            distanceKm: dist.toFixed(2),
            note: 'Rejected due to distance > 2 km'
          });
        }
      } else {
        ecccMatch = candidate;
        matchLogs.push({
          stationName: station.name,
          matchedName: candidate.name,
          distanceKm: null,
          note: 'Accepted fuzzy match (no geo info)'
        });
      }
    } else {
      matchLogs.push({
        stationName: station.name,
        matchedName: null,
        distanceKm: null,
        note: 'No match found'
      });
    }
  } else {
    matchLogs.push({
      stationName: station.name,
      matchedName: ecccMatch.name,
      distanceKm: station.lat && station.lon && ecccMatch.lat && ecccMatch.lon ?
                  haversineDistance(station.lat, station.lon, ecccMatch.lat, ecccMatch.lon).toFixed(2) :
                  null,
      note: 'Exact normalized name match'
    });
  }

  if (ecccMatch) {
  // Overwrite provinceCode with official and remove old 'province' field
  if (station.provinceCode && ecccMatch.provinceCode && station.provinceCode !== ecccMatch.provinceCode) {
    matchLogs.push({
      stationName: station.name,
      note: `Conflicting provinceCode (master: ${station.provinceCode}, official: ${ecccMatch.provinceCode}), using official one`,
      latMaster: station.lat,
      lonMaster: station.lon,
      latOfficial: ecccMatch.lat,
      lonOfficial: ecccMatch.lon
    });
  }
  station.provinceCode = ecccMatch.provinceCode;
  delete station.province;  // Remove conflicting legacy field

  // Merge other fields
  station.stationId = station.stationId || ecccMatch.stationId;
  station.name = station.name || ecccMatch.name;
  station.operatorEng = station.operatorEng || ecccMatch.operatorEng;
  station.lat = isValidLatLon(station.lat, station.lon) ? station.lat : ecccMatch.lat;
  station.lon = isValidLatLon(station.lat, station.lon) ? station.lon : ecccMatch.lon;
}

  return station;
});

// Save enriched master list
const outputFilePath = output
  ? path.resolve(process.cwd(), output)
  : path.join(__dirname, 'master_stations_enriched_validated.json');
fs.writeFileSync(outputFilePath, JSON.stringify(enriched, null, 2));

// Save matching logs for review
const logFilePath = log
  ? path.resolve(process.cwd(), log)
  : path.join(__dirname, 'enrichment_match_logs.json');
fs.writeFileSync(logFilePath, JSON.stringify(matchLogs, null, 2));

console.log(`Enrichment complete. Results saved to ${outputFilePath}`);
console.log(`Match logs saved to ${logFilePath}`);
