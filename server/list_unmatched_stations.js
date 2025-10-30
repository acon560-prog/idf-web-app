const fs = require('fs');
const path = require('path');

// Directory containing your txt files (adjust as needed)
const txtDir = path.join(__dirname, '../server/data/QC');

// Load your current stations JSON (adjust path)
const stationsFilePath = path.join(__dirname, '../utils/stations_lookup_demo_fixed.json');

let stations;
try {
  stations = JSON.parse(fs.readFileSync(stationsFilePath, 'utf8'));
} catch (err) {
  console.error(`Failed to load or parse stations file: ${stationsFilePath}`, err);
  process.exit(1); // Exit if stations data is mandatory
}

const knownStations = new Set(stations.map(s => s.name.trim().toLowerCase()));

// Helper: extract station name/id from TXT file content and filename
function extractStationName(fileContent, fileName = '') {
  const lines = fileContent.split(/\r?\n/).map(line => line.trim());

  // Regex to detect station name line: name (letters/spaces), province code (2 letters), station ID (alphanumeric)
  const stationLineRegex = /^([A-Z\s\-']+)\s{2,}([A-Z]{2})\s{2,}([A-Z0-9]+)$/;

  for (const line of lines) {
    const match = line.match(stationLineRegex);
    if (match) {
      return match[1].toLowerCase();
    }
  }

  // If no match in content, fallback to parsing filename
  if (!fileName) {
    console.warn('No filename provided for fallback station name extraction.');
    return '';
  }

  return fileName
    .replace(/^idf_v3-30_\d{4}_\d{2}_\d{2}_\d+_[A-Z]{2}_/, '')
    .replace(/\.txt$/i, '')
    .replace(/_/g, ' ')
    .toLowerCase();
}

function listUnmatchedStations() {
  let txtFiles;
  try {
    txtFiles = fs.readdirSync(txtDir).filter(f => f.toLowerCase().endsWith('.txt'));
  } catch (err) {
    console.error(`Failed to read directory: ${txtDir}`, err);
    return;
  }

  const unmatchedStations = [];

  for (const fileName of txtFiles) {
    const filePath = path.join(txtDir, fileName);
    let fileContent;
    try {
      fileContent = fs.readFileSync(filePath, 'utf8');
    } catch (err) {
      console.error(`Failed to read file: ${filePath}`, err);
      continue; // Skip problematic files but continue processing others
    }

    try {
      const stationName = extractStationName(fileContent, fileName).trim();
      if (!stationName) {
        console.warn(`Could not extract station name for file: ${fileName}`);
        continue;
      }

      if (!knownStations.has(stationName)) {
        unmatchedStations.push({ file: fileName, station: stationName });
      }

    } catch (err) {
      console.error(`Error processing file "${fileName}":`, err);
      // Continue processing rest of files
    }
  }

  if (unmatchedStations.length) {
    const unmatchedFilePath = path.join(__dirname, '../server/data/unmatchedstations.json');
    try {
      fs.writeFileSync(unmatchedFilePath, JSON.stringify(unmatchedStations, null, 2), 'utf8');
      console.log(`Unmatched stations saved to ${unmatchedFilePath}`);
    } catch (err) {
      console.error('Error writing unmatched stations JSON:', err);
    }
  } else {
    console.log('All stations matched the known stations list.');
  }
}

// Run the listing
listUnmatchedStations();
