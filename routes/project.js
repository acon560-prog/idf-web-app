const express = require('express');
const router = express.Router();

router.post('/', async (req, res) => {
  console.log('📥 /api/project POST hit');
  console.log('📥 Received project submission:', req.body);  
  const db = req.app.locals.db;
  const { form, enrichment } = req.body;

  console.log('🔍 Received submission:', { form, enrichment });

  if (!db) {
    console.error('❌ MongoDB not connected');
    return res.status(500).json({ success: false, message: 'MongoDB not connected' });
  }

  if (!form || !form.location || !enrichment) {
    console.error('❌ Missing form or enrichment data');
    return res.status(400).json({ success: false, message: 'Missing form or enrichment data' });
  }

  try {
    const result = await db.collection('projects').insertOne({
      form,
      enrichment,
      submittedAt: new Date()
    });

    console.log('✅ Project saved to MongoDB:', result.insertedId);
    res.json({ success: true, id: result.insertedId });
  } catch (err) {
    console.error('❌ Failed to save project:', err.stack || err);
    res.status(500).json({ success: false, message: 'Failed to save project', error: err.message });
  }
});

module.exports = router;
