const axios = require('axios');

async function fetchFromNOAACDO(lat, lon) {
  const token = process.env.NOAA_API_TOKEN;
  if (!token) throw new Error('❌ NOAA_API_TOKEN is missing in environment variables');

  const latNum = parseFloat(lat);
  const lonNum = parseFloat(lon);

  const bbox = [
    (latNum - 0.2).toFixed(3),
    (lonNum - 0.2).toFixed(3),
    (latNum + 0.2).toFixed(3),
    (lonNum + 0.2).toFixed(3)
  ].join(',');

  let attempts = 0;
  const maxRetries = 3;

  while (attempts < maxRetries) {
    try {
      const response = await axios.get('https://www.ncei.noaa.gov/cdo-web/api/v2/stations', {
        params: {
          datasetid: 'GHCND',
          extent: bbox,
          startdate: '2020-01-01',
          enddate: '2020-12-31',
          limit: 5
        },
        headers: { token }
      });

      const stations = response.data.results || [];
      console.log(`✅ Found ${stations.length} NOAA stations near [${latNum}, ${lonNum}]`);
      return stations;
    } catch (error) {
      if (error.response?.status === 503) {
        console.warn(`⚠️ NOAA API 503 — retrying (${attempts + 1}/${maxRetries})...`);
        attempts++;
        await new Promise(resolve => setTimeout(resolve, 3000));
      } else {
        console.error('❌ Error fetching from NOAA CDO /stations:', error.response?.status, error.response?.data);
        throw new Error(`Request failed with status code ${error.response?.status || 'unknown'}`);
      }
    }
  }

  throw new Error('❌ NOAA API failed after multiple retries (503)');
}

module.exports = fetchFromNOAACDO;
