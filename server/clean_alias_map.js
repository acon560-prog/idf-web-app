const fs = require('fs');
const path = require('path');

// File paths
const aliasMapPath = path.join(__dirname, 'alias_map.json');
const cleanedAliasMapPath = path.join(__dirname, 'alias_map_cleaned.json');

// Patterns to exclude keys containing years or weather terms
const excludePatterns = [
  /\b\d{4}(-\d{4})?\b/,  // years or year ranges
  /\bprecip\b/i,
  /\brain\b/i,
  /\btemp\b/i,
  /\bsolar\b/i,
  /\bwind\b/i,
];

// Function to check if a key should be kept
function isValidAliasKey(key) {
  for (const pattern of excludePatterns) {
    if (pattern.test(key)) {
      // Keep exceptions like "2 lb1"
      if (key === '2 lb1') return true;
      return false;
    }
  }
  return true;
}

// Main filtering function
function filterAliasMap() {
  try {
    const rawData = fs.readFileSync(aliasMapPath, 'utf8');
    const aliasMap = JSON.parse(rawData);

    const cleanedAliasMap = {};
    for (const key in aliasMap) {
      if (isValidAliasKey(key)) {
        cleanedAliasMap[key] = aliasMap[key];
      } else {
        console.log(`Removing key '${key}' from alias map`);
      }
    }

    fs.writeFileSync(cleanedAliasMapPath, JSON.stringify(cleanedAliasMap, null, 2), 'utf8');
    console.log(`Cleaned alias map saved to ${cleanedAliasMapPath}`);
  } catch (error) {
    console.error('Error processing alias map:', error);
  }
}

filterAliasMap();
