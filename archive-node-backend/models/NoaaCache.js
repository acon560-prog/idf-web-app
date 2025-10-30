const mongoose = require('mongoose');

const NoaaCacheSchema = new mongoose.Schema({
  lat: Number,
  lon: Number,
  roundedLat: Number,
  roundedLon: Number,
  data: Object,
  createdAt: {
    type: Date,
    default: Date.now,
    expires: 60 * 60 * 24 * 30 // 30 days auto-expiry
  }
});

module.exports = mongoose.model('NoaaCache', NoaaCacheSchema);
