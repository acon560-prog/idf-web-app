import React from "react";
import { motion } from "framer-motion";
import permitImg from '../assets/permit-drawings.jpg';
import gradingImg from '../assets/grading-drainage.jpg';

function Services() {
  return (
    <motion.div
      className="mx-auto max-w-6xl px-4 py-16 md:px-8"
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8 }}
    >
      <div className="mx-auto max-w-3xl text-center">
        <h2 className="text-3xl font-bold text-slate-900 sm:text-4xl">Our Services</h2>
        <p className="mt-4 text-lg text-slate-600">
          Practical, code-compliant civil and structural engineering for small projects, renovations, and site development.
          Clear drawings, constructible details, and responsive support through permitting and construction.
        </p>
      </div>

      <div className="mt-12 grid gap-8 md:grid-cols-3">
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-xl font-semibold text-slate-900">Structural design</h3>
          <p className="mt-3 text-sm text-slate-600">
            Design of wood, steel, and reinforced concrete components for safe load paths and efficient framing. Typical
            deliverables include foundation sizing, beam and lintel design, connection detailing, and notes aligned with
            the applicable building code.
          </p>
          <ul className="mt-4 space-y-2 text-sm text-slate-600">
            <li className="flex gap-2">
              <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
              <span>Member sizing and connection details</span>
            </li>
            <li className="flex gap-2">
              <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
              <span>Foundation and retaining element checks</span>
            </li>
            <li className="flex gap-2">
              <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
              <span>Repair / retrofit concepts for renovations</span>
            </li>
          </ul>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-xl font-semibold text-slate-900">Permit drawings</h3>
          <p className="mt-3 text-sm text-slate-600">
            Permit-ready drawing sets that help reviewers quickly understand the scope and compliance approach.
            I focus on clean sheets, clear notes, and coordination between architectural intent and engineering details.
          </p>
          <div className="mt-4 overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
            
           <div className="h-40">
              <img
                src={permitImg}
                alt="Permit drawings example"
                className="h-full w-full object-cover"
              />
            </div>
          </div>
          <ul className="mt-4 space-y-2 text-sm text-slate-600">
            <li className="flex gap-2">
              <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
              <span>General notes, typical details, and schedules</span>
            </li>
            <li className="flex gap-2">
              <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
              <span>Coordination with site and grading drawings</span>
            </li>
            <li className="flex gap-2">
              <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
              <span>Revisions and responses during plan review</span>
            </li>
          </ul>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-xl font-semibold text-slate-900">Grading &amp; drainage plans</h3>
          <p className="mt-3 text-sm text-slate-600">
            Site grading concepts focused on constructability, positive drainage, and sensible stormwater routing. Where
            needed, we can provide rational-method sizing checks and supporting documentation for approvals.
          </p>
          <div className="mt-4 overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
            <div className="h-40">
					    <img
						    src={gradingImg}
						    alt="Grading and drainage plan example"
						    className="h-full w-full object-cover"
			      />
		        </div>
          </div>
          <ul className="mt-4 space-y-2 text-sm text-slate-600">
            <li className="flex gap-2">
              <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
              <span>Spot elevations, slopes, swales, and flow arrows</span>
            </li>
            <li className="flex gap-2">
              <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
              <span>Catch basins / culverts / driveway drainage concepts</span>
            </li>
            <li className="flex gap-2">
              <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
              <span>Erosion and sediment control notes (as applicable)</span>
            </li>
          </ul>
        </section>
      </div>

      <div className="mt-12 rounded-2xl border border-slate-200 bg-slate-50 p-6">
        <h3 className="text-lg font-semibold text-slate-900">Site planning &amp; analysis</h3>
        <p className="mt-2 text-sm text-slate-600">
          Early feasibility input to reduce redesign: layout constraints, drainage paths, grading implications, and
          practical construction sequencing considerations.
        </p>
      </div>
    </motion.div>
  );
}

export default Services;
