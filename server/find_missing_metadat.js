const fs = require('fs');
const path = require('path');
const fetch = require('node-fetch');

const masterPath = path.join(__dirname, '../utils/stations_lookup_demo_fixed.json');

const normalize = name => name.trim().toLowerCase();

// Load master list JSON
function loadJSON(filePath) {
  try {
    const rawData = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(rawData);
  } catch (err) {
    console.error(`Failed to load JSON: ${filePath}`, err);
    process.exit(1);
  }
}

// Save JSON back to file
function saveJSON(filePath, data) {
  try {
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf8');
    console.log(`Saved updated master to ${filePath}`);
  } catch (err) {
    console.error('Error saving JSON:', err);
  }
}

// Query Environment Canada Climate Stations API by station name
async function getStationMetadataByName(name) {
  const url = `https://api.weather.gc.ca/collections/climate-stations/items?lang=en&f=json&search=${encodeURIComponent(name)}`;
  try {
    const res = await fetch(url);
    if (!res.ok) {
      console.error(`API request failed (status ${res.status}) for: ${name}`);
      return null;
    }
    const data = await res.json();
    if (data.features && data.features.length > 0) {
      // Here we return the first matching station's properties
      return data.features[0].properties;
    }
    return null;
  } catch (err) {
    console.error(`Fetch error for "${name}":`, err);
    return null;
  }
}

// Main update function
async function enrichPartialStations() {
  const masterStations = loadJSON(masterPath);
  let updatedCount = 0;
  let skippedCount = 0;

  // Find partial stations (only have 'name' property)
  const partialStations = masterStations.filter(s => Object.keys(s).length === 1 && s.name);

  console.log(`Found ${partialStations.length} partial stations to enrich.`);

  // For each partial station, fetch and update metadata
  for (const station of partialStations) {
    console.log(`Looking up metadata for: "${station.name}"`);
    const metadata = await getStationMetadataByName(station.name);

    if (metadata) {
      // Merge relevant fields into the station object
      station.province = metadata.province || station.province;
      station.stationId = metadata.stationIdentifier || station.stationId;
      station.lat = metadata.latitude || station.lat;
      station.lon = metadata.longitude || station.lon;
      station.normalsCsvUrl = metadata.normalsCsvUrl || station.normalsCsvUrl;

      updatedCount++;
      console.log(`  Updated metadata for: "${station.name}"`);
    } else {
      skippedCount++;
      console.log(`  No metadata found for: "${station.name}"`);
    }

    // Simple delay for rate limiting (e.g., 500ms)
    await new Promise(resolve => setTimeout(resolve, 500));
  }

  console.log(`\nMetadata enrichment complete.`);
  console.log(`  Stations updated: ${updatedCount}`);
  console.log(`  Stations skipped (no metadata): ${skippedCount}`);

  saveJSON(masterPath, masterStations);
}

// Run the enrichment
enrichPartialStations().catch(err => {
  console.error('Error during enrichment:', err);
});
