const axios = require('axios');

async function geocodeLocation(location) {
  const apiKey = process.env.OPENCAGE_API_KEY;
  const url = `https://api.opencagedata.com/geocode/v1/json?q=${encodeURIComponent(location)}&key=${apiKey}&limit=1`;

  try {
    const response = await axios.get(url);
    const result = response.data.results[0];
    if (result && result.geometry) {
      return {
        lat: result.geometry.lat,
        lon: result.geometry.lng
      };
    }
    throw new Error('No geocoding result found.');
  } catch (err) {
    console.error('❌ Geocoding error:', err.message);
    throw err;
  }
}

module.exports = geocodeLocation;
