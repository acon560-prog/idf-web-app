const express = require('express');
const path = require('path');
const app = express();

// Serve station data as an API endpoint
app.get('/api/stations', (req, res) => {
  res.sendFile(path.join(__dirname, 'master_stations_enriched_validated.json'));
});

// Other routes and app.listen ...
const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});
