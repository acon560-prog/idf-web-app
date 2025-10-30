// File: server/routes/report.js
const express = require('express');
const PDFDocument = require('pdfkit');
const router = express.Router();

router.post('/', (req, res) => {
  const { form, enrichment } = req.body;

  // 🧾 Markdown summary
  const markdown = `## Compliance Summary

**Location**: ${form.location}  
**Project Type**: ${form.projectType}  
**Foundation Depth**: ${form.foundationDepth} m  
**Height**: ${form.height}

---

### Enrichment Data:
- 10-year rainfall: ${enrichment?.rainfall_10yr} mm
- Annual rainfall: ${enrichment?.annual_rainfall} mm
- Frost depth: ${enrichment?.frost_depth} m
- Snow load zone: ${enrichment?.snow_load_zone}
- Setback min: ${enrichment?.setback_min} m

---

### Compliance Checks:
${parseFloat(form.foundationDepth) < enrichment?.frost_depth
    ? '❌ Foundation below frost depth'
    : '✅ Foundation depth is sufficient'}

${
  form.drainage === 'swale' && enrichment?.rainfall_10yr > 80
    ? '⚠️ Swale might not be suitable for high rainfall.'
    : '✅ Drainage type acceptable'
}
`;

  // 🖨️ Generate PDF
  const doc = new PDFDocument();
  let buffers = [];
  doc.on('data', buffers.push.bind(buffers));
  doc.on('end', () => {
    const pdfData = Buffer.concat(buffers);
    res
      .writeHead(200, {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'attachment;filename=report.pdf',
        'Content-Length': pdfData.length,
      })
      .end(pdfData);
  });
  console.log('📝 Generating report for:', form);
  doc.fontSize(16).text('Compliance Report', { underline: true });
  doc.moveDown();
  doc.fontSize(12).text(markdown);
  doc.end();
});

module.exports = router;
