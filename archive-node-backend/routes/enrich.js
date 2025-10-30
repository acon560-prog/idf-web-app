const express = require('express');
const router = express.Router();
const geocodeLocation = require('../utils/geocode');
const enrichFromECCC = require('../utils/enrichFromECCC');
const enrichFromNOAA = require('../utils/enrichFromNOAA');
const fallbackFromTxt = require('../utils/fallbackFromTxt');
const findClosestTxtStation = require('../utils/findClosestTxtStation');

// ✅ Safe import for enrichFromMeteostat
let enrichFromMeteostat;
try {
  enrichFromMeteostat = require('../utils/enrichFromMeteostat');
} catch (err) {
  console.warn('⚠️ enrichFromMeteostat.js not found, using fallback.');
  enrichFromMeteostat = async () => ({
    idf: {},
    fallback: true,
    message: 'Meteostat enrichment unavailable'
  });
}


router.post('/', async (req, res) => {
  const { city, province, unitSystem = 'metric' } = req.body;
  console.log('📍 Enrich request:', { city, province, unitSystem });

  let lat, lng, countryCode;

  try {
    // Step 1: Geocode
    const geo = await geocodeLocation(city, province);
    lat = geo.lat;
    lng = geo.lng;
    countryCode = geo.countryCode;

    console.log(`🌍 Geolocation -> lat: ${lat}, lng: ${lng}, country: ${countryCode}`);

    // Step 2: Primary enrichment
    let enrichment;
    if (countryCode === 'CA') {
      enrichment = await enrichFromECCC(city, province, unitSystem, lat, lng);
    } else if (countryCode === 'US') {
      console.log('🇺🇸 Calling enrichFromNOAA...');
      enrichment = await enrichFromNOAA(unitSystem, lat, lng, req.app.locals.db);
    } else {
      console.log('🌎 Calling enrichFromMeteostat (fallback for other countries)...');
      enrichment = await enrichFromMeteostat(city, province, unitSystem, lat, lng);
    }

    console.log('✅ Enrichment successful:', enrichment);
    return res.json(enrichment);

  } catch (err) {
    const msg = err?.message || '';
    console.error('❌ Enrichment error:', msg);

    // Step 3: TXT fallback for Canadian stations
    if (
      msg.includes('GeoMet WFS') ||
      msg.includes('No IDF station') ||
      msg.includes('station_id')
    ) {
      console.log('⚠️ Falling back to TXT IDF data...');

      try {
        const closest = findClosestTxtStation(lat, lng);
        const safeStationId = closest.name.replace(/\s+/g, '_');

        console.log('📍 Closest TXT station for fallback:', closest.name);
        console.log('🔹 SafeStationId for file lookup:', safeStationId);
        console.log('🔹 Coordinates for fallback:', { lat, lng, unitSystem });

        const fallbackData = fallbackFromTxt(safeStationId, unitSystem);
        console.log('✅ TXT fallback data parsed successfully');
        return res.json(fallbackData);
      } catch (fallbackErr) {
        console.error('❌ TXT fallback also failed:', fallbackErr.message);
        return res.status(500).json({ error: 'Enrichment and fallback failed' });
      }
    }

    // General error response
    return res.status(500).json({ error: 'Enrichment failed', message: msg });
  }
});

module.exports = router;
