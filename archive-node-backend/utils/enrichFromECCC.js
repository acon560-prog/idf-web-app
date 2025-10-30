const axios = require('axios');
const fs = require('fs');
const path = require('path');

async function enrichFromECCC({ city, province, unitSystem = 'metric', lat, lon }) {
  // Step 1: Query GeoMet WFS for nearest IDF_PT station (within 20 km)
  const wfsUrl = `https://geo.weather.gc.ca/geomet?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=IDF_PT&OUTPUTFORMAT=application/json&CQL_FILTER=DWITHIN(geometry,POINT(${lon} ${lat}),1.0,units=degrees)`;

  const stationRes = await axios.get(wfsUrl);
  console.log('📡 Raw GeoMet WFS stationRes.data:', JSON.stringify(stationRes.data, null, 2));

  if (!stationRes.data || !Array.isArray(stationRes.data.features)) {
    throw new Error('Invalid or missing station data from GeoMet WFS');
  }

  const stations = stationRes.data.features;

  if (!stations.length) {
    throw new Error('No IDF station found nearby');
  }

  // ✅ Added validation for station_id
  const stationId = stations[0].properties.station_id;
  if (!stationId || typeof stationId !== 'string') {
    throw new Error('Invalid or missing station data from GeoMet WFS');
  }

  const cacheDir = path.join(__dirname, '../cache/idf');
  const cacheFile = path.join(cacheDir, `${stationId}.json`);

  if (!fs.existsSync(cacheDir)) {
    fs.mkdirSync(cacheDir, { recursive: true });
  }

  let idfData;
  if (fs.existsSync(cacheFile)) {
    console.log(`📦 Using cached IDF data for ${stationId}`);
    idfData = JSON.parse(fs.readFileSync(cacheFile, 'utf-8'));
  } else {
    const idfUrl = `https://dd.weather.gc.ca/hydrometric/idf/${stationId}/idf_data.json`;
    const idfRes = await axios.get(idfUrl);
    idfData = idfRes.data;
    fs.writeFileSync(cacheFile, JSON.stringify(idfData, null, 2));
    console.log(`💾 Cached IDF data for ${stationId}`);
  }

  const durationsWanted = ['5min', '10min', '15min', '30min', '1h', '6h', '12h', '24h'];
  const returnPeriods = ['2', '5', '10', '25', '50', '100'];
  const intensityResult = {};

  durationsWanted.forEach((duration) => {
    const durationData = idfData[duration];
    if (!durationData) return;

    intensityResult[duration] = {};
    returnPeriods.forEach((rp) => {
      const mmPerHour = durationData[rp];
      intensityResult[duration][`${rp}yr`] = unitSystem === 'imperial'
        ? +(mmPerHour / 25.4).toFixed(2)
        : +mmPerHour.toFixed(1);
    });
  });

  const enrichment = {
    city,
    province,
    station_id: stationId,
    station_name: stations[0].properties.station_name,
    rainfall_intensity: intensityResult,
    frost_depth: unitSystem === 'imperial' ? +(1.5 * 3.281).toFixed(1) : 1.5,
    snow_load_zone: province === 'Quebec' ? '2.2 kPa' : '1.8 kPa',
    setback_min: unitSystem === 'imperial' ? +(1.2 * 3.281).toFixed(1) : 1.2
  };

  return enrichment;
}

module.exports = enrichFromECCC;

