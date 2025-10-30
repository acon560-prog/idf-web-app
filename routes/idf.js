// File: server/routes/idf.js
const express = require('express');
const fs = require('fs');
const path = require('path');
const router = express.Router();
const stations = require('../utils/stations_lookup_verified_sample.json');

router.post('/', async (req, res) => {
  const { city, province } = req.body;
  if (!city || !province) return res.status(400).json({ error: 'Missing city or province' });

  const match = stations.find(s => s.province === province && city.toLowerCase().includes(s.name.toLowerCase().split(' ')[0]));
  if (!match) return res.status(404).json({ error: 'No nearby station found' });

  const txtFile = path.join(__dirname, `../../data/${match.stationId}_RAIN.txt`);
  if (!fs.existsSync(txtFile)) return res.status(404).json({ error: 'RAIN data file not found for this station' });

  try {
    const content = fs.readFileSync(txtFile, 'utf-8');
    const lines = content.split('\n');

    const idfData = {};
    const durations = [];
    const returnPeriods = [];

    let headerRow;
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].includes('RETURN PERIOD')) {
        headerRow = lines[i + 1].trim().split(/\s+/);
        durations.push(...headerRow.map(d => d.split('-')[0]).filter(d => d !== 'YEAR'));
        for (let j = i + 2; j < lines.length; j++) {
          const parts = lines[j].trim().split(/\s+/);
          if (parts.length < durations.length + 1) break;
          const year = parts[0];
          returnPeriods.push(Number(year));
          durations.forEach((d, idx) => {
            if (!idfData[d]) idfData[d] = {};
            idfData[d][year] = parseFloat(parts[1 + idx]);
          });
        }
        break;
      }
    }

    res.json({
      station: match.name,
      return_periods: returnPeriods,
      durations_min: durations,
      intensities: idfData
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to parse IDF file' });
  }
});

module.exports = router;
