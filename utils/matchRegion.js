// server/utils/matchRegion.js

const regions = [
  {
    name: 'Colorado',
    bounds: { minLat: 36.9, maxLat: 41.0, minLon: -109.1, maxLon: -102.0 },
    url: 'https://hdsc.nws.noaa.gov/pub/data/atlas14/volume8/CSV/CO_TP.zip'
  },
  {
    name: 'Illinois',
    bounds: { minLat: 36.9, maxLat: 42.5, minLon: -91.5, maxLon: -86.5 },
    url: 'https://hdsc.nws.noaa.gov/pub/data/atlas14/volume9/CSV/IL_TP.zip'
  },
  {
    name: 'Midwest (Generic)',
    bounds: { minLat: 36.0, maxLat: 49.0, minLon: -105.0, maxLon: -80.0 },
    url: 'https://hdsc.nws.noaa.gov/pub/data/atlas14/volume8/CSV/MW_TP.zip'
  },
  {
    name: 'Northeast',
    bounds: { minLat: 38.0, maxLat: 47.5, minLon: -80.0, maxLon: -66.5 },
    url: 'https://hdsc.nws.noaa.gov/pub/data/atlas14/volume10/CSV/NE_TP.zip'
  },
  {
    name: 'Southeast',
    bounds: { minLat: 24.0, maxLat: 38.0, minLon: -90.0, maxLon: -75.0 },
    url: 'https://hdsc.nws.noaa.gov/pub/data/atlas14/volume11/CSV/SE_TP.zip'
  },
  {
    name: 'West Coast',
    bounds: { minLat: 32.0, maxLat: 49.0, minLon: -125.0, maxLon: -115.0 },
    url: 'https://hdsc.nws.noaa.gov/pub/data/atlas14/volume6/CSV/CA_TP.zip'
  },
  {
    name: 'Texas',
    bounds: { minLat: 25.8, maxLat: 36.5, minLon: -106.7, maxLon: -93.5 },
    url: 'https://hdsc.nws.noaa.gov/pub/data/atlas14/volume11/CSV/TX_TP.zip'
  }
];


function getRegionForCoordinates(lat, lon) {
  for (const r of regions) {
    if (
      lat >= r.bounds.minLat && lat <= r.bounds.maxLat &&
      lon >= r.bounds.minLon && lon <= r.bounds.maxLon
    ) {
      console.log(`✅ Matched NOAA region: ${r.name}`);
      return r;
    }
  }

  console.warn(`❌ No match for lat: ${lat}, lon: ${lon}`);
  console.warn(`🔍 Tried bounds:`);
  for (const r of regions) {
    console.warn(
      ` - ${r.name}: lat[${r.bounds.minLat}, ${r.bounds.maxLat}], lon[${r.bounds.minLon}, ${r.bounds.maxLon}]`
    );
  }

  return null;
}

module.exports = { getRegionForCoordinates };
