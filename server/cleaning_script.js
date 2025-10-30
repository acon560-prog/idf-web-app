const fs = require('fs');
const path = require('path');

// Utility: validate numeric latitude/longitude
function isValidLatLon(lat, lon) {
  return (
    typeof lat === 'number' &&
    !isNaN(lat) &&
    lat >= -90 && lat <= 90 &&
    typeof lon === 'number' &&
    !isNaN(lon) &&
    lon >= -180 && lon <= 180
  );
}

// Load your stations file
const infile = path.join(__dirname, 'master_stations_enriched_validated.json');
const outfile = path.join(__dirname, 'master_stations_cleaned.json');
const reportfile = path.join(__dirname, 'cleaning_report.json');

const stations = JSON.parse(fs.readFileSync(infile));

const changed = [];

const cleaned = stations.map(station => {
  let origLat = station.lat;
  let origLon = station.lon;
  if (!isValidLatLon(origLat, origLon)) {
    changed.push({
      name: station.name,
      originalLat: origLat,
      originalLon: origLon,
      reason: `Invalid lat/lon, set to null`
    });
    station.lat = null;
    station.lon = null;
  }
  return station;
});

fs.writeFileSync(outfile, JSON.stringify(cleaned, null, 2));
fs.writeFileSync(reportfile, JSON.stringify(changed, null, 2));

console.log(
  `\nWrote cleaned data to: ${outfile}\n` +
  `Stations updated: ${changed.length}\n` +
  `Detailed report: ${reportfile}\n`
);
