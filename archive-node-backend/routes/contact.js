const express = require('express');
const nodemailer = require('nodemailer');
const router = express.Router();

router.post('/', async (req, res) => {
  console.log('📩 /api/contact POST hit');
  console.log('📩 Received body:', req.body);

  const { name, email, message } = req.body;
    try {
    const db = req.app.locals.db;
    await db.collection('contacts').insertOne({
      name,
      email,
      message,
      submittedAt: new Date()
    });

    res.status(200).json({ success: true, message: 'Contact saved to database' });
  } catch (err) {
    console.error('❌ Failed to save contact:', err);
    res.status(500).json({ success: false, message: 'Database error' });
  }

  if (!name || !email || !message) {
    return res.status(400).json({ success: false, message: 'All fields are required' });
  }

  try {
    // Create a transporter using Gmail (or any SMTP)
    const transporter = nodemailer.createTransport({
      service: 'gmail',
      auth: {
        user: process.env.EMAIL_USER,
        pass: process.env.EMAIL_PASS,
      },
    });

    // Email to site owner
    await transporter.sendMail({
      from: `"${name}" <${email}>`,
      to: process.env.EMAIL_USER,
      subject: 'New Contact Form Submission',
      text: `Name: ${name}\nEmail: ${email}\nMessage:\n${message}`,
    });

    // Email copy to sender
    await transporter.sendMail({
      from: `"CiviSpec" <${process.env.EMAIL_USER}>`,
      to: email,
      subject: 'We received your message!',
      text: `Hi ${name},\n\nThank you for contacting us. We will get back to you soon.\n\nYour message:\n${message}`,
    });

    res.json({ success: true, message: 'Message sent successfully!' });
  } catch (err) {
    console.error('❌ Contact form error:', err);
    res.status(500).json({ success: false, message: 'Error sending message' });
  }
});

module.exports = router;
