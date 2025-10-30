const dbPromise = require('../db');
const { getRegionForCoordinates } = require('./matchRegion');
const fetchNoaaCsv = require('./fetchNoaaCsv');
const fetchFromNOAACDO = require('./fetchFromNOAACDO');
const fallbackFromNoaaCsv = require('./fallbackFromNoaaCsv');

async function getNearestStation(lat, lon) {
  const extent = `${lat - 0.1},${lon - 0.1},${lat + 0.1},${lon + 0.1}`;
  try {
    const response = await fetchFromNOAACDO('/stations', {
      extent,
      datasetid: 'GHCND',
      sortfield: 'distance',
      limit: 1
  });
  return response.results?.[0] || null;
  } catch (error) {
    console.warn('⚠️ NOAA API failed, using fallbackFromNoaaCsv');
    const fallback = await fallbackFromNoaaCsv(lat, lon);
    return fallback?.station || null;
  }
}

async function getPrecipData(stationId, startDate, endDate) {
  const response = await fetchFromNOAACDO('/data', {
    datasetid: 'GHCND',
    stationid: stationId,
    startdate: startDate,
    enddate: endDate,
    units: 'metric',
    limit: 1000,
    datatypeid: 'PRCP'
  });
  return response.results || [];
}

async function enrichFromNOAA(unitSystem, lat, lon) {
  const roundedLat = +lat.toFixed(3);
  const roundedLon = +lon.toFixed(3);
  const db = await dbPromise;
  const NoaaCache = db.collection('noaa_cache');

  const cached = await NoaaCache.findOne({ roundedLat, roundedLon });
  if (cached) {
    console.log('⚡ Using cached NOAA data');
    return cached.data;
  }

  // 🧠 Dynamic region lookup
  const regionMatch = getRegionForCoordinates(lat, lon);
  if (!regionMatch) {
    console.error('🛑 Enrichment error: No NOAA region matches coordinates');
    throw new Error('No NOAA region matches coordinates');
  }

  const region = regionMatch;
  console.log(`🌎 NOAA region selected: ${region.name}`);
  // Fetch nearby NOAA stations (CDO API)
  const nearbyStations = await fetchFromNOAACDO(lat, lon);
  console.log('📡 Nearby NOAA stations:', nearbyStations.map(s => s.name || s.id).join(', '));


  // 🌧️ Fetch station and precipitation data from NOAA CDO API
  const station = await getNearestStation(lat, lon);
  if (!station) throw new Error('No station found near coordinates');

  const today = new Date();
  const oneMonthAgo = new Date(today);
  oneMonthAgo.setMonth(today.getMonth() - 1);

  const start = oneMonthAgo.toISOString().split('T')[0];
  const end = today.toISOString().split('T')[0];

  const rainfallData = await getPrecipData(station.id, start, end);

  const fetchedData = await fetchNoaaCsv(unitSystem, lat, lon, region);

  const enriched = {
    station: {
      id: station.id,
      name: station.name,
      location: station.location
    },
    rainfallData,
    idfData: fetchedData
  };

  await NoaaCache.insertOne({
    lat,
    lon,
    roundedLat,
    roundedLon,
    data: enriched
  });

  return enriched;
}

module.exports = enrichFromNOAA;
