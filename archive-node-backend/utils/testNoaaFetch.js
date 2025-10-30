// testNoaaFetch.js
require('dotenv').config({ path: '../.env' });
console.log('TOKEN from env:', process.env.NOAA_API_TOKEN);
const fetchFromNOAACDO = require('./fetchFromNOAACDO');

(async () => {
  const data = await fetchFromNOAACDO('/datasets');
  console.log(data);
})();
