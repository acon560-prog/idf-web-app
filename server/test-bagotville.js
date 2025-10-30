// test-bagotville.js

const path = require('path');
const slug = require('slug'); // make sure 'slug' package is installed
// Adjust this path to point to your stations_lookup.json location
const stations = require(path.join(__dirname, 'utils/stations_lookup_demo_fixed.json'));

// Simulate the entry name from your .txt file
const entryName = '706 BAGOTVILLE A txt';

// Clean and split the entry name into words
const entrySlug = slug(entryName)
  .replace(/\b\d+\b/g, '')  // remove numbers
  .replace(/\btxt\b/g, '')  // remove literal "txt"
  .trim();

const entryWords = entrySlug.split(/[-\s]+/).filter(Boolean);

// Try to find a matching meta station from the JSON
const match = stations.find(meta => {
  const metaSlug = slug(meta.name)
    .replace(/\b\d+\b/g, '')
    .trim();
  const metaWords = metaSlug.split(/[-\s]+/).filter(Boolean);

  return entryWords.some(w =>
    metaWords.some(mw => mw.toLowerCase() === w.toLowerCase())
  );
});

console.log('entrySlug:', entrySlug);
console.log('entryWords:', entryWords);
console.log('Match found:', match);
