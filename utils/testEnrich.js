require('dotenv').config();
const enrichFromNOAA = require('./enrichFromNOAA');

(async () => {
  try {
    const lat = 40.7128; // Replace with your target
    const lon = -74.0060;
    const unitSystem = 'metric'; // or 'imperial'

    const data = await enrichFromNOAA(unitSystem, lat, lon);
    console.log(JSON.stringify(data, null, 2));
  } catch (err) {
    console.error('Error during enrichment:', err.message);
  }
})();
