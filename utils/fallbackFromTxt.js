const fs = require('fs');
const path = require('path');

async function fallbackFromTxt({ stationId }) {
  const safeStationId = stationId.replace(/\s+/g, '_');
  const filePath = path.join(__dirname, `../data/${safeStationId}.txt`);
  console.log('📄 Reading IDF TXT file for fallback:', filePath);

  const raw = fs.readFileSync(filePath, 'latin1');
  const lines = raw.split(/\r?\n/).map(l => l.trim()).filter(Boolean);

  console.log(`📏 File length: ${raw.length} chars`);
  console.log(`📊 Total lines: ${lines.length}`);

  // --- Clean function for Table 2B ---
  function cleanLine(line) {
    return line
      .replace(/\+\//g, '')        // remove "+/"
      .replace(/[^\d.\s-]/g, ' ')  // keep digits, minus, dots, spaces
      .replace(/\s+/g, ' ')        // normalize spaces
      .trim();
  }

  // --- Detect numeric blocks ---
  let numericBlocks = [];
  let currentBlock = [];
  lines.forEach(line => {
    if (/\d/.test(line)) {
      currentBlock.push(line);
    } else {
      if (currentBlock.length) {
        numericBlocks.push(currentBlock);
        currentBlock = [];
      }
    }
  });
  if (currentBlock.length) numericBlocks.push(currentBlock);

  console.log(`🔹 Found ${numericBlocks.length} numeric blocks in file`);

  // --- Pick the longest numeric block (likely Table 2B) ---
  const table2BBlock = numericBlocks.sort((a,b)=>b.length-a.length)[0] || [];
  console.log(`📊 Using numeric block with ${table2BBlock.length} lines as Table 2B`);
  console.log('First 5 raw lines from block:', table2BBlock.slice(0,5));

  const cleanedLines = table2BBlock.map(cleanLine).filter(Boolean);
  console.log('🔹 Cleaned first 5 lines:', cleanedLines.slice(0,5));

  // --- IDF structure ---
  const returnPeriods = ['2yr', '5yr', '10yr', '25yr', '50yr', '100yr'];
  const durations = [
    '5 min', '10 min', '15 min', '30 min',
    '60 min', '120 min', '180 min', '240 min', '1440 min'
  ];

  const idf = {};
  returnPeriods.forEach(rp => { idf[rp] = {}; });

  // --- Parse cleaned lines into IDF ---
  cleanedLines.slice(0, returnPeriods.length).forEach((line, idx) => {
    const cols = line.split(' ').filter(Boolean);
    console.log(`Line ${idx+1} → ${cols.length} cols:`, cols);

    if (cols.length < 10) {
      console.warn(`⚠️ Line ${idx+1} has ${cols.length} tokens (expected 10)`);
    }

    durations.forEach((dur, dIdx) => {
      const val = parseFloat(cols[dIdx + 1]); // first column is the return period
      if (!isNaN(val)) {
        idf[returnPeriods[idx]][dur] = val;
      }
    });
  });

  console.log('✅ Parsed Table 2B fallback IDF:', idf);

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
