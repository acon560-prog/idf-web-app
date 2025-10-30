import React from 'react';
import { motion } from 'framer-motion';

function About() {
  return (
    <motion.div
      className="p-4"
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}   // ← changed this
      transition={{ duration: 0.8 }}
    >
      <h2 className="text-2xl font-bold">About Us</h2>
      <p className="mt-4">
        With decades of experience, we help clients achieve safe, code-compliant and cost-effective solutions in residential and commercial projects.
      </p>
    </motion.div>
  );
}

export default About;

