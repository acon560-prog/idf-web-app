const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');

function fallbackFromCsv(province, city) {
  return new Promise((resolve, reject) => {
    const results = [];
    const filePath = path.join(__dirname, '../data/idf_1991_2020.csv'); // Make sure this exists

    if (!fs.existsSync(filePath)) {
      return reject(new Error('CSV file not found'));
    }

    fs.createReadStream(filePath)
      .pipe(csv())
      .on('data', (row) => {
        if (row.Province?.toLowerCase() === province.toLowerCase()) {
          results.push(row);
        }
      })
      .on('end', () => {
        if (!results.length) {
          return reject(new Error(`No matches found for province: ${province}`));
        }

        const fallback = results.find(row => row.StationName.toLowerCase().includes(city.toLowerCase())) || results[0];

        const extract = (duration, year) => {
          const val = fallback[`${duration}_${year}`];
          return val ? +parseFloat(val).toFixed(1) : null;
        };

        const idf = {
          '5min': { '2yr': extract('5min', 2), '5yr': extract('5min', 5), '10yr': extract('5min', 10), '25yr': extract('5min', 25), '50yr': extract('5min', 50), '100yr': extract('5min', 100) },
          '10min': { '2yr': extract('10min', 2), '5yr': extract('10min', 5), '10yr': extract('10min', 10), '25yr': extract('10min', 25), '50yr': extract('10min', 50), '100yr': extract('10min', 100) },
          '15min': { '2yr': extract('15min', 2), '5yr': extract('15min', 5), '10yr': extract('15min', 10), '25yr': extract('15min', 25), '50yr': extract('15min', 50), '100yr': extract('15min', 100) },
          '30min': { '2yr': extract('30min', 2), '5yr': extract('30min', 5), '10yr': extract('30min', 10), '25yr': extract('30min', 25), '50yr': extract('30min', 50), '100yr': extract('30min', 100) },
          '1h': { '2yr': extract('1h', 2), '5yr': extract('1h', 5), '10yr': extract('1h', 10), '25yr': extract('1h', 25), '50yr': extract('1h', 50), '100yr': extract('1h', 100) },
          '6h': { '2yr': extract('6h', 2), '5yr': extract('6h', 5), '10yr': extract('6h', 10), '25yr': extract('6h', 25), '50yr': extract('6h', 50), '100yr': extract('6h', 100) },
          '12h': { '2yr': extract('12h', 2), '5yr': extract('12h', 5), '10yr': extract('12h', 10), '25yr': extract('12h', 25), '50yr': extract('12h', 50), '100yr': extract('12h', 100) },
          '24h': { '2yr': extract('24h', 2), '5yr': extract('24h', 5), '10yr': extract('24h', 10), '25yr': extract('24h', 25), '50yr': extract('24h', 50), '100yr': extract('24h', 100) }
        };

        resolve({
          idf,
          frost_depth: 1.5,
          rainfall_10yr: extract('1h', 10),
          annual_rainfall: 850,
          snow_load_zone: 'S-1',
          setback_min: 3
        });
      });
  });
}

module.exports = fallbackFromCsv;
