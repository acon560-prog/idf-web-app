const express = require('express');
const router = express.Router();
const PDFDocument = require('pdfkit');
const fs = require('fs');
const path = require('path');
const { MongoClient, ObjectId } = require('mongodb');
require('dotenv').config();

const mongoUri = process.env.MONGO_URI;
const client = new MongoClient(mongoUri);

// 📄 Generate a PDF report for a project
router.post('/', async (req, res) => {
  console.log('📥 Incoming /api/report request...');
  const { projectId } = req.body;

  if (!projectId) {
    return res.status(400).json({ error: 'Missing projectId in request body' });
  }

  try {
    await client.connect();
    const db = client.db('civispec');
    const collection = db.collection('projects');

    // 🔹 Fetch the project from DB
    const project = await collection.findOne({ _id: new ObjectId(projectId) });

    if (!project) {
      return res.status(404).json({ error: 'Project not found' });
    }

    // 🔹 Create PDF file path
    const reportsDir = path.join(__dirname, '../reports');
    if (!fs.existsSync(reportsDir)) fs.mkdirSync(reportsDir);

    const pdfPath = path.join(reportsDir, `project_${projectId}.pdf`);

    // 🔹 Generate PDF
    const doc = new PDFDocument({ margin: 50 });
    doc.pipe(fs.createWriteStream(pdfPath));

    // Header
    doc.fontSize(20).text('CiviSpec Project Report', { align: 'center' });
    doc.moveDown();
    doc.fontSize(12).text(`Project ID: ${projectId}`);
    doc.text(`Date: ${new Date().toLocaleString()}`);
    doc.moveDown();

    // Project Summary
    doc.fontSize(14).text('Project Details:', { underline: true });
    doc.moveDown();
    Object.entries(project).forEach(([key, value]) => {
      if (key !== '_id') doc.fontSize(12).text(`${key}: ${JSON.stringify(value)}`);
    });

    doc.end();

    console.log('✅ PDF report generated at:', pdfPath);

    res.status(200).json({
      message: 'Report generated successfully',
      pdfPath: `/reports/project_${projectId}.pdf`
    });

  } catch (err) {
    console.error('❌ Error generating report:', err.message);
    res.status(500).json({ error: 'Failed to generate report' });
  } finally {
    await client.close();
  }
});

module.exports = router;
