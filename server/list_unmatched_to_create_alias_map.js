const fs = require('fs');
const path = require('path');

const dataFolder = './data';
const incompletePath = '../utils/incomplete_stations_to_review.json';

// Load incomplete stations from JSON
const incompleteStations = JSON.parse(fs.readFileSync(incompletePath, 'utf8'));
const incompleteNamesSet = new Set(incompleteStations.map(s => s.name.toLowerCase()));

function normalizeName(name) {
  return name.toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')  // remove accents
    .replace(/[^a-z0-9 ]/g, ' ')                       // replace non-alphanum with space
    .replace(/\b(a|the|la|le|des|de|du|d)\b/g, '')    // remove common articles
    .replace(/\s+/g, ' ')                              // collapse multiple spaces
    .trim();
}

function extractStationName(filename) {
  // Remove directory and extension
  const basename = path.basename(filename, '.txt');

  // The pattern is: idf_v3-30_2022_10_31_705_QC_7056480_RIMOUSKI
  // Split by underscore
  const parts = basename.split('_');

  // Find the part where province code appears (e.g., QC)
  const provinceIndex = parts.findIndex(p => /^[A-Z]{2}$/.test(p));
  if (provinceIndex < 0) {
    // If not found, fallback to last part
    return '';
  }

  // Station name is all parts after the province code and numeric ID
  // The numeric ID always comes after province at provinceIndex + 1
  const stationParts = parts.slice(provinceIndex + 2);

  // Join the station parts with spaces (some may be multiple words split by underscore)
  const rawStationName = stationParts.join(' ');

  return normalizeName(rawStationName);
}


fs.readdir(dataFolder, (err, files) => {
  if (err) {
    console.error('Error reading data directory:', err);
    return;
  }

  let unmatched = [];

  files.forEach(file => {
    if (file.endsWith('.txt')) {
      const stationName = extractStationName(file);
      if (!incompleteNamesSet.has(stationName)) {
        unmatched.push({ file, stationName });
      }
    }
  });

  if (unmatched.length === 0) {
    console.log('All stations from filenames found in incomplete stations list.');
  } else {
    console.log('Stations found in filenames but NOT in incomplete stations list:');
    unmatched.forEach(u => console.log(`- ${u.stationName} (file: ${u.file})`));

    // Save unmatched to a JSON file for creating alias map entries
    fs.writeFileSync('unmatched_from_filenames.json', JSON.stringify(unmatched, null, 2), 'utf8');
    console.log(`Unmatched stations saved to unmatched_from_filenames.json`);
  }
});
