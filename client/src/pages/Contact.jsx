// File: client/src/pages/Contact.jsx

import React, { useState } from 'react';
import axios from 'axios';

function Contact() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    message: '',
    sendCopy: false,
    honeypot: ''  // Spam bot trap
  });

  const [status, setStatus] = useState('');

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prevData) => ({
      ...prevData,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Honeypot protection: if filled, likely a bot
    if (formData.honeypot) {
      setStatus('Spam detected. Submission blocked.');
      return;
    }

    try {
      const res = await axios.post('http://localhost:5000/api/contact', {
        name: formData.name,
        email: formData.email,
        message: formData.message,
        sendCopy: formData.sendCopy
      });

      if (res.data.success) {
        setStatus('✅ Message sent successfully!');
        setFormData({
          name: '',
          email: '',
          message: '',
          sendCopy: false,
          honeypot: ''
        });
      } else {
        setStatus('❌ Something went wrong. Try again.');
      }
    } catch (err) {
      console.error(err);
      setStatus('❌ Error sending message.');
    }
  };

  return (
    <div className="max-w-xl mx-auto mt-10 p-6 bg-white rounded shadow">
      <h2 className="text-2xl font-bold mb-4">Contact Us</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Honeypot field (hidden from real users) */}
        <input
          type="text"
          name="honeypot"
          value={formData.honeypot}
          onChange={handleChange}
          style={{ display: 'none' }}
          autoComplete="off"
        />

        <input
          type="text"
          name="name"
          placeholder="Your Name"
          className="w-full p-2 border rounded"
          value={formData.name}
          onChange={handleChange}
          required
        />

        <input
          type="email"
          name="email"
          placeholder="Your Email"
          className="w-full p-2 border rounded"
          value={formData.email}
          onChange={handleChange}
          required
        />

        <textarea
          name="message"
          placeholder="Your Message"
          className="w-full p-2 border rounded"
          rows="5"
          value={formData.message}
          onChange={handleChange}
          required
        />

        <label className="block">
          <input
            type="checkbox"
            name="sendCopy"
            checked={formData.sendCopy}
            onChange={handleChange}
            className="mr-2"
          />
          Send me a copy
        </label>

        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Send
        </button>
      </form>

      {status && (
        <p className="mt-4 text-sm text-center text-green-600">
          {status}
        </p>
      )}
    </div>
  );
}

export default Contact;

