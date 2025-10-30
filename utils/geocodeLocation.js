const axios = require('axios');
const OPENCAGE_API_KEY = process.env.OPENCAGE_API_KEY;

async function geocodeLocation(city, region) {
  const query = `${city}, ${region}`;
  const response = await axios.get('https://api.opencagedata.com/geocode/v1/json', {
    params: {
      q: query,
      key: OPENCAGE_API_KEY,
    },
  });

  const data = response.data;
  if (!data.results || data.results.length === 0) {
    throw new Error('No results from geocoding API');
  }

  const { lat, lng } = data.results[0].geometry;
  const countryCode = data.results[0].components['ISO_3166-1_alpha-2'];

  return { lat, lng, countryCode };
}

module.exports = geocodeLocation;
