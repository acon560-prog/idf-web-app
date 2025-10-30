const fs = require('fs');
const path = require('path');
const Fuse = require('fuse.js');

const masterPath = path.join(__dirname, '../utils/stations_lookup_demo_fixed.json');
const unmatchedPath = path.join(__dirname, '../server/data/unmatchedstations.json');

const normalize = name => name.trim().toLowerCase();

function loadJSON(filePath) {
  try {
    const rawData = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(rawData);
  } catch (err) {
    console.error(`Failed to read or parse JSON from ${filePath}:`, err);
    process.exit(1);
  }
}

function saveJSON(filePath, data) {
  try {
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf8');
    console.log(`Successfully saved updated JSON to ${filePath}`);
  } catch (err) {
    console.error(`Failed to write JSON to ${filePath}:`, err);
  }
}

function updateMasterStationLookup() {
  const masterStations = loadJSON(masterPath);
  const unmatchedStations = loadJSON(unmatchedPath);

  const fuse = new Fuse(masterStations, {
    keys: ['name'],
    threshold: 0.35,
    includeScore: true
  });

  const updatedStations = [...masterStations];

  let correctionsCount = 0;
  let additionsCount = 0;

  unmatchedStations.forEach(({ station, file }) => {
    const normStation = normalize(station);
    console.log(`Processing unmatched station: "${station}" from file "${file}"`);

    const results = fuse.search(normStation);

    if (results.length > 0) {
      const score = results.score;
       console.log(`  Best match: "${results[0].item.name}" with score: ${typeof score === 'number' ? score.toFixed(3) : 'N/A'}`);

      if (results.score <= 0.35) {
        const bestMatch = results.item.name;
        if (bestMatch.toLowerCase() !== normStation) {
          correctionsCount++;
          console.log(`  Correction applied: "${station}" → "${bestMatch}"`);
        } else {
          console.log('  Names match closely; no correction needed.');
        }
      } else {
        additionsCount++;
        if (!updatedStations.some(s => normalize(s.name) === normStation)) {
          updatedStations.push({ name: station });
          console.log(`  No close match found; added as new station.`);
        } else {
          console.log('  Station already exists in updated list.');
        }
      }
    } else {
      additionsCount++;
      if (!updatedStations.some(s => normalize(s.name) === normStation)) {
        updatedStations.push({ name: station });
        console.log('  No matches found; added as new station.');
      } else {
        console.log('  Station already exists in updated list.');
      }
    }
  });

  if (correctionsCount === 0 && additionsCount === 0) {
    console.log('No changes needed. Master station lookup is up to date.');
  } else {
    console.log(`\nSummary:\n  Corrections made: ${correctionsCount}\n  New stations added: ${additionsCount}`);
    saveJSON(masterPath, updatedStations);
  }
}

updateMasterStationLookup();
