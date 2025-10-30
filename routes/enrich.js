const express = require('express');
const router = express.Router();
const geocodeLocation = require('../utils/geocodeLocation');
const enrichFromECCC = require('../utils/enrichFromECCC');
const enrichFromNOAA = require('../utils/enrichFromNOAA');
const fallbackFromTxt = require('../utils/fallbackFromTxt');
const findClosestTxtStation = require('../utils/findClosestTxtStation');

router.post('/', async (req, res) => {
  const { city, province, unitSystem = 'metric' } = req.body;
  console.log('📥 Enrich request:', { city, province, unitSystem });

  let lat, lng, countryCode;

  try {
    // 🔹 Step 1: Geocode
    const geo = await geocodeLocation(city, province);
    lat = geo.lat;
    lng = geo.lng;
    countryCode = geo.countryCode;

    console.log(`🌍 Geolocation → lat: ${lat}, lng: ${lng}, country: ${countryCode}`);

    // 🔹 Step 2: Primary enrichment
    let enrichment;
    if (countryCode === 'CA') {
      enrichment = await enrichFromECCC(city, province, unitSystem, lat, lng);
    } else if (countryCode === 'US') {
      console.log("👉 Calling enrichFromNOAA with DB:", !!req.app.locals.db);
      enrichment = await enrichFromNOAA(unitSystem, lat, lng, req.app.locals.db);
    } else {
      // Optional: fallback to another global source
      enrichment = await enrichFromMeteostat(city, province, unitSystem, lat, lng);
    }

    return res.status(200).json({ success: true, data: enrichment });

  } catch (err) {
    const msg = err?.message || '';
    console.error('❌ Enrichment error:', msg);

    // 🔹 Step 3: TXT fallback for Canadian stations
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

        const fallback = await fallbackFromTxt({
          stationId: closest.name
        });

        // ✅ Send fallback result
        return res.status(200).json({ success: true, data: fallback });

      } catch (txtErr) {
        console.warn('❌ TXT fallback also failed:', txtErr.message);
      }
    }

    // 🔹 Step 4: Send failure
    res.status(500).json({
      success: false,
      message: 'Failed to enrich site',
      error: msg
    });
  }
});

module.exports = router;
