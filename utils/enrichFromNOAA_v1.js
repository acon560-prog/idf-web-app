const axios = require('axios');

async function enrichFromNOAA({ lat, lon, unitSystem = 'metric' }) {
  const base = 'https://hdsc.nws.noaa.gov/pfds/point';
  const dur = ['5min','10min','15min','30min','60min','2hr','6hr','12hr','24hr'];
  const rps = ['2','5','10','25','50','100'];

  const params = new URLSearchParams({
    lat: lat.toString(),
    lon: lon.toString(),
    units: unitSystem === 'metric' ? 'metric' : 'eng',
    format: 'json'
  });

  const url = `${base}?${params.toString()}`;
  const res = await axios.get(url);
  if (!res.data || !res.data.data) {
    throw new Error('No IDF data from NOAA PFDS');
  }

  const raw = res.data.data; // structure based on PFDS v
  const output = {};

  dur.forEach(d => {
    if (raw[d]) {
      output[d] = {};
      rps.forEach(r => {
        output[d][`${r}yr`] = +raw[d][r];
      });
    }
  });

  return {
    source: 'NOAA Atlas 14',
    rainfall_intensity: output,
    lat,
    lon
  };
}
