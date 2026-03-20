import React from "react";
import { motion } from "framer-motion";
import permitImg from '../assets/permit-drawings.jpg';
import gradingImg from '../assets/grading-drainage.jpg';

const SERVICE_CARDS = [
  {
    id: "structural",
    enabled: false, // Keep content in code, hide from UI for now
    title: "Structural design",
    description:
      "Design of wood, steel, and reinforced concrete components for safe load paths and efficient framing. Typical deliverables include foundation sizing, beam and lintel design, connection detailing, and notes aligned with the applicable building code.",
    bullets: [
      "Member sizing and connection details",
      "Foundation and retaining element checks",
      "Repair / retrofit concepts for renovations",
    ],
  },
  {
    id: "permit",
    enabled: true,
    title: "Permit drawings",
    description:
      "Permit-ready drawing sets that help reviewers quickly understand the scope and compliance approach. I focus on clean sheets, clear notes, and coordination between architectural intent and engineering details.",
    image: {
      src: permitImg,
      alt: "Permit drawings example",
    },
    bullets: [
      "General notes, typical details, and schedules",
      "Coordination with site and grading drawings",
      "Revisions and responses during plan review",
    ],
  },
  {
    id: "grading",
    enabled: true,
    title: "Grading & drainage plans",
    description:
      "Site grading concepts focused on constructability, positive drainage, and sensible stormwater routing. Where needed, we can provide rational-method sizing checks and supporting documentation for approvals.",
    image: {
      src: gradingImg,
      alt: "Grading and drainage plan example",
    },
    bullets: [
      "Spot elevations, slopes, swales, and flow arrows",
      "Catch basins / culverts / driveway drainage concepts",
      "Erosion and sediment control notes (as applicable)",
    ],
  },
];

function Services() {
  const visibleCards = SERVICE_CARDS.filter((card) => card.enabled);

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

      <div className="mt-12 grid gap-8 md:grid-cols-2 lg:grid-cols-3">
        {visibleCards.map((card) => (
          <section
            key={card.id}
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
          >
            <h3 className="text-xl font-semibold text-slate-900">{card.title}</h3>
            <p className="mt-3 text-sm text-slate-600">{card.description}</p>
            {card.image && (
              <div className="mt-4 overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
                <img
                  src={card.image.src}
                  alt={card.image.alt}
                  className="h-48 w-full object-cover"
                />
              </div>
            )}
            <ul className="mt-4 space-y-2 text-sm text-slate-600">
              {card.bullets.map((bullet) => (
                <li key={bullet} className="flex gap-2">
                  <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
                  <span>{bullet}</span>
                </li>
              ))}
            </ul>
          </section>
        ))}
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
