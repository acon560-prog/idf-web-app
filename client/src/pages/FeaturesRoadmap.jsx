import React from "react";
import { Link } from "react-router-dom";
import Card from "../components/ui/Card.jsx";

const roadmapFeatures = [
  {
    title: "Design storm generator",
    description: "Produce hyetographs from IDF (Chicago, alternating block).",
  },
  {
    title: "Compare stations",
    description: "Side-by-side IDF curves with distance and metadata.",
  },
  {
    title: "API access",
    description: "Generate an API key for programmatic IDF queries (for municipalities).",
  },
  {
    title: "Saved templates",
    description: "Customizable PDF report templates (logo, disclaimers, units).",
  },
];

function FeaturesRoadmap() {
  return (
    <section className="bg-white py-20">
      <div className="mx-auto max-w-6xl px-4 md:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-3xl font-bold text-slate-900 sm:text-4xl">Explore features</h2>
          <p className="mt-4 text-lg text-slate-600">
            These features are planned and will roll out over time. If you want one prioritized, send us a message.
          </p>
        </div>

        <div className="mt-12 grid gap-8 md:grid-cols-2">
          {roadmapFeatures.map((f) => (
            <Card key={f.title}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h3 className="text-lg font-semibold text-slate-900">{f.title}</h3>
                <span className="inline-flex items-center rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">
                  Coming soon
                </span>
              </div>
              <p className="mt-3 text-sm text-slate-600">{f.description}</p>
              <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">
                <span className="font-semibold text-slate-800">Note:</span> timeline depends on demand and availability.
              </div>
            </Card>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Link
            to="/pricing"
            className="inline-flex items-center justify-center rounded-full bg-sky-600 px-8 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-700 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2"
          >
            View pricing
          </Link>
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-full border border-slate-300 px-8 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2"
          >
            Back to home
          </Link>
        </div>
      </div>
    </section>
  );
}

export default FeaturesRoadmap;

