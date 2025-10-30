// index.js
require('dotenv').config();
console.log('GEOCODER_UA present?', !!process.env.GEOCODER_UA);
console.log('GEOCODER_REF present?', !!process.env.GEOCODER_REF);

const express = require('express');
const helmet = require('helmet');
const morgan = require('morgan');
const cors = require('cors');
const { MongoClient } = require('mongodb');

const app = express();

// --- Basics & Security ---
app.set('trust proxy', 1);
app.use(helmet());
app.use(express.json({ limit: '2mb' }));       // avoid accidental giant payloads
app.use(express.urlencoded({ extended: true }));
app.use(morgan(process.env.NODE_ENV === 'production' ? 'combined' : 'dev'));

// --- CORS (allow your frontend) ---
const allowedOrigin = process.env.FRONTEND_ORIGIN || '*';
app.use(cors({ origin: allowedOrigin, credentials: true }));

// --- Routes ---
const contactRoute = require('./routes/contact');
const reportRoute = require('./routes/report');
const projectRoute = require('./routes/project');
const enrichRoute = require('./routes/enrich');
const idfRoute = require('./routes/idf');

app.use('/api/contact', contactRoute);
app.use('/api/report', reportRoute);
app.use('/api/project', projectRoute);
app.use('/api/enrich-location', enrichRoute);
app.use('/api/idf', idfRoute);

// --- Simple root + health/version ---
app.get('/', (_req, res) => res.send('Hello, world!'));
app.get('/health', (_req, res) => res.status(200).json({ status: 'ok' }));
app.get('/version', (_req, res) => res.json({ version: process.env.APP_VERSION || '0.1.0' }));

// === MongoDB Setup ===
const uri = process.env.MONGO_URI;
if (!uri) {
  console.error('❌ MONGO_URI is not set in .env');
  process.exit(1);
}
const client = new MongoClient(uri, {
  tls: true,
  serverSelectionTimeoutMS: 5000,
});

let server; // to close gracefully

async function startServer() {
  try {
    await client.connect();
    const dbName = process.env.MONGO_DB_NAME || 'contactDB';
    const db = client.db(dbName);
    app.locals.db = db;
    console.log(`✅ Connected to MongoDB Atlas (db: ${dbName})`);

    // 404 handler for unknown routes (after all routes)
    app.use((req, res, _next) => {
      res.status(404).json({ error: 'Not Found', path: req.originalUrl });
    });

    // Centralized error handler (last)
    // If any route calls next(err), it lands here.
    // eslint-disable-next-line no-unused-vars
    app.use((err, _req, res, _next) => {
      console.error('🔥 Unhandled error:', err);
      const status = err.status || 500;
      res.status(status).json({
        error: err.message || 'Internal Server Error',
      });
    });

    const PORT = process.env.PORT || 3000;
    server = app.listen(PORT, () => {
      console.log(`🚀 Server running on port ${PORT}`);
    });

    // Graceful shutdown
    const shutdown = async (signal) => {
      try {
        console.log(`\n🛑 ${signal} received: closing server...`);
        if (server) await new Promise((resolve) => server.close(resolve));
        await client.close();
        console.log('👋 Server and DB connections closed. Bye!');
        process.exit(0);
      } catch (e) {
        console.error('Error during shutdown:', e);
        process.exit(1);
      }
    };

    process.on('SIGINT', () => shutdown('SIGINT'));
    process.on('SIGTERM', () => shutdown('SIGTERM'));

  } catch (err) {
    console.error('❌ Failed to connect to MongoDB or start server:', err);
    process.exit(1);
  }
}

startServer();

// Export for testing if needed
module.exports = app;
