const fs = require('fs');
const path = require('path');
const express = require('express');
const router = express.Router();
const https = require('https');
const http = require('http');
const unzipper = require('unzipper');
const NodeGeocoder = require('node-geocoder');
const slugify = require('slugify');
const Fuse = require('fuse.js');
const axios = require('axios')
// wrap it so we can call `slug(text)` just like before, with lowercase + no special chars
const slug = (text) => slugify(text, { lower: true, strict: true });

// Stations list with lat/lon (if available)
const stations = require('../utils/stations_lookup_demo_fixed.json');

// === Simple in-memory cache for parsed IDF results ===
const CACHE_TTL_MS = Number(process.env.IDF_CACHE_TTL_MS || 30 * 60 * 1000); // default 30m
const _cache = new Map(); // key -> { value, expires }
// Use the existing stations variable from require()
// Filter station entries missing lat/lon
const missingCoordsStations = stations.filter(s => !s.lat || !s.lon);
// Prepare addresses for geocoding as "name, province"
const addresses = missingCoordsStations.map(s => `${s.name}, ${s.province}`);
// Your Geoapify API key
const GEOAPIFY_API_KEY = 'c95c5d38956546b497bcfa8089453d08';

// Function to submit batch geocoding job
async function submitBatchJob(addresses) {
  const url = `https://api.geoapify.com/v1/batch/geocode/search?apiKey=${GEOAPIFY_API_KEY}`;
  try {
    const response = await axios.post(url, addresses, {
      headers: { 'Content-Type': 'application/json' },
    });
    if (response.status === 202) {
      return response.data;  // Contains job id and status URL
    } else {
      throw new Error(`Unexpected response status: ${response.status}`);
    }
  } catch (err) {
    console.error('Error submitting batch job:', err.message);
    throw err;
  }
}
// Function to poll for batch job results
async function pollBatchResults(resultUrl, interval = 30000, maxAttempts = 20) {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    console.log(`Checking batch job status: attempt ${attempt}`);
    const res = await axios.get(resultUrl);
    if (res.data.status === 'finished') {
      console.log('Batch job finished!');
      return res.data.results;
    } else if (res.data.status === 'failed') {
      throw new Error('Batch geocoding job failed');
    }
    // Wait before next poll
    await new Promise(r => setTimeout(r, interval));
  }
  throw new Error('Batch geocoding job timed out');
}
// Main execution function
async function runBatchGeocode() {
  try {
    console.log(`Submitting batch geocode job for ${addresses.length} addresses...`);
    const job = await submitBatchJob(addresses);

    console.log(`Job ID: ${job.id}`);
    console.log(`Status URL: ${job.url}`);

    // Poll for results
    const results = await pollBatchResults(`${job.url}&apiKey=${GEOAPIFY_API_KEY}`);

    // Update stations with coordinates
    results.forEach((result, idx) => {
      const station = missingCoordsStations[idx];
      if (result && result.lat && result.lon) {
        station.lat = result.lat;
        station.lon = result.lon;
      } else {
        console.warn(`No coords found for ${station.name}`);
      }
    });

    // Save updated stations JSON
    fs.writeFileSync('stations_updated.json', JSON.stringify(stations, null, 2));
    console.log('Updated stations saved to stations_updated.json');
  } catch (err) {
    console.error('Error in batch geocoding:', err);
  }
}

runBatchGeocode();
function cacheGet(key) {
  const hit = _cache.get(key);
  if (!hit) return null;
  if (hit.expires < Date.now()) { _cache.delete(key); return null; }
  return hit.value;
}
function cacheSet(key, value) {
  _cache.set(key, { value, expires: Date.now() + CACHE_TTL_MS });
}

// ---------- helpers ----------
const norm = (s) => (s ? String(s).trim() : '');
const lc = (s) => norm(s).toLowerCase();



const provider = process.env.GEOCODER_PROVIDER || 'openstreetmap';

let geocoder;

if (provider === 'openstreetmap') {
  // Your existing OSM config
  geocoder = NodeGeocoder({
    provider: 'openstreetmap',
    osmServer: 'https://nominatim.openstreetmap.org',
    userAgent: process.env.GEOCODER_UA || 'civil-eng-website/1.0 (+civispec.projects@gmail.com)',
    headers: {
      'User-Agent': process.env.GEOCODER_UA || 'civil-eng-website/1.0 (+civispec.projects@gmail.com)',
      'Referer': process.env.GEOCODER_REF || 'http://localhost'
    }
  });
} else if (provider === 'opencage') {
  geocoder = NodeGeocoder({
    provider: 'opencage',
    apiKey: process.env.GEOCODER_KEY
  });
} else if (provider === 'geoapify') {
  geocoder = NodeGeocoder({
    provider: 'geoapify',
    apiKey: process.env.GEOCODER_KEY
  });
} else {
  throw new Error(`Unknown geocoder provider: ${provider}`);
}

// Quick manual test
geocoder.geocode("Saguenay, QC")
  .then(console.log)
  .catch(console.error);

module.exports = geocoder;

//geocoder.geocode("Saguenay, QC").then(console.log).catch(console.error);
// Rough Quebec bounding box (keeps us out of the Canada centroid)
function isInQuebec(lat, lon) {
  return Number.isFinite(lat) && Number.isFinite(lon)
    && lat >= 45 && lat <= 63
    && lon >= -80 && lon <= -57;
}

// Reject the "center of Canada" false positive from Nominatim
const CANADA_CENTROID = { lat: 61.0666922, lon: -107.991707 };
function looksLikeCanadaCentroid(lat, lon) {
  return Number.isFinite(lat) && Number.isFinite(lon) &&
         haversine(lat, lon, CANADA_CENTROID.lat, CANADA_CENTROID.lon) < 300; // km
}

function haversine(lat1, lon1, lat2, lon2) {
  const R = 6371; // km
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * Math.PI / 180) *
      Math.cos(lat2 * Math.PI / 180) *
      Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function scoreStationMatch(stationName, city) {
  const ns = slug(stationName);
  const cs = slug(city);
  if (!ns || !cs) return 0;
  if (ns.includes(cs)) return 2; // strong contain
  const nset = new Set(ns.split(' '));
  const overlap = cs.split(' ').filter((t) => nset.has(t)).length;
  return overlap > 0 ? 1 : 0;
}
function chooseHttpModule(url) {
  return url.startsWith('https:') ? https : http;
}

function downloadToBuffer(url) {
  return new Promise((resolve, reject) => {
    const mod = chooseHttpModule(url);
    mod.get(url, (res) => {
      if (res.statusCode !== 200) {
        return reject(new Error(`HTTP ${res.statusCode} for ${url}`));
      }
      const chunks = [];
      res.on('data', (d) => chunks.push(d));
      res.on('end', () => resolve(Buffer.concat(chunks)));
    }).on('error', reject);
  });
}
function chooseHttpModule(url) {
  return url.startsWith('https:') ? https : http;
}

function downloadToBuffer(url, maxRedirects = 5) {
  return new Promise((resolve, reject) => {
    const seen = new Set();

    function go(currentUrl, redirectsLeft) {
      if (seen.has(currentUrl)) return reject(new Error('Redirect loop detected'));
      seen.add(currentUrl);

      const mod = chooseHttpModule(currentUrl);
      const req = mod.get(currentUrl, {
        headers: {
          'User-Agent': 'idf-fetcher/1.0 (+node)',
          'Accept': '*/*',
        },
        timeout: 30000
      }, (res) => {
        const status = res.statusCode || 0;

        // Handle redirects
        if ([301, 302, 303, 307, 308].includes(status)) {
          const loc = res.headers.location;
          if (!loc) return reject(new Error(`Redirect (${status}) without Location for ${currentUrl}`));
          if (redirectsLeft <= 0) return reject(new Error(`Too many redirects fetching ${currentUrl}`));
          const nextUrl = new URL(loc, currentUrl).toString();
          res.resume(); // drain any body
          return go(nextUrl, redirectsLeft - 1);
        }

        if (status !== 200) {
          let body = [];
          res.on('data', (d) => body.push(d));
          res.on('end', () => {
            body = Buffer.concat(body).toString('utf8').slice(0, 500);
            reject(new Error(`HTTP ${status} for ${currentUrl}: ${body}`));
          });
          return;
        }

        // 200 OK
        const chunks = [];
        res.on('data', (d) => chunks.push(d));
        res.on('end', () => resolve(Buffer.concat(chunks)));
      });

      req.on('timeout', () => req.destroy(new Error(`Timeout fetching ${currentUrl}`)));
      req.on('error', reject);
    }

    go(url, maxRedirects);
  });
}

const normalizeProvinceCode = (p) => {
  const v = lc(p);
  const map = {
    qc: 'QC', quebec: 'QC',
    on: 'ON', ontario: 'ON',
    pe: 'PE', pei: 'PE', 'prince edward island': 'PE',
    bc: 'BC', 'british columbia': 'BC',
    ab: 'AB', alberta: 'AB',
    mb: 'MB', manitoba: 'MB',
    sk: 'SK', saskatchewan: 'SK',
    ns: 'NS', 'nova scotia': 'NS',
    nb: 'NB', 'new brunswick': 'NB',
    nl: 'NL', 'newfoundland and labrador': 'NL', 'newfoundland & labrador': 'NL',
    yt: 'YT', yukon: 'YT',
    nt: 'NT', 'northwest territories': 'NT',
    nu: 'NU', nunavut: 'NU',
  };
  return map[v] || norm(p);
};

// Durations we care about (minutes) and hour values that appear in some files
const DURATIONS_MIN = [5, 10, 15, 30, 60, 120, 180, 240, 1440];
const RP_LABELS = ['2yr', '5yr', '10yr', '25yr', '50yr', '100yr'];
const HOUR_WHITELIST = new Set([1, 2, 3, 4, 24]); // hours → 60,120,180,240,1440
// ---------- Unified Duration Parser ----------
// Converts tokens like "5", "10 min", "1 h", "24 h", "24hrs", "1 day" → minutes
function parseDurTok(tok) {
 if (!tok) return null;
 tok = String(tok).trim().toLowerCase();

  // plain number (no unit)
  if (/^\d+(\.\d+)?$/.test(tok)) {
    const n = Number(tok);
    if ([5, 10, 15, 30, 60, 120, 180, 240, 1440].includes(n)) return n;
    if (n === 24) return 1440; // bare 24 hours
    if (n === 1) return 1440;  // bare 1 day
    return null;
  }

  // minutes
  const m = tok.match(/(\d+(\.\d+)?)\s*(min|m)\b/);
  if (m) return Math.round(Number(m[1]));

  // hours
  const h = tok.match(/(\d+(\.\d+)?)\s*(h|hr|hrs|hour|hours)\b/);
  if (h) return Math.round(Number(h[1]) * 60);

  // days
  const d = tok.match(/(\d+(\.\d+)?)\s*(d|day|days)\b/);
  if (d) return Math.round(Number(d[1]) * 1440);

  // explicit 24‑hour formats
  if (/^24\s*h(rs?)?$/i.test(tok) || /^24-?hr?s?$/i.test(tok)) return 1440;

  // explicit 1‑day formats
  if (/^1\s*(day|days|d)$/i.test(tok) || /^1-?day(s)?$/i.test(tok)) return 1440;

  // catch "24h" without space
  if (/^24[^0-9]*h/.test(tok)) return 1440;

  return null;
}
  function fileHasUsableDurations(stationFile) {
    try {
      const dataDir = getDataDir();
      const fPath = path.join(getDataDir(), stationFile);
      if (!fs.existsSync(fPath)) return false;
      const content = fs.readFileSync(fPath, 'utf-8').replace(/\r/g, '');
      const lines = content.split('\n').map(l => l.trim());
      const startIdx = lines.findIndex(l =>
        /(table(?:au)?\s*2[ab]?|rainfall amounts|pr[eé]cipitation)/i.test(l)
      );
      if (startIdx === -1) return false;
      const block = lines.slice(startIdx, startIdx + 40);
      let subDailyCount = 0;
      for (const raw of block) {
        const toks = raw.split(/\s+/).filter(Boolean);
        if (!toks.length) continue;
        const durMin = parseDurTok(toks[0] + (toks[1] ? ' ' + toks[1] : ''));
        if (durMin && durMin < 1440) subDailyCount++;
      }
      return subDailyCount >= 3; // need at least 3 sub-daily durations
    } catch (e) {
      return false;    function fileHasUsableDurations(stationFile) {
      try {
        const dataDir = getDataDir();
        const fPath = path.join(getDataDir(), stationFile);
        if (!fs.existsSync(fPath)) return false;
        const content = fs.readFileSync(fPath, 'utf-8').replace(/\r/g, '');
        const lines = content.split('\n').map(l => l.trim());
        const startIdx = lines.findIndex(l =>
          /(table(?:au)?\s*2[ab]?|rainfall amounts|pr[eé]cipitation)/i.test(l)
        );
        if (startIdx === -1) return false;
        const block = lines.slice(startIdx, startIdx + 40);
        let subDailyCount = 0;
        for (const raw of block) {
          const toks = raw.split(/\s+/).filter(Boolean);
          if (!toks.length) continue;
          const durMin = parseDurTok(toks[0] + (toks[1] ? ' ' + toks[1] : ''));
          if (durMin && durMin < 1440) subDailyCount++;
        }
        return subDailyCount >= 3; // need at least 3 sub-daily durations
      } catch (e) {
        return false;
      }
    }
    }
  }
// Normalize a first-column duration to minutes (supports minutes or hours)
function normalizeDurationToMinutes(firstNumber) {
  if (DURATIONS_MIN.includes(firstNumber)) return firstNumber; // already minutes
  const asInt = Math.round(firstNumber);
  // also explicitly catch 1 day written as "1" in days
  if (Math.abs(firstNumber - 1) < 1e-6) return 1440;
  if (HOUR_WHITELIST.has(asInt) && Math.abs(firstNumber - asInt) < 1e-6) {
    return asInt * 60; // convert hours → minutes
  }
  if (Math.abs(firstNumber - 0.5) < 1e-6) return 30; // rare: 0.5 h line
  return null;
}

// Split a row into numeric tokens (order preserved), tolerant of whitespace/CSV-ish files
function nums(row) {
  let parts = row.split(/\s+/).filter(Boolean);
  if (parts.length < 4) parts = row.split(/[,\t;]+/).filter(Boolean);
  return parts.map(Number).filter((n) => Number.isFinite(n));
}

// Small helper to describe a file record for /available
function parseFileRecord(f) {
  const base = path.basename(f);
  const lower = base.toLowerCase();
  const idMatch = base.match(/([0-9]+S[0-9]+|[0-9]{6,})/i);
  const stationId = idMatch ? idMatch[1] : null;

  let province = null;
  const provMatch = lower.match(/_(qc|on|bc|ab|mb|sk|ns|nb|nl|yt|nt|nu)_/i);
  if (provMatch) province = provMatch[1].toUpperCase();

  const nameGuess = base
    .replace(/idf_v3[-_]?30[_-]\d{4}[_-]\d{2}[_-]\d{2}/i, '')
    .replace(new RegExp(`_${province}_`, 'i'), '_')
    .replace(new RegExp(stationId || '', 'i'), '')
    .replace(/_?\d{4}-\d{4}_?/g, '_')
    .replace(/_?(RAIN|PRECIP|IDF|INTENSITY|TXT)\b/i, '')
    .replace(/[_\-\.]+/g, ' ')
    .trim();

  return { file: base, stationId, province, name: nameGuess || base };
}

// ---- data dir helper (reuse everywhere) ----
function getDataDir() {
  return process.env.DATA_DIR
    ? (path.isAbsolute(process.env.DATA_DIR) ? process.env.DATA_DIR : path.join(__dirname, process.env.DATA_DIR))
    : path.join(__dirname, '../data');
}

// ---- station index (file-backed) ----
let STATION_INDEX = []; // [{stationId,name,province,lat,lon,file}]

// Helper function to clean station names before matching
function cleanName(name) {
  return name
    .toLowerCase()
    .replace(/\b\d+\b/g, '')       // Remove standalone numbers like "709"
    .replace(/\btxt\b/g, '')       // Remove literal "txt"
    .replace(/_/g, ' ')            // Replace underscores with spaces
    .replace(/[^a-z\s]/g, '')      // Remove non-letter characters
    .trim()
    .replace(/\s+/g, ' ');         // Collapse multiple spaces
}
// Declare arrays once at top level of your file or main function:
const matchedStations = [];
const unmatchedStations = [];
function buildStationIndex() {
  const dataDir = getDataDir();
  const files = fs.existsSync(dataDir) ? fs.readdirSync(dataDir) : [];
  const txts = files.filter(f => f.toLowerCase().endsWith('.txt'));

  // Load your stations JSON (update path as needed)
  let stations = [];
  try {
    const stationsJsonPath = path.join(__dirname, '../utils/stations_lookup_demo_fixed.json');
    stations = JSON.parse(fs.readFileSync(stationsJsonPath, 'utf8'));
    console.log(`Loaded ${stations.length} stations from JSON.`);
  } catch (err) {
    console.error('Failed to load stations JSON:', err);
  }

  const byId = new Map((stations || []).map(s => [String(s.stationId || '').toLowerCase(), s]));

  const index = [];
  for (const f of txts) {
  const idMatch = f.match(/([0-9]+S[0-9]+|[0-9]{6,})/i);
  const stationId = idMatch ? idMatch[1] : null;
  if (!stationId) continue;

  const meta = byId.get(String(stationId).toLowerCase()) || {};
  const nameGuess = path.basename(f)
    .replace(/idf\_v3[-\_]?30[\_-]\d{4}[\_-]\d{2}[\_-]\d{2}/i, '')
    .replace(new RegExp(stationId, 'i'), '')
    .replace(/\_(QC|ON|BC|AB|MB|SK|NS|NB|NL|YT|NT|NU)\_/i, '_')
    .replace(/\_\d{4}-\d{4}\_/g, '_')
    .replace(/\_(RAIN|PRECIP|IDF|INTENSITY|TXT)\b/i, '')
    .replace(/[\._\-\\]+/g, ' ')
    .trim();

  const entry = {
    stationId,
    name: meta.name || nameGuess || stationId,
    province: meta.province || (f.match(/\_(QC|ON|BC|AB|MB|SK|NS|NB|NL|YT|NT|NU)\_/i)?.[1]?.toUpperCase() || null),
    lat: Number(meta.lat) || null,
    lon: Number(meta.lon) || null,
    file: f
  };

  console.log("Processing station entry:", entry.stationId, entry.name, entry.lat, entry.lon);

  if ((entry.lat == null || entry.lon == null) && entry.name) {
    console.log("DEBUG: Checking entry", {
      name: entry.name,
      lat: entry.lat,
      lon: entry.lon,
      province: entry.province
    });

    const cleanEntryName = cleanName(entry.name);
    const provinceStations = (stations || []).filter(s => s.province === entry.province);

    console.log("DEBUG: Found", provinceStations.length, "candidates in province", entry.province);

    if (provinceStations.length > 0) {
      const fuseLocal = new Fuse(provinceStations, {
        keys: ['name'],
        threshold: 0.5,
        ignoreLocation: true,
        getFn: obj => cleanName(obj.name)
      });

      const results = fuseLocal.search(cleanEntryName);
      console.log("DEBUG: Fuse.js results for", entry.name, results.map(r => r.item.name));

      if (results.length > 0) {
        const bestMatch = results[0]?.item;  // Safe access to prevent TypeError

        if (bestMatch && bestMatch.lat != null && bestMatch.lon != null) {
          entry.lat = Number(bestMatch.lat);
          entry.lon = Number(bestMatch.lon);
          matchedStations.push({
            entryName: entry.name,
            matchedName: bestMatch.name,
            province: bestMatch.province,
            lat: bestMatch.lat,
            lon: bestMatch.lon,
            file: entry.file
          });
          console.log(`MATCHED: "${entry.name}" ➔ "${bestMatch.name}" (${bestMatch.province}) lat=${entry.lat} lon=${entry.lon}`);
        } else {
          unmatchedStations.push({ entryName: entry.name, reason: "No coords in matched station" });
          console.warn(`NO COORDS: Matched "${bestMatch?.name || 'UNKNOWN'}" for "${entry.name}" but no coordinates available`);
        }
      } else {
        unmatchedStations.push({ entryName: entry.name, province: entry.province, reason: "No fuzzy match found" });
        console.warn(`NO MATCH: "${entry.name}" in province ${entry.province}`);
      }
    } else {
      unmatchedStations.push({ entryName: entry.name, province: entry.province, reason: "No stations in province" });
      console.warn(`NO CANDIDATES: No stations available in province ${entry.province} for "${entry.name}"`);
    }
  }

  if (fileHasUsableDurations && fileHasUsableDurations(f)) {
    index.push(entry);
  } else {
    console.log(`⏩ Skipping ${f} — multi-day only`);
  }
}

STATION_INDEX = index;

console.log(`📚 Station index built: ${STATION_INDEX.length} stations with files`);
console.log('--- Matched stations count:', matchedStations.length);
console.log('--- Unmatched stations count:', unmatchedStations.length);
// Write diagnostic files
fs.writeFileSync('matchedStations.json', JSON.stringify(matchedStations, null, 2));
fs.writeFileSync('unmatchedStations.json', JSON.stringify(unmatchedStations, null, 2));

}

// build once on load
buildStationIndex();
// ---------- GET /api/idf/available ----------
router.get('/available', (req, res) => {
  try {
    const dataDir = process.env.DATA_DIR
      ? (path.isAbsolute(process.env.DATA_DIR) ? process.env.DATA_DIR : path.join(__dirname, process.env.DATA_DIR))
      : path.join(__dirname, '../data');

    if (!fs.existsSync(dataDir)) {
      return res.status(500).json({ error: 'Data directory not found', expectedDir: dataDir });
    }

    const province = req.query.province ? String(req.query.province).trim().toUpperCase() : null;
    const q = req.query.q ? String(req.query.q).trim().toLowerCase() : null;

    const all = fs.readdirSync(dataDir).filter(f => f.toLowerCase().endsWith('.txt'));
    let items = all.map(parseFileRecord);

    if (province) items = items.filter(x => x.province === province);
    if (q) {
      const slugQ = q.replace(/[^a-z0-9]+/g, ' ').trim();
      items = items.filter(x =>
        (x.stationId && x.stationId.toLowerCase().includes(q)) ||
        (x.name && x.name.toLowerCase().includes(q)) ||
        (x.file && x.file.toLowerCase().includes(q)) ||
        (x.name && x.name.replace(/[^a-z0-9]+/g, ' ').includes(slugQ))
      );
    }

    items.sort((a,b) => (a.province || '').localeCompare(b.province || '') || (a.name || '').localeCompare(b.name || ''));
    return res.json({ count: items.length, items });
  } catch (err) {
    console.error('Error in GET /api/idf/available:', err);
    return res.status(500).json({ error: 'Failed to list available IDF files' });
  }
});
// ---- parse + respond helper (reuses your existing parsing logic) ----
function parseAndRespondFromFile({ dataDir, chosenFile, unitSystem }, res) {
  try {
    // cache key
    const cacheKey = `${chosenFile}|${lc(unitSystem)}`;
    const cached = cacheGet(cacheKey);
    if (cached) {
      return res.json({
        file: chosenFile,
        idf: cached.idf,
        units: cached.units
      });
    }

    // read + parse (this is the SAME logic you already have in POST /api/idf)
    const txtPath = path.join(dataDir, chosenFile);
    const content = fs.readFileSync(txtPath, 'utf-8');
    const lines = content.replace(/\r/g, '').split('\n').map((l) => l.trim());
    // more flexible: match "Table 2", "Table 2a", "Table 2b", French, etc.
    const startIdx = lines.findIndex((l) =>
      /(table(?:au)?\s*2[ab]?|rainfall amounts|pr[eé]cipitation)/i.test(l)
    );
    if (startIdx === -1) {
      return res.status(500).json({ error: 'Rainfall amounts table not found', file: chosenFile });
    }
    
    let endIdx = lines.slice(startIdx + 1).findIndex((l) => /^table\b/i.test(l));
    endIdx = endIdx === -1 ? lines.length : startIdx + 1 + endIdx;
    const block = lines.slice(startIdx + 1, endIdx);

   const idfDepths = {};
    const idfIntensities = {};
    RP_LABELS.forEach((rp) => { idfDepths[rp] = {}; idfIntensities[rp] = {}; });

    // ---- Row-oriented Table 2A parse (same as /curves) ----
    const RP_LIST = [2, 5, 10, 25, 50, 100];
    let parsedAny = false;
    for (const raw of block) {
      if (!raw) continue;
      const toks = raw.split(/\s+/).filter(Boolean);
      if (toks.length < 3) continue;
      const durMin = parseDurTok(toks[0] + (toks[1] ? ' ' + toks[1] : ''));
      if (!durMin) continue;
      let startValsIdx = 1;
      if (/(min|m|h|hr|hrs|hour|hours|d|day|days)/i.test(toks[1] || '')) {
        startValsIdx = 2;
      }
      const vals = toks.slice(startValsIdx).map(Number);
      for (let i = 0; i < RP_LIST.length; i++) {
        const rpName = `${RP_LIST[i]}yr`;
        const val = vals[i];
        if (!Number.isFinite(val)) continue;
        idfDepths[rpName][`${durMin} min`] = Number(val.toFixed(2));
        let inten = (val * 60) / durMin;
        if (lc(unitSystem) === 'imperial') inten *= 0.0393701;
        idfIntensities[rpName][`${durMin} min`] = Number(inten.toFixed(2));
        parsedAny = true;
      }
    }

    // ---- Fallback: RP-rows orientation ----
    if (!parsedAny) {
      const numericRows = block
        .map((row) => nums(row))
        .filter((v) => v.length >= 9)
        .slice(0, RP_LABELS.length);
      let rpIdx = 0;
      for (const v of numericRows) {
        if (rpIdx >= RP_LABELS.length) break;
        const rp = RP_LABELS[rpIdx++];
        DURATIONS_MIN.forEach((dur, i) => {
          const amount = v[i];
          if (!Number.isFinite(amount)) return;
          idfDepths[rp][`${dur} min`] = Number(amount.toFixed(2));
          let intensity = (amount * 60) / dur;
          if (lc(unitSystem) === 'imperial') intensity *= 0.0393701;
          idfIntensities[rp][`${dur} min`] = Number(intensity.toFixed(2));
        });
      }
    }


//use the shared parseDurTok defined at top

// 1) Identify candidate header line (contains duration hints) — scan a handful of lines
let headerIdx = -1;
for (let i = 0; i < Math.min(block.length, 6); i++) {
  const t = block[i].toLowerCase();
  if (/(duration|dur[eé]e|min|h|hr|hour|hours|day)/.test(t)) {
    headerIdx = i; break;
  }
}
// If no obvious header, treat the whole block as body
const bodyStart = headerIdx >= 0 ? headerIdx + 1 : 0;
const body = block.slice(bodyStart);

// 2) Accumulate numbers per duration across wrapped lines
//    ECCC often splits a duration row into 2 lines (first 3 RPs then next 3).
const valuesByDur = new Map(); // minutes -> array of depths
let currentDur = null;

for (const raw of body) {
  if (!raw) continue;

  // split tokens but keep the first token to check if it's a duration
  const tokens = raw.split(/\s+/).filter(Boolean);
  if (tokens.length === 0) continue;

  // try first token as duration
  const maybeDur = parseDurTok(tokens[0]);
  let startCol = 0;
  if (maybeDur != null) {
    currentDur = maybeDur;
    startCol = 1;
    if (!valuesByDur.has(currentDur)) valuesByDur.set(currentDur, []);
  } else if (currentDur == null) {
    // still haven't locked onto a duration; skip
    continue;
  }

  // parse numbers from the rest of the line and append
  const arr = valuesByDur.get(currentDur) || [];
  for (let i = startCol; i < tokens.length; i++) {
    const n = Number(tokens[i].replace(/[^\d.+-]/g, '')); // strip stray symbols
    if (Number.isFinite(n)) arr.push(n);
  }
  valuesByDur.set(currentDur, arr);
}

// 3) Normalize durations to canonical order and fill missing ones if we can infer
const CANON_DURS = [5, 10, 15, 30, 60, 120, 180, 240, 1440];

// Some files omit 5 or 1440 in header but still provide 9 values per RP. If for each
// duration we see exactly 6 values (for 6 RPs) and the set of durations we found is 7,
// we can trust the found durations; otherwise, if we found 7 durations and every array
// length is 6, but missing 5 or 1440, we’ll still use only the found ones.
// (Do not invent values; only include durations we parsed.)
const durationsFound = [...valuesByDur.keys()].sort((a,b) => a - b);

// 4) Build depths/intensities from the accumulated arrays
for (const dur of durationsFound) {
  const depthsForDur = valuesByDur.get(dur) || [];
  // Some files have more than 6 numbers — keep the first 6 (2yr..100yr order)
  const firstSix = depthsForDur.slice(0, RP_LABELS.length);
  for (let c = 0; c < firstSix.length; c++) {
    const amount = firstSix[c];
    if (!Number.isFinite(amount)) continue;

    const rp = RP_LABELS[c]; // ["2yr","5yr","10yr","25yr","50yr","100yr"]

    // store depth
    idfDepths[rp][`${dur} min`] = Number(amount.toFixed(2));

    // intensity (always depth_mm * 60 / minutes)
    let intensity = (amount * 60) / dur;
    if (lc(unitSystem) === 'imperial') intensity *= 0.0393701;
    idfIntensities[rp][`${dur} min`] = Number(intensity.toFixed(2));
  }
}

// 5) Expose the durations we actually parsed (sorted ascending)
 const parsedDurations = Array.from(new Set(
     durationsFound
       .map(n => parseInt(String(n).replace(/[^\d]/g, ''), 10))
       .filter(n => Number.isFinite(n))
   )).sort((a,b) => a - b);
// ---- END replacement ----


    const units = {
      depths: 'mm',
      intensities: lc(unitSystem) === 'imperial' ? 'in/hr' : 'mm/hr'
    };

    cacheSet(cacheKey, { idf: { depths_mm: idfDepths, intensities: idfIntensities }, units });

    return res.json({
    file: chosenFile,
    durations: parsedDurations,
    series: RP_LABELS.map((rp) => ({
      name: rp,
      points: parsedDurations.map((d) => ({
        x: d,
        y: idfIntensities[rp]?.[`${d} min`] ?? null
      }))
    })),
    units,
    idf: { depths_mm: idfDepths, intensities: idfIntensities }
  });

  } catch (err) {
    console.error('❌ parseAndRespondFromFile error:', err);
    return res.status(500).json({ error: 'Failed to parse IDF file', detail: err.message });
  }
}

// ---------- POST /api/idf ----------
router.post('/', async (req, res) => {
  try {
    let { city, province, unitSystem, stationId } = req.body;
    if (!city || !province) {
      return res.status(400).json({ error: 'City and province are required' });
    }
    city = norm(city);
    province = normalizeProvinceCode(province);

    // --- data dir & file inventory ---
    const dataDir = process.env.DATA_DIR
      ? (path.isAbsolute(process.env.DATA_DIR) ? process.env.DATA_DIR : path.join(__dirname, process.env.DATA_DIR))
      : path.join(__dirname, '../data');

    if (!fs.existsSync(dataDir)) {
      return res.status(500).json({ error: 'Data directory not found', expectedDir: dataDir });
    }

    const files = fs.readdirSync(dataDir);
    const filesL = files.map((f) => f.toLowerCase());

    // Does a station have *some* usable .txt file?
   function stationHasFile(st) {
  const idL = String(st.stationId || '').toLowerCase();
  const nameS = slug(st.name || '');

  const match = filesL.some((f) => {
    const result = (
      f.endsWith('.txt') &&
      ((idL && f.includes(idL)) || (nameS && slug(f).includes(nameS)))
    );
    if (slug(f).includes('bagotville')) {
      console.log('Checking file', f, 'against station', st.stationId, st.name, '=>', result);
    }
    return result;
  });

  return match;
}

    // ---- FAST PATH: if a stationId is provided, use it directly ----
if (stationId) {
  const idLower = String(stationId).toLowerCase();
  const chosenFile =
    files.find(f => f.toLowerCase().endsWith('.txt') && f.toLowerCase().includes(idLower));

  if (!chosenFile) {
    return res.status(404).json({
      error: 'Requested stationId has no matching data file in /data',
      stationId,
      filesPreview: files.slice(0, 20),
    });
  }

  console.log(`📍 Direct stationId match → file: ${chosenFile}`);
  return parseAndRespondFromFile({ dataDir, chosenFile, unitSystem }, res);
}



// after your /api/idf/refresh completes (in that route), call buildStationIndex() again.

    // 1) Candidates = stations in province **with matching file**
    const inProv = stations.filter((st) => normalizeProvinceCode(st.province) === province);
    let candidates = inProv.filter(stationHasFile);
    // DEBUG: list candidate stations
    console.log('Candidates:', candidates.map(s => ({
      id: s.stationId,
      name: s.name,
      province: s.province,
      lat: s.lat,
      lon: s.lon
    })));
    // FILE-DRIVEN FALLBACK: if none found, synthesize candidates from filenames in this province
    if (!candidates.length) {
      const provToken = `_${province.toLowerCase()}_`;
      const txtsInProv = files.filter(
        (f) => f.toLowerCase().endsWith('.txt') && f.toLowerCase().includes(provToken)
      );
      if (!txtsInProv.length) {
        return res.status(404).json({
          error: `No stations with data files found for province ${province}`,
          hint: 'Add a TXT for that province or adjust naming to include _<PROVINCE>_.',
          dataDir,
          filesPreview: files.slice(0, 15),
        });
      }
      candidates = txtsInProv.map((f) => {
        // Accept IDs like 7016520 OR 702S006
        const idMatch = f.match(/([0-9]+S[0-9]+|[0-9]{6,})/i);
        const id = idMatch ? idMatch[1] : null;
        const base = path.basename(f, path.extname(f));
        let nameGuess = base
          .replace(new RegExp(id || '', 'i'), '')
          .replace(new RegExp(`_${province}_`, 'i'), '_')
          .replace(/_?\d{4}-\d{4}_?/g, '_')
          .replace(/_?(RAIN|PRECIP|IDF|INTENSITY|TXT|V3[-_]?30)\b/i, '')
          .replace(/idf_v3[-_]?30[_-]\d{4}[_-]\d{2}[_-]\d{2}/i, '')
          .replace(/[_\-]+/g, ' ')
          .trim();
        return { stationId: id || base, name: nameGuess || base, province, _file: f };
      });
    }

    // 2) If stationId is supplied, honor it (search files FIRST, then stations)
    let chosen = null;
    let chosenDist = Infinity;

    if (stationId) {
      const wanted = String(stationId).toLowerCase();
      const byIdFile = files.find(
        (f) => f.toLowerCase().includes(wanted) && f.toLowerCase().endsWith('.txt')
      );

      if (byIdFile) {
        const base = path.basename(byIdFile, path.extname(byIdFile));
        let nameGuess = base
          .replace(new RegExp(wanted, 'i'), '')
          .replace(/_?(QC|ON|BC|AB|MB|SK|NS|NB|NL|YT|NT|NU)_?/i, '_')
          .replace(/_?\d{4}-\d{4}_?/g, '_')
          .replace(/_?(RAIN|PRECIP|IDF|INTENSITY|TXT|V3[-_]?30)\b/i, '')
          .replace(/idf_v3[-_]?30[_-]\d{4}[_-]\d{2}[_-]\d{2}/i, '')
          .replace(/[_\-]+/g, ' ')
          .trim();
        chosen = { stationId, name: nameGuess || base, province, _file: byIdFile };
      } else {
        const forced = candidates.find(
          (st) => String(st.stationId).toLowerCase() === wanted
        );
        if (!forced) {
          return res.status(404).json({
            error: 'Requested stationId has no matching data file in /data',
            stationId,
            filesPreview: files.slice(0, 20),
          });
        }
        chosen = forced;
      }
    }

    // 3) Nearest by coords if request includes lat/lon and candidate has lat/lon
    const reqLat = Number(req.body.lat);
    const reqLon = Number(req.body.lon);
    const hasReqCoords = Number.isFinite(reqLat) && Number.isFinite(reqLon);

    if (!chosen && hasReqCoords) {
      for (const st of candidates) {
        const stLat = Number(st.lat);
        const stLon = Number(st.lon);
        if (!Number.isFinite(stLat) || !Number.isFinite(stLon)) continue;
        const d = haversine(reqLat, reqLon, stLat, stLon);
        if (d < chosenDist) {
          chosenDist = d;
          chosen = st;
        }
      }
    }

    // 4) Name-match fallback
    if (!chosen) {
      let bestScore = -1;
      for (const st of candidates) {
        const sc = scoreStationMatch(st.name || '', city);
        if (sc > bestScore) {
          bestScore = sc;
          chosen = st;
        }
      }
      if (!chosen) chosen = candidates[0];
    }

    const chosenId = norm(chosen.stationId);

    // 5) Pick the actual file for the chosen station (honour _file first)
    let chosenFile = null;
    if (chosen && chosen._file) {
      chosenFile = chosen._file; // from stationId override or file-driven fallback
    } else {
      const idL = (chosenId || '').toLowerCase();
      const nameS = slug(chosen.name || '');
      chosenFile =
        files.find((f) => f.toLowerCase().endsWith('.txt') && f.toLowerCase().includes(idL)) ||
        files.find((f) => f.toLowerCase().endsWith('.txt') && slug(f).includes(nameS));
    }

    if (!chosenFile) {
      return res.status(404).json({
        error: 'Data file not found for chosen station',
        station: { id: chosenId || null, name: chosen.name },
        dataDir,
        filesPreview: files.slice(0, 15),
      });
    }

    // ---- Cache check (per file + unitSystem) ----
    const cacheKey = `${chosenFile}|${lc(unitSystem)}`;
    const cached = cacheGet(cacheKey);
    if (cached) {
      return res.json({
        station: {
          id: chosenId || null,
          name: chosen.name,
          province: province,
          ...(Number.isFinite(chosenDist) ? { distance_km: Number(chosenDist.toFixed(2)) } : {}),
        },
        file: chosenFile,
        idf: cached.idf,
        units: cached.units
      });
    }

    const txtPath = path.join(dataDir, chosenFile);
    console.log(
      `📍 Station chosen: ${chosen.name} (${chosenId || 'no-id'})  file: ${chosenFile}${
        Number.isFinite(chosenDist) ? `  ~${chosenDist.toFixed(1)} km` : ''
      }`
    );

    // ---------- Robust Table 2A parser (depths → intensities) ----------
    const content = fs.readFileSync(txtPath, 'utf-8');
    const lines = content.replace(/\r/g, '').split('\n').map((l) => l.trim());

    // Find the rainfall amounts table
    const startIdx = lines.findIndex((l) =>
      /(table\s*2a|tableau\s*2a|rainfall amounts|pr[eé]cipitation)/i.test(l)
    );
    if (startIdx === -1) {
      return res.status(500).json({ error: 'Rainfall amounts table not found', file: chosenFile });
    }
    let endIdx = lines.slice(startIdx + 1).findIndex((l) => /^table\b/i.test(l));
    endIdx = endIdx === -1 ? lines.length : startIdx + 1 + endIdx;

    const block = lines.slice(startIdx + 1, endIdx);

    // Outputs: depths (mm) and intensities (mm/hr or in/hr)
    const idfDepths = {};
    const idfIntensities = {};
    RP_LABELS.forEach((rp) => {
      idfDepths[rp] = {};
      idfIntensities[rp] = {};
    });

    // Extract rows whose first numeric token is a known duration (minutes) or allowed hours
    const durRows = [];
    for (const row of block) {
      const v = nums(row);
      if (v.length >= 7) {
        const durMin = normalizeDurationToMinutes(v[0]);
        if (durMin != null) {
          v[0] = durMin; // normalize column 0 to minutes
          durRows.push(v);
        }
      }
      if (durRows.length === DURATIONS_MIN.length) break;
    }

    if (durRows.length) {
      // orientation: durations as rows; columns 1..6 are depths for 2..100 yr
      for (const v of durRows) {
        const dur = v[0];
        for (let c = 0; c < RP_LABELS.length; c++) {
          const amount = v[c + 1]; // depth in mm
          if (!Number.isFinite(amount)) continue;

          // store depth
          idfDepths[RP_LABELS[c]][`${dur} min`] = Number(amount.toFixed(2));

          // convert to intensity: depth_mm * 60 / minutes (ALWAYS)
          let intensity = (amount * 60) / dur; // mm/hr
          if (lc(unitSystem) === 'imperial') intensity *= 0.0393701; // -> in/hr
          idfIntensities[RP_LABELS[c]][`${dur} min`] = Number(intensity.toFixed(2));
        }
      }
    } else {
      // Fallback: treat rows as "RP rows" (first 6 rows), first 9 numbers are depths
      const numericRows = block
        .map((row) => nums(row))
        .filter((v) => v.length >= 9)
        .slice(0, RP_LABELS.length);

      let rpIdx = 0;
      for (const v of numericRows) {
        if (rpIdx >= RP_LABELS.length) break;
        const rp = RP_LABELS[rpIdx++];
        DURATIONS_MIN.forEach((dur, i) => {
          const amount = v[i]; // depth in mm
          if (!Number.isFinite(amount)) return;

          idfDepths[rp][`${dur} min`] = Number(amount.toFixed(2));

          let intensity = (amount * 60) / dur; // mm/hr
          if (lc(unitSystem) === 'imperial') intensity *= 0.0393701;
          idfIntensities[rp][`${dur} min`] = Number(intensity.toFixed(2));
        });
      }
    }

    // Ensure we parsed something
    const nonEmpty =
      Object.values(idfDepths).some((v) => Object.keys(v).length) &&
      Object.values(idfIntensities).some((v) => Object.keys(v).length);

    if (!nonEmpty) {
      return res.status(500).json({
        error: 'Parsed zero rows from rainfall table (format mismatch?)',
        file: chosenFile
      });
    }

    const units = {
      depths: 'mm',
      intensities: lc(unitSystem) === 'imperial' ? 'in/hr' : 'mm/hr'
    };

    // write to cache
    cacheSet(cacheKey, { idf: { depths_mm: idfDepths, intensities: idfIntensities }, units });

    return res.json({
      station: {
        id: chosenId || null,
        name: chosen.name,
        province: province,
        ...(Number.isFinite(chosenDist) ? { distance_km: Number(chosenDist.toFixed(2)) } : {}),
      },
      file: chosenFile,
      idf: { depths_mm: idfDepths, intensities: idfIntensities },
      units
    });
  } catch (err) {
    console.error('❌ Error in /api/idf:', err);
    return res.status(500).json({ error: 'Failed to fetch IDF data' });
  }
});

// POST /api/idf/refresh
// Body example:
// { "provinces": ["QC","ON"], "only": "montreal", "force": false, "dryRun": false, "deleteOrphans": true }
// Env:
// IDF_BASE_URL=https://collaboration.cmc.ec.gc.ca/cmc/climate/Engineer_Climate/IDF/idf_v3-30_2022_10_31/IDF_Files_Fichiers
router.post('/refresh', async (req, res) => {
  try {
    const BASE = process.env.IDF_BASE_URL ? String(process.env.IDF_BASE_URL).replace(/\/+$/, '') : null;
    if (!BASE) {
      return res.status(400).json({
        error: 'IDF_BASE_URL not set',
        hint: 'Set IDF_BASE_URL in .env to the folder that contains QC.zip, ON.zip, etc.'
      });
    }

    let { provinces, only, force, dryRun, deleteOrphans } = req.body || {};
    if (!Array.isArray(provinces) || provinces.length === 0) {
      return res.status(400).json({ error: 'Body must include "provinces": ["QC","ON",...]' });
    }
    provinces = provinces.map(p => String(p).trim().toUpperCase());
    const PROV_SET = new Set(['QC','ON','BC','AB','MB','SK','NS','NB','NL','YT','NT','NU']);
    const bad = provinces.filter(p => !PROV_SET.has(p));
    if (bad.length) {
      return res.status(400).json({ error: `Invalid province codes: ${bad.join(', ')}` });
    }

    const onlyFilter = (only ? String(only).toLowerCase() : '').trim();
    const doForce = Boolean(force);
    const doDryRun = Boolean(dryRun);
    const doDeleteOrphans = Boolean(deleteOrphans);

    const dataDir = process.env.DATA_DIR
      ? (path.isAbsolute(process.env.DATA_DIR) ? process.env.DATA_DIR : path.join(__dirname, process.env.DATA_DIR))
      : path.join(__dirname, '../data');
    if (!fs.existsSync(dataDir) && !doDryRun) fs.mkdirSync(dataDir, { recursive: true });

    const results = [];

    for (const prov of provinces) {
      const zipUrl = `${BASE}/${prov}.zip`;
      const buf = await downloadToBuffer(zipUrl); // follows redirects

      // Snapshot current province files (for orphan detection)
      const allLocal = fs.existsSync(dataDir)
        ? fs.readdirSync(dataDir).filter(f =>
            f.toLowerCase().endsWith('.txt') &&
            f.toLowerCase().includes(`_${prov.toLowerCase()}_`) &&
            (!onlyFilter || f.toLowerCase().includes(onlyFilter))
          )
        : [];

      const currentSet = new Set(allLocal.map(f => f)); // basenames

      const directory = await unzipper.Open.buffer(buf);

      let extracted = 0;
      let overwritten = 0;
      let skippedExisting = 0;
      let skippedByFilter = 0;

      const files = [];
      const writtenSet = new Set(); // track files we extracted/overwrote this run

      for (const entry of directory.files) {
        const name = entry.path; // e.g. idf_v3-30_..._QC_702S006_...txt
        const lower = name.toLowerCase();

        if (!lower.endsWith('.txt')) continue;
        if (!lower.includes(`_${prov.toLowerCase()}_`)) continue; // safety: ensure province match

        if (onlyFilter && !lower.includes(onlyFilter)) {
          skippedByFilter++;
          continue;
        }

        const baseName = path.basename(name);
        writtenSet.add(baseName);

        const outPath = path.join(dataDir, baseName);
        const exists = fs.existsSync(outPath);

        if (exists && !doForce) {
          skippedExisting++;
          files.push({ file: baseName, action: 'skipped-existing' });
          continue;
        }

        if (doDryRun) {
          files.push({ file: baseName, action: exists ? 'would-overwrite' : 'would-extract' });
          if (exists) { overwritten++; } else { extracted++; }
          continue;
        }

        // write to disk
        await new Promise((resolve, reject) => {
          const ws = fs.createWriteStream(outPath);
          entry.stream().pipe(ws).on('finish', resolve).on('error', reject);
        });

        if (exists) {
          overwritten++;
          files.push({ file: baseName, action: 'overwritten' });
        } else {
          extracted++;
          files.push({ file: baseName, action: 'extracted' });
        }
      }

      // Orphan detection (province-scoped + optional substring filter)
      const orphanCandidates = allLocal.filter(f => !writtenSet.has(f));
      let deleted = 0;
      const orphans = [];

      if (orphanCandidates.length) {
        if (doDryRun || !doDeleteOrphans) {
          // report only
          for (const f of orphanCandidates) {
            orphans.push({ file: f, action: doDryRun ? 'would-delete' : 'kept (deleteOrphans=false)' });
          }
        } else {
          // actually delete
          for (const f of orphanCandidates) {
            try {
              fs.unlinkSync(path.join(dataDir, f));
              deleted++;
              orphans.push({ file: f, action: 'deleted' });
            } catch (e) {
              orphans.push({ file: f, action: `delete-failed: ${e.message}` });
            }
          }
        }
      }

      results.push({
        province: prov,
        extracted,
        overwritten,
        skippedExisting,
        skippedByFilter,
        deletedOrphans: deleted,
        files,
        orphans
      });
    }
    buildStationIndex();
    return res.json({
      ok: true,
      base: BASE,
      dataDir,
      dryRun: doDryRun,
      force: doForce,
      deleteOrphans: doDeleteOrphans,
      results
    });
  } catch (err) {
    console.error('Error in POST /api/idf/refresh:', err);
    return res.status(500).json({ error: 'Failed to refresh IDF files', detail: err.message });
  }
});
// GET /api/idf/by-place?place=Saguenay,%20QC&province=QC&unitSystem=metric&fetch=true
router.get('/by-place', async (req, res) => {
  try {
    const placeRaw = (req.query.place || '').toString().trim();
    const province = (req.query.province || '').toString().trim().toUpperCase();
    const unitSystem = (req.query.unitSystem || 'metric').toString().trim();
    const doFetch = String(req.query.fetch || 'false').toLowerCase() === 'true';
    if (!placeRaw) return res.status(400).json({ error: 'Query param "place" is required' });

    // --- 1) Geocode, but force Quebec/Canada and reject centroidy results ---
    let geo = null;

    // Try a couple of query shapes to help Nominatim
    const attempts = [
      `${placeRaw}, Quebec, Canada`,
      `${placeRaw}, QC, Canada`,
      placeRaw
    ];

    for (const q of attempts) {
      try {
        const r = await geocoder.geocode({
          address: q,
          limit: 1
          // node-geocoder abstracts provider params; we bias with string form above
        });
        if (r && r.length) {
          const { latitude: lat, longitude: lon, stateCode } = r[0];
          if (!looksLikeCanadaCentroid(lat, lon) && isInQuebec(lat, lon)) {
            geo = { lat, lon, stateCode };
            break;
          }
        }
      } catch (_) {
        // ignore and try next attempt
      }
    }

    // If geocoder failed or got outside QC, fall back later to text match
    const inferredProvince = province || (geo?.stateCode ? geo.stateCode.toUpperCase() : 'QC');

    // --- 2) Choose candidate stations from in-memory index (province filter if provided/inferred) ---
    let candidates = STATION_INDEX;
    if (inferredProvince) candidates = candidates.filter(s => s.province === inferredProvince);
    console.log('Candidates:', candidates.map(s => ({
      id: s.stationId,
      name: s.name,
      province: s.province,
      lat: s.lat,
      lon: s.lon
    })));
    let best = null, bestD = Infinity;
    // helper: check if a station's file has usable sub-daily durations

    if (geo && Number.isFinite(geo.lat) && Number.isFinite(geo.lon)) {
      // Nearest by coordinates (only stations with coords)
      for (const s of candidates) {
        if (!Number.isFinite(s.lat) || !Number.isFinite(s.lon)) continue;
        const d = haversine(geo.lat, geo.lon, s.lat, s.lon);
        if (d < bestD && fileHasUsableDurations(s.file)) {
          bestD = d; best = s;
        }
      }
    }

    // --- 3) Fallback: if no coords on stations or geocode failed, do text match on names ---
    if (!best) {
      const q = placeRaw.toLowerCase();
      const tokens = q.replace(/[^a-z0-9]+/g, ' ').split(' ').filter(Boolean);
      const scored = candidates.map(s => {
        const nm = (s.name || '').toLowerCase();
        const fn = (s.file || '').toLowerCase();
        let score = 0;
        for (const t of tokens) {
          if (nm.includes(t)) score += 2;
          if (fn.includes(t)) score += 1;
        }
        // optional nudge: Saguenay → Bagotville
        if (/saguenay/.test(q) && (/bagotville/.test(nm) || /bagotville/.test(fn))) score += 3;
        return { s, score };
        }).filter(x => x.score > 0 && fileHasUsableDurations(x.s.file))
        .sort((a,b) => b.score - a.score);

      if (scored.length) { best = scored[0].s; bestD = NaN; }
    }


    if (!best) {
      return res.status(404).json({
        error: 'No station found near place',
        place: placeRaw,
        province: inferredProvince || null,
        hint: 'Add lat/lon for QC stations in stations_lookup JSON or ensure /data has matching TXT files.'
      });
    }

    // If fetch=false → return match only
    if (!doFetch) {
      return res.json({
        place: {
          query: placeRaw,
          lat: geo?.lat ?? null,
          lon: geo?.lon ?? null,
          inferredProvince: inferredProvince || null
        },
        nearest: {
          ...best,
          ...(Number.isFinite(bestD) ? { distance_km: Number(bestD.toFixed(2)) } : {})
        },
        hint: 'Append &fetch=true to also parse IDF data.'
      });
    }

    // --- 4) fetch=true → parse station file (reuse your cache + parser) ---
    const dataDir = getDataDir();
    const files = fs.readdirSync(dataDir);
    const chosenFile = best.file && files.includes(best.file)
      ? best.file
      : files.find(f => f.toLowerCase().endsWith('.txt') && f.toLowerCase().includes(String(best.stationId).toLowerCase()));

    if (!chosenFile) {
      return res.status(404).json({ error: 'Data file not found for chosen station', station: best });
    }

    // Cache check
    const cacheKey = `${chosenFile}|${(unitSystem || '').toLowerCase()}`;
    const cached = cacheGet(cacheKey);
    if (cached) {
      return res.json({
        place: {
          query: placeRaw,
          lat: geo?.lat ?? null,
          lon: geo?.lon ?? null,
          inferredProvince: inferredProvince || null
        },
        nearest: {
          ...best,
          ...(Number.isFinite(bestD) ? { distance_km: Number(bestD.toFixed(2)) } : {})
        },
        file: chosenFile,
        idf: cached.idf,
        units: cached.units
      });
    }

    // Parse (same logic you use in POST /api/idf)
    const txtPath = path.join(dataDir, chosenFile);
    const content = fs.readFileSync(txtPath, 'utf-8');
    const lines = content.replace(/\r/g, '').split('\n').map((l) => l.trim());

    const startIdx = lines.findIndex((l) =>
      /(table\s*2a|tableau\s*2a|rainfall amounts|pr[eé]cipitation)/i.test(l)
    );
    if (startIdx === -1) {
      return res.status(500).json({ error: 'Rainfall amounts table not found', file: chosenFile });
    }
    let endIdx = lines.slice(startIdx + 1).findIndex((l) => /^table\b/i.test(l));
    endIdx = endIdx === -1 ? lines.length : startIdx + 1 + endIdx;
    const block = lines.slice(startIdx + 1, endIdx);

    const idfDepths = {}; const idfIntensities = {};
    RP_LABELS.forEach((rp) => { idfDepths[rp] = {}; idfIntensities[rp] = {}; });

    const durRows = [];
    for (const row of block) {
      const v = nums(row);
      if (v.length >= 7) {
        const durMin = normalizeDurationToMinutes(v[0]);
        if (durMin != null) { v[0] = durMin; durRows.push(v); }
      }
      if (durRows.length === DURATIONS_MIN.length) break;
    }

    if (durRows.length) {
      for (const v of durRows) {
        const dur = v[0];
        for (let c = 0; c < RP_LABELS.length; c++) {
          const amount = v[c + 1];
          if (!Number.isFinite(amount)) continue;
          idfDepths[RP_LABELS[c]][`${dur} min`] = Number(amount.toFixed(2));
          let intensity = (amount * 60) / dur;
          if (lc(unitSystem) === 'imperial') intensity *= 0.0393701;
          idfIntensities[RP_LABELS[c]][`${dur} min`] = Number(intensity.toFixed(2));
        }
      }
    } else {
      const numericRows = block
        .map((row) => nums(row))
        .filter((v) => v.length >= 9)
        .slice(0, RP_LABELS.length);
      let rpIdx = 0;
      for (const v of numericRows) {
        if (rpIdx >= RP_LABELS.length) break;
        const rp = RP_LABELS[rpIdx++];
        DURATIONS_MIN.forEach((dur, i) => {
          const amount = v[i];
          if (!Number.isFinite(amount)) return;
          idfDepths[rp][`${dur} min`] = Number(amount.toFixed(2));
          let intensity = (amount * 60) / dur;
          if (lc(unitSystem) === 'imperial') intensity *= 0.0393701;
          idfIntensities[rp][`${dur} min`] = Number(intensity.toFixed(2));
        });
      }
    }

    const units = { depths: 'mm', intensities: (unitSystem || '').toLowerCase() === 'imperial' ? 'in/hr' : 'mm/hr' };
    cacheSet(cacheKey, { idf: { depths_mm: idfDepths, intensities: idfIntensities }, units });
    // --- Build safe durations + series exactly like /curves ---
    const durations = Array.from(new Set(
      Object.values(idfDepths)
        .flatMap(o => Object.keys(o))
        .map(k => parseInt(String(k).replace(/[^\d]/g, ''), 10))
        .filter(n => Number.isFinite(n))
    )).sort((a, b) => a - b);

    const series = Object.entries(idfIntensities).map(([rp, vals]) => ({
      name: rp,
      points: durations.map(d => ({ x: d, y: vals[`${d} min`] ?? null }))
    }));
    return res.json({
      place: {
        query: placeRaw,
        lat: geo?.lat ?? null,
        lon: geo?.lon ?? null,
        inferredProvince: inferredProvince || null
      },
      nearest: {
        ...best,
        ...(Number.isFinite(bestD) ? { distance_km: Number(bestD.toFixed(2)) } : {})
      },
      file: chosenFile,
      durations,
      series,
      units,
      idf: { depths_mm: idfDepths, intensities: idfIntensities }
     });
    
  } catch (err) {
    console.error('Error in GET /api/idf/by-place:', err);
    return res.status(500).json({ error: 'Failed to resolve place', detail: err.message });
  }
});
router.get('/ping', (req, res) => res.json({ ok: true, route: 'idf' }));
// GET /api/idf/debug/preview?file=<exact filename in /data>
router.get('/debug/preview', (req, res) => {
  try {
    const file = String(req.query.file || '').trim();
    if (!file) return res.status(400).json({ error: 'Provide ?file=<filename.txt>' });

    const dataDir = getDataDir();
    const txtPath = path.join(dataDir, file);
    if (!fs.existsSync(txtPath)) return res.status(404).json({ error: 'File not found', txtPath });

    const content = fs.readFileSync(txtPath, 'utf-8');
    const lines = content.replace(/\r/g, '').split('\n').map(l => l.trim());

    // find Table 2A block
    const startIdx = lines.findIndex(l => /(table\s*2a|tableau\s*2a)/i.test(l));
    if (startIdx === -1) return res.status(500).json({ error: 'Table 2A not found' });

    let headerIdx = -1;
    for (let i = startIdx; i < Math.min(lines.length, startIdx + 30); i++) {
      const t = lines[i].toLowerCase();
      if (
        /5[^0-9]+10[^0-9]+15[^0-9]+30[^0-9]+60/.test(t) ||
        /(5\s*min).*(10\s*min).*(15\s*min)/.test(t) ||
        /(1\s*h|1\s*hr).*(2\s*h|2\s*hr)/.test(t)
      ) { headerIdx = i; break; }
    }
    if (headerIdx === -1) headerIdx = startIdx + 1;

    const endIdxRel = lines.slice(headerIdx + 1).findIndex(l => /^table\b/i.test(l));
    const endIdx = endIdxRel === -1 ? lines.length : headerIdx + 1 + endIdxRel;

    const header = lines[headerIdx];
    const body = lines.slice(headerIdx + 1, endIdx).filter(Boolean).slice(0, 20);

    // quick token dump (first 6 RP rows)
    const rows = body.map(r => r.split(/\s+/).filter(Boolean).slice(0, 15));

    return res.json({
      file,
      aroundTitle: lines.slice(Math.max(0, startIdx - 2), Math.min(lines.length, startIdx + 3)),
      header,
      firstRows: rows
    });
  } catch (e) {
    return res.status(500).json({ error: 'Preview failed', detail: e.message });
  }
});

// GET /api/idf/curves?stationId=7060400&unitSystem=metric
// or     /api/idf/curves?place=Saguenay, QC&province=QC&unitSystem=metric
router.get('/curves', async (req, res) => {
  try {
    const unitSystem = (req.query.unitSystem || 'metric').toString().trim().toLowerCase();
    const dataDir = getDataDir();

    // Resolve file either by stationId or by place
    let file = null;

    if (req.query.stationId) {
      const idL = String(req.query.stationId).toLowerCase();
      const files = fs.readdirSync(dataDir);
      file = files.find(f => f.toLowerCase().endsWith('.txt') && f.toLowerCase().includes(idL));
      if (!file) return res.status(404).json({ error: 'No file for that stationId' });
    } else if (req.query.place) {
      // reuse your by-place chooser but without parsing
      const placeUrl = `/api/idf/by-place?place=${encodeURIComponent(req.query.place)}`
        + (req.query.province ? `&province=${encodeURIComponent(req.query.province)}` : '');
      // quick local call replacement: pick best from STATION_INDEX by text
      const q = String(req.query.place).toLowerCase();
      const tokens = q.replace(/[^a-z0-9]+/g, ' ').split(' ').filter(Boolean);
      const prov = (req.query.province || '').toString().trim().toUpperCase();
      let candidates = STATION_INDEX;
      if (prov) candidates = candidates.filter(s => s.province === prov);
      const scored = candidates.map(s => {
        const nm = (s.name || '').toLowerCase();
        const fn = (s.file || '').toLowerCase();
        let score = 0;
        for (const t of tokens) { if (nm.includes(t)) score += 2; if (fn.includes(t)) score += 1; }
        return { s, score };
      }).filter(x => x.score > 0).sort((a,b) => b.score - a.score);
      if (!scored.length) return res.status(404).json({ error: 'No station match for that place' });
      file = scored[0].s.file;
    } else {
      return res.status(400).json({ error: 'Provide stationId or place' });
    }

    // Parse via your helper
    const cacheKey = `${file}|${unitSystem}`;
    const cached = cacheGet(cacheKey);
    let depths_mm, intensities, units;

    if (cached) {
      depths_mm = cached.idf.depths_mm;
      intensities = cached.idf.intensities;
      units = cached.units;
    } else {
      // inline minimal parse (reuse same code you already use)
      const txtPath = path.join(dataDir, file);
      const content = fs.readFileSync(txtPath, 'utf-8');
      const lines = content.replace(/\r/g, '').split('\n').map(l => l.trim());
      const startIdx = lines.findIndex(l => /(table\s*2a|tableau\s*2a|rainfall amounts|pr[eé]cipitation)/i.test(l));
      if (startIdx === -1) return res.status(500).json({ error: 'Table 2A not found', file });

      let headerIdx = -1;
      for (let i = startIdx; i < Math.min(lines.length, startIdx + 30); i++) {
        const t = lines[i].toLowerCase();
        if (/5[^0-9]+10[^0-9]+15[^0-9]+30[^0-9]+60/.test(t) ||
            /(5\s*min).*(10\s*min).*(15\s*min)/.test(t) ||
            /(1\s*h|1\s*hr).*(2\s*h|2\s*hr)/.test(t)) { headerIdx = i; break; }
      }
      if (headerIdx === -1) headerIdx = startIdx + 1;

      const endIdxRel = lines.slice(headerIdx + 1).findIndex(l => /^table\b/i.test(l));
      const endIdx = endIdxRel === -1 ? lines.length : headerIdx + 1 + endIdxRel;
      const body = lines.slice(headerIdx + 1, endIdx).filter(Boolean);

      const RP_MAP = new Map([[2,'2yr'],[5,'5yr'],[10,'10yr'],[25,'25yr'],[50,'50yr'],[100,'100yr']]);
      depths_mm = {}; intensities = {}; for (const v of RP_MAP.values()) { depths_mm[v] = {}; intensities[v] = {}; }

      // derive duration columns from header tokens
   
      // Parse duration tokens from the header row (e.g., "5", "10 min", "1 h", "24 h", "1 day")
      
      // use the shared parseDurTok defined at top

      const headerTokens = lines[headerIdx].split(/\s+/);
      let durationCols = [];
      for (let ci = 0; ci < headerTokens.length; ci++) {
        const d = parseDurTok(headerTokens[ci]);
        if (d != null) durationCols.push({ colIndex: ci, minutes: d });
      }
      if (durationCols.length < 3) {
        // ===== Row‑oriented Table 2A fallback =====
        const RP_LIST = [2, 5, 10, 25, 50, 100];
        for (const raw of body) {
          if (!raw) continue;
          const toks = raw.split(/\s+/).filter(Boolean);
          if (toks.length < 3) continue;

          // Combine first two tokens if unit is separated (e.g. "24" "h")
          const firstTwo = toks[0] + (toks[1] ? ' ' + toks[1] : '');
          const durMin = parseDurTok(firstTwo);
          if (!durMin) continue;

          let startValsIdx = 1;
          if (/(min|m|h|hr|hrs|hour|hours|d|day|days)/i.test(toks[1] || '')) {
            startValsIdx = 2;
          }
          const vals = toks.slice(startValsIdx).map(Number);

          for (let i = 0; i < RP_LIST.length; i++) {
            const rpName = `${RP_LIST[i]}yr`;
            const val = vals[i];
            if (!Number.isFinite(val)) continue;
            depths_mm[rpName][`${durMin} min`] = Number(val.toFixed(2));
            let inten = (val * 60) / durMin;
            if (unitSystem === 'imperial') inten *= 0.0393701;
            intensities[rpName][`${durMin} min`] = Number(inten.toFixed(2));
          }
        }
      } else {
        // ===== Usual header‑based parse =====
        console.log('Header row:', lines[headerIdx]);
        console.log('Parsed duration cols:', durationCols);
        for (const row of body) {
          const toks = row.split(/\s+/);
          const rpNum = Number(toks[0]);
          if (!RP_MAP.has(rpNum)) continue;
          const rp = RP_MAP.get(rpNum);
          for (const { colIndex, minutes } of durationCols) {
            const val = Number(toks[colIndex]);
            if (!Number.isFinite(val)) continue;
            depths_mm[rp][`${minutes} min`] = Number(val.toFixed(2));
            let inten = (val * 60) / minutes;
            if (unitSystem === 'imperial') inten *= 0.0393701;
            intensities[rp][`${minutes} min`] = Number(inten.toFixed(2));
          }
        }
      } 

      const nonEmpty = Object.values(depths_mm).some(o => Object.keys(o).length);
      if (!nonEmpty) return res.status(500).json({ error: 'Could not parse Table 2A', file, preview: body.slice(0,15) });

      units = { depths: 'mm', intensities: unitSystem === 'imperial' ? 'in/hr' : 'mm/hr' };
      cacheSet(cacheKey, { idf: { depths_mm, intensities }, units });
    }

    // Shape for chart libraries: durations array + series per RP
      
    const durations = Array.from(new Set(
      Object.values(depths_mm)
        .flatMap(o => Object.keys(o))
        .map(k => parseInt(String(k).replace(/[^\d]/g, ''), 10))
        .filter(n => Number.isFinite(n))
    )).sort((a,b) => a - b); 
    const series = Object.entries(intensities).map(([rp, vals]) => ({
      name: rp,
      points: durations.map(d => ({ x: d, y: vals[`${d} min`] ?? null }))
    }));

    return res.json({ file, durations, series, units, depths_mm, intensities });
  } catch (e) {
    console.error('Error in GET /api/idf/curves:', e);
    return res.status(500).json({ error: 'Failed to build curves', detail: e.message });
  }
});

module.exports = router;
