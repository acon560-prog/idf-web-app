const stations = require('./stations_lookup.json');

function haversineDistance(lat1, lon1, lat2, lon2) {
  const R = 6371; // km
  const toRad = deg => deg * (Math.PI / 180);

  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;

  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function findClosestTxtStation(lat, lon) {
  let closest = null;
  let minDistance = Infinity;

  for (const station of stations) {
    const dist = haversineDistance(lat, lon, station.lat, station.lon);
    if (dist < minDistance) {
      minDistance = dist;
      closest = station;
    }
  }

  return closest; // has .id and .txt_file
}

module.exports = findClosestTxtStation;
