import React from 'react';
import { motion } from 'framer-motion';

function NotFound() {
  return (
    <motion.div
      className="p-4 text-center"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <h1 className="text-3xl font-bold text-red-600">404 - Page Not Found</h1>
      <p className="mt-2 text-gray-700">The page you're looking for does not exist.</p>
    </motion.div>
  );
}

export default NotFound;
