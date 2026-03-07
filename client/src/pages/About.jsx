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
      <div className="max-w-2xl w-full">
        <h2 className="text-3xl font-bold text-slate-900">About Us</h2>
        <p className="mt-4 text-lg text-slate-700 leading-relaxed">
         With over 18 years of experience in civil engineering, we help each client plan and deliver practical, code-compliant and cost-effective infrastructure solutions. Our work spans residential, industrial, mining and public projects, covering drinking water, wastewater and stormwater systems, earthworks, road drainage and hydraulic and hydrologic modeling.
        </p>
      </div>
 
      <div className="mt-8 max-w-2xl border-l-4 border-indigo-500 pl-6">
        <section className="pb-5">
          <h3 className="text-xl font-semibold text-slate-900">Core strengths</h3>
          <ul className="mt-3 list-disc space-y-1 pl-6 text-slate-700">
            <li>Experience in aqueduct, sewer, and storm drainage systems</li>
            <li>Hydrology and hydraulic design for road and urban projects</li>
            <li>Practical grading and site-servicing design approach</li>
          </ul>
        </section>
      </div>  
    </motion.div>
  );
}

export default About;

