const fs = require('fs');
const path = require('path');

const unmatchedPath = path.join(__dirname, 'unmatched_from_filenames.json');
const aliasMapPath = path.join(__dirname, 'alias_map.json');

// Load unmatched stations (array of objects with stationName field)
let unmatched = [];
try {
  unmatched = JSON.parse(fs.readFileSync(unmatchedPath, 'utf8'));
} catch (err) {
  console.error('Error reading unmatched_from_filenames.json:', err);
  process.exit(1);
}

// Load existing alias map or start new
let aliasMap = {};
try {
  aliasMap = JSON.parse(fs.readFileSync(aliasMapPath, 'utf8'));
} catch {
  console.log('alias_map.json not found; starting empty alias map');
}

// Normalize function to generate keys consistently
function normalizeName(name) {
  return name.toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9 ]/g, '')
    .replace(/\b(a|the|la|le|des|de|du|d)\b/g, '')
    .trim();
}

// Add unmatched station names as new alias keys with empty values
let addedCount = 0;
for (const station of unmatched) {
  const key = normalizeName(station.stationName);
  if (!(key in aliasMap)) {
    aliasMap[key] = "";
    addedCount++;
  }
}

// Save updated alias map
fs.writeFileSync(aliasMapPath, JSON.stringify(aliasMap, null, 2), 'utf8');
console.log(`Added ${addedCount} new entries to alias_map.json`);
