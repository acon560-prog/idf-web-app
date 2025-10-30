const fs = require('fs');
const path = require('path');

const masterStationsPath = path.join(__dirname, '../utils/stations_lookup_demo_fixed.json');
const masterStations = JSON.parse(fs.readFileSync(masterStationsPath, 'utf8'));

const incompleteMetadataStations = masterStations.filter(st =>
  !st.stationId || !st.lat || !st.lon || !st.officialName
);

console.log(`Stations missing metadata: ${incompleteMetadataStations.length}`);
incompleteMetadataStations.forEach(st => {
  console.log(st.name || st.lookupName);
});
