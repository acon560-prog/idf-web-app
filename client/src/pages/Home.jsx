// File: src/Home.jsx
import React from 'react';
import { motion } from 'framer-motion';

function Home() {
  return (
    <motion.div
      className="p-4"
      initial={{ opacity: 0, y: 50 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.8 }}
    >
      <h2 className="text-2xl font-bold">Welcome to CiviSpec</h2>
      <p className="mt-4">
        We provide structural design, permit drawings, grading plans, and more — tailored for residential and commercial projects.
      </p>
    </motion.div>
  );
}

export default Home;
