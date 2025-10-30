const fs = require('fs');
const path = require('path');

// ✅ Parse TXT file for Table 2A (Rainfall Amounts)
async function fallbackFromTxt({ stationId }) {
  // 🔹 Build file path (stationId like "LONDON CS")
  const safeStationId = stationId.replace(/\s+/g, '_');
  const filePath = path.join(__dirname, `../data/${safeStationId}.txt`);
  console.log('📄 Reading IDF TXT file for fallback:', filePath);

  // 🔹 Read file and normalize spacing
  const raw = fs.readFileSync(filePath, 'latin1');
  const normalized = raw
    .normalize('NFKD')
    .replace(/[\u0000-\u001F\u007F-\u00A0]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  console.log(`📏 File length: ${normalized.length} chars`);

  // 🔹 Try to locate Table 2A section
  const lowerRaw = normalized.toLowerCase();
  const sectionStart = lowerRaw.indexOf('table 2a');
  if (sectionStart === -1) {
    throw new Error('Table 2A section not found in file');
  }

  // 🔹 Extract lines after Table 2A
  const tableContent = raw.slice(sectionStart);
  const lines = tableContent
    .split(/\r?\n/)
    .map(l => l.trim())
    .filter(Boolean)
    .filter(l => /^\d+/.test(l)); // keep lines starting with number (duration)

  console.log(`📊 Extracted ${lines.length} lines from Table 2A`);

  // 🔹 Duration → Label map
  const durationsMap = {
    5: '5 min',
    10: '10 min',
    15: '15 min',
    30: '30 min',
    60: '60 min',
    120: '120 min',
    180: '180 min',
    240: '240 min',
    1440: '1440 min'
  };

  // 🔹 Return periods
  const returnPeriods = ['2yr', '5yr', '10yr', '25yr', '50yr', '100yr'];
  const idf = {};
  returnPeriods.forEach(rp => { idf[rp] = {}; });

  // 🔹 Parse Table 2A lines
  lines.forEach(line => {
    const cols = line.split(/\s+/); // split by whitespace
    const durationMinutes = parseInt(cols[0], 10);
    const durationLabel = durationsMap[durationMinutes];
    if (!durationLabel) return; // skip unknown durations

    // 🔹 Convert rainfall amounts to intensity (mm/hr)
    //    - Durations < 60 min → divide amount by (duration / 60)
    //    - Durations >= 60 min → divide by duration in hours
    const durationHours = durationMinutes < 60 ? durationMinutes / 60 : durationMinutes / 60;

    returnPeriods.forEach((rp, idx) => {
      const amountMm = parseFloat(cols[idx + 1]);
      if (!isNaN(amountMm)) {
        const intensity = amountMm / durationHours; // mm/hr
        idf[rp][durationLabel] = parseFloat(intensity.toFixed(2));
      }
    });
  });

  console.log('✅ Parsed Table 2A fallback IDF:', idf);

  return {
    idf,
    station_id: stationId,
    rainfall_10yr: idf['10yr']?.['60 min'] || null,
    frost_depth: 1.5,
    setback_min: 1.2,
    snow_load_zone: 'S-1'
  };
}

module.exports = fallbackFromTxt;
