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
      <h2 className="text-2xl font-bold">Skills and Experience</h2>

      <p className="mt-4">
        Practical and versatile Civil Engineer with more than 18 years of experience in the analysis,
        design, and construction supervision of water distribution, sanitary sewer, and stormwater
        drainage systems. My professional path across multiple engineering roles supports a practical,
        results-driven approach to project delivery.
      </p>

      <h3 className="mt-6 text-xl font-semibold">Qualification Highlights</h3>
      <ul className="mt-3 list-disc space-y-2 pl-6">
        <li>
          More than 18 years of experience in the analysis, design, and supervision of aqueduct,
          sewer, and stormwater drainage systems.
        </li>
        <li>
          Project experience in residential, industrial, and mining sectors, including grading,
          site servicing design, storm and sanitary pumping stations, storage ponds, and road design.
        </li>
        <li>
          Contribution to major City of Montreal infrastructure projects, including the Sainte-Catherine
          Street redevelopment and the Pie-IX Boulevard Bus Rapid Transit (BRT) corridor.
        </li>
        <li>
          Strong capability in hydrology and drainage planning for road projects, including watershed
          studies, hydraulic design for stormwater quantity and quality control, low-impact development
          practices, and flood/scour analysis for existing highway sites and watercourse crossings.
        </li>
        <li>
          Familiar with Quebec Ministry of Transport (MTQ) standards, guidelines, and specifications
          related to roadway and drainage design.
        </li>
        <li>
          Advanced use of EPANET, WaterCAD, CulvertMaster, HY-8, SWMM 5.0, HEC-HMS, and HEC-RAS for
          hydraulic/hydrologic simulation and drainage system design.
        </li>
        <li>
          Proficient with MicroStation V8, AutoCAD Civil 3D, OpenRoads, MS Office, STAAD.Pro, SAP2000,
          RISA, and programming in Python and Java.
        </li>
      </ul>

      <h3 className="mt-6 text-xl font-semibold">Recent Experience</h3>
      <ul className="mt-3 list-disc space-y-2 pl-6">
        <li>
          <strong>Hatch Ltd., Montreal, QC (May 2022 - Feb 2025) - Senior Civil Engineer:</strong> Led
          infrastructure project activities for rail programs (ONxpress, Metrolinx Ontario) and
          hydraulic system design/analysis including pipelines, channels, and drainage systems
          (Hydro-Quebec, Rio Tinto).
        </li>
        <li>
          <strong>FNX-INNOV, Montreal, QC (Nov 2020 - Mar 2022) - Senior Civil Engineer:</strong>
          Managed drainage system design projects for Hydro One electrical substations in Ontario and
          completed design and cost estimation for schoolyard redevelopment projects in Quebec, including
          Gaetan-Boucher and Charles-Bruneau schools.
        </li>
      </ul>
    </motion.div>
  );
}

export default About;

