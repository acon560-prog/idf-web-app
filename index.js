require('dotenv').config();

const express = require('express');
const cors = require('cors');
const { MongoClient } = require('mongodb');
const path = require('path');

const contactRoute = require('./routes/contact');
const enrichRoute = require('./routes/enrich');
const projectRoute = require('./routes/project');
const reportRoute = require('./routes/report');
const idfRoute = require('./routes/idf');

const app = express();
app.use(cors());
app.use(express.json());

// === 1. MongoDB Setup ===
const uri = process.env.MONGO_URI;
const client = new MongoClient(uri, {
  tls: true,                       // Ensure TLS for Render
  serverSelectionTimeoutMS: 5000,  // Faster fail on bad connection
});

async function startServer() {
  try {
    await client.connect();
    const db = client.db('contactDB');
    app.locals.db = db;
    console.log('✅ Connected to MongoDB Atlas');

    // Middleware to attach DB to every request
    app.use((req, res, next) => {
      req.db = db;
      next();
    });

    // === 2. API Routes ===
    app.use('/api/idf', idfRoute);
    app.use('/api/contact', contactRoute);
    app.use('/api/enrich-location', enrichRoute);
    app.use('/api/project', projectRoute);
    app.use('/api/report', reportRoute);

    // === 3. Serve React Frontend (Production) ===
    app.use(express.static(path.join(__dirname, 'client/build')));

    // Catch-all route for React (Express 4 compatible)
    app.get('/*', (req, res) => {
      res.sendFile(path.join(__dirname, 'client/build', 'index.html'));
    });

    // === 4. Start Server ===
    const PORT = process.env.PORT || 3000;
    app.listen(PORT, () => {
      console.log(`🚀 Server running on port ${PORT}`);
    });
  } catch (err) {
    console.error('❌ Failed to connect to MongoDB or start server:', err);
    process.exit(1); // Exit if DB or server fails
  }
}

startServer();
