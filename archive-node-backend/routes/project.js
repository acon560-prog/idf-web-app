const express = require('express');
const router = express.Router();
const { MongoClient } = require('mongodb');
require('dotenv').config();

const mongoUri = process.env.MONGO_URI;
const client = new MongoClient(mongoUri);

router.post('/', async (req, res) => {
  console.log('📥 Incoming /api/project request...');
  const projectData = req.body;

  try {
    await client.connect();
    const db = client.db('civispec');
    const collection = db.collection('projects');

    // Insert project data into MongoDB
    const result = await collection.insertOne({
      ...projectData,
      createdAt: new Date()
    });

    console.log('✅ Project saved to DB:', result.insertedId);
    res.status(201).json({
      message: 'Project saved successfully',
      projectId: result.insertedId
    });
  } catch (err) {
    console.error('❌ Error saving project:', err.message);
    res.status(500).json({ error: 'Failed to save project data' });
  } finally {
    await client.close();
  }
});

module.exports = router;
