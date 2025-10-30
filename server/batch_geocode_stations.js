const fs = require('fs');
const path = require('path');
const axios = require('axios');

// Your Geoapify API key here
const GEOAPIFY_API_KEY = 'c95c5d38956546b497bcfa8089453d08';

// Load stations JSON (replace with your actual file path)
const stationsFilePath = path.join(__dirname, '../utils/stations_lookup_demo_fixed.json');
let stations = JSON.parse(fs.readFileSync(stationsFilePath, 'utf8'));
// Add these logs **right after loading stations**
console.log(`Loaded ${stations.length} stations from JSON.`);
// Filter stations missing lat/lon
const missingCoordsStations = stations.filter(s => !s.lat || !s.lon);
// Log how many are missing coordinates
console.log(`${missingCoordsStations.length} stations missing lat/lon.`);

// Exit early if none to do
if (missingCoordsStations.length === 0) {
  console.log('All stations have coordinates. Exiting.');
  process.exit(0);
}

// Prepare addresses as "name, province"
const addresses = missingCoordsStations.map(s => `${s.name}, ${s.province}`);

// Submit batch geocode job
async function submitBatchJob(addresses) {
  const url = `https://api.geoapify.com/v1/batch/geocode/search?apiKey=${GEOAPIFY_API_KEY}`;
  try {
    const response = await axios.post(url, addresses, { headers: { 'Content-Type': 'application/json' } });
    if (response.status === 202) {
      console.log('Batch geocode job submitted successfully.');
      return response.data;  // Contains job id and url
    } else {
      throw new Error(`Unexpected response status: ${response.status}`);
    }
  } catch (err) {
    console.error('Error submitting batch job:', err.message);
    process.exit(1);
  }
}

// Poll batch job for results
async function pollBatchResults(resultUrl, interval = 30000, maxAttempts = 20) {
  console.log('Polling for batch geocode job completion...');
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      const res = await axios.get(resultUrl);
      if (res.data.status === 'finished') {
        console.log('Batch geocode job finished!');
        return res.data.results;
      } else if (res.data.status === 'failed') {
        throw new Error('Batch geocode job failed');
      }
      console.log(`Attempt ${attempt}: job status is "${res.data.status}". Waiting...`);
    } catch (err) {
      console.error('Error polling batch job:', err.message);
    }
    await new Promise(r => setTimeout(r, interval));
  }
  throw new Error('Batch geocode job timed out');
}

// Main run function
(async () => {
  if (addresses.length === 0) {
    console.log('No stations missing lat/lon. Exiting.');
    return;
  }

  try {
    const batchJob = await submitBatchJob(addresses);
    console.log(`Job ID: ${batchJob.id}`);
    console.log(`Job URL: ${batchJob.url}`);

    // Append apiKey to results URL
    const resultsUrl = `${batchJob.url}&apiKey=${GEOAPIFY_API_KEY}`;

    const results = await pollBatchResults(resultsUrl);

    // Update stations with results
    results.forEach((result, idx) => {
      const station = missingCoordsStations[idx];
      if (result && result.lat && result.lon) {
        station.lat = result.lat;
        station.lon = result.lon;
      } else {
        console.warn(`No coords found for station: ${station.name}`);
      }
    });

    // Write updated JSON file
    const outputPath = path.join(__dirname, '../utils/stations_lookup_demo_fixed_updated.json');
    fs.writeFileSync(outputPath, JSON.stringify(stations, null, 2));
    console.log(`Updated stations saved to: ${outputPath}`);
  } catch (err) {
    console.error('Error during batch geocoding process:', err.message);
  }
})();
