const fs = require('fs');

const masterPath = '../utils/stations_lookup_demo_fixed.json';
const incompletePath = '../utils/incomplete_stations_to_review.json';

const masterStations = JSON.parse(fs.readFileSync(masterPath, 'utf8'));

const incompleteStations = masterStations.filter(station =>
  station.name && (!station.stationId || !station.lat || !station.lon)
);

fs.writeFileSync(incompletePath, JSON.stringify(incompleteStations, null, 2), 'utf8');

console.log(`Extracted ${incompleteStations.length} incomplete stations for review to ${incompletePath}`);
