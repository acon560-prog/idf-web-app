import React from 'react';
import { motion } from 'framer-motion';

function Services() {
  return (
    <motion.div
      className="p-4"
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8 }}
    >
      <h2 className="text-2xl font-bold mb-4">Our Services</h2>
      <ul className="list-disc ml-6 space-y-2">
        <li>Structural Design</li>
        <li>Permit Drawings</li>
        <li>Grading & Drainage Plans</li>
        <li>Site Planning & Analysis</li>
      </ul>
    </motion.div>
  );
}

export default Services;

