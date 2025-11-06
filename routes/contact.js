const express = require('express');
const nodemailer = require('nodemailer');
const fs = require('fs');
const jwt = require('jsonwebtoken');

const router = express.Router();

const JWT_SECRET = process.env.JWT_SECRET_KEY || 'change-me';
const ADMIN_EMAIL = (process.env.ADMIN_EMAIL || '').trim().toLowerCase();

function extractBearerToken(req) {
  const authHeader = req.headers.authorization || '';
  if (authHeader.startsWith('Bearer ')) {
    return authHeader.slice(7);
  }
  return null;
}

function requireAdmin(req, res, next) {
  try {
    const token = extractBearerToken(req);
    if (!token) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    const payload = jwt.verify(token, JWT_SECRET);
    const role = payload?.role;
    const email = (payload?.email || '').toLowerCase();
    const isAdmin = role === 'admin' || (!!ADMIN_EMAIL && email === ADMIN_EMAIL);

    if (!isAdmin) {
      return res.status(403).json({ error: 'Administrator access required' });
    }

    req.user = { id: payload?.sub, email, role: role || (isAdmin ? 'admin' : undefined) };
    next();
  } catch (err) {
    console.error('JWT verification failed for admin route:', err);
    return res.status(401).json({ error: 'Invalid or expired token' });
  }
}

router.post('/', async (req, res) => {
  const { name, email, message, sendCopy, honeypot } = req.body;

  if (honeypot && honeypot.trim() !== '') {
    return res.status(400).json({ success: false, message: 'Spam detected' });
  }

  if (!name || !email || !message) {
    return res.status(400).json({ success: false, message: 'All fields are required' });
  }

  // ✅ Log to file
  const logEntry = `[${new Date().toISOString()}] ${name} <${email}>: ${message}\n`;
  fs.appendFile('submissions.log', logEntry, err => {
    if (err) console.error('Logging error:', err);
  });

  // ✅ Save to MongoDB
  try {
    const db = req.app.locals.db;
    if (!db) throw new Error('MongoDB not connected');
    await db.collection('submissions').insertOne({
      name,
      email,
      message,
      date: new Date()
    });
    console.log('📥 Saved to MongoDB');
  } catch (err) {
    console.error('❌ MongoDB error:', err);
  }

  // ✅ Email logic
  const transporter = nodemailer.createTransport({
    service: 'gmail',
    auth: {
      user: process.env.EMAIL_USER,
      pass: process.env.EMAIL_PASS
    }
  });

  const adminEmail = {
    from: process.env.EMAIL_USER,
    to: process.env.EMAIL_USER,
    subject: 'New Contact Form Submission',
    text: `Name: ${name}\nEmail: ${email}\nMessage:\n${message}`
  };

  const userEmail = {
    from: process.env.EMAIL_USER,
    to: email,
    subject: 'We received your message!',
    text: `Hi ${name},\n\nThanks for contacting us. Here's what you sent:\n\n"${message}"\n\nWe'll get back to you soon.\n\n- Civil Engineering Practice`
  };

  try {
    await transporter.sendMail(adminEmail);
    if (sendCopy) {
      await transporter.sendMail(userEmail);
    }
    return res.status(200).json({ success: true });
  } catch (error) {
    console.error('Email send error:', error);
    return res.status(500).json({ success: false, message: 'Failed to send message' });
  }
});

// GET route for Admin Dashboard
router.get('/', requireAdmin, async (req, res) => {
  try {
    const db = req.app.locals.db;
    if (!db) throw new Error('MongoDB not connected');
    const submissions = await db.collection('submissions').find().sort({ date: -1 }).toArray();
    res.json(submissions);
  } catch (err) {
    console.error('❌ Failed to fetch submissions:', err);
    res.status(500).json({ error: 'Failed to fetch submissions' });
  }
});

module.exports = router;
