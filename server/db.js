const { MongoClient } = require('mongodb');
require('dotenv').config({ path: __dirname + '/../.env' });

const uri = process.env.MONGO_URI;
console.log('Loaded MONGO_URI:', uri); // for debugging
if (!uri) {
  console.log('Loaded MONGO_URI:', uri); // Debug line
  throw new Error('❌ MONGO_URI is missing from environment variables.');
}

const client = new MongoClient(uri, {
  useNewUrlParser: true,
  useUnifiedTopology: true
});

let dbInstance = null;

async function connectDB() {
  if (!dbInstance) {
    try {
      await client.connect();
      dbInstance = client.db(); // Defaults to DB in URI
      console.log('✅ MongoDB connected');
    } catch (err) {
      console.error('❌ MongoDB connection failed:', err);
      throw err;
    }
  }
  return dbInstance;
}

module.exports = connectDB();
