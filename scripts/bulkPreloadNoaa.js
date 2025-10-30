const mongoose = require('mongoose');
const enrichFromNOAA = require('../utils/enrichFromNOAA');
const dbConnect = require('../dbConnect'); // Your MongoDB connection
const cities = [
  { city: "New York", lat: 40.7128, lon: -74.0060 },
  { city: "Los Angeles", lat: 34.0522, lon: -118.2437 },
  { city: "Chicago", lat: 41.8781, lon: -87.6298 },
  { city: "Miami", lat: 25.7617, lon: -80.1918 }
];

(async () => {
  await dbConnect();

  for (const city of cities) {
    try {
      const data = await enrichFromNOAA({
        lat: city.lat,
        lon: city.lon,
        unitSystem: 'imperial'
      });
      console.log(`✅ Cached: ${city.city}`);
    } catch (err) {
      console.error(`❌ Failed for ${city.city}:`, err.message);
    }
  }

  process.exit();
})();
