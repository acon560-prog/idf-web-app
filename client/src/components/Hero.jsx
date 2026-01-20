import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

const Hero = () => {
  const { user } = useAuth();
  const [featuresOpen, setFeaturesOpen] = useState(false);

  const primaryHref = user ? "/start" : "/login";
  const primaryLabel = user ? "Go to dashboard" : "Log in";

  const features = useMemo(
    () => [
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
    ],
    []
  );

  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-sky-50 via-white to-white">
      <div className="absolute -left-24 -top-24 h-72 w-72 rounded-full bg-sky-100 blur-3xl opacity-60" />
      <div className="absolute -right-20 top-1/3 h-80 w-80 rounded-full bg-blue-100 blur-3xl opacity-70" />

      <div className="relative mx-auto flex max-w-6xl flex-col-reverse items-center gap-12 px-4 py-24 md:flex-row md:justify-between md:px-8">
        <div className="max-w-2xl text-center md:text-left">
          <p className="inline-flex items-center rounded-full bg-sky-100 px-4 py-1 text-sm font-medium text-sky-700">
            Rainfall Data Finder • Canada
          </p>
          <h1 className="mt-6 text-4xl font-extrabold text-slate-900 sm:text-5xl lg:text-6xl">
            Powerful rainfall insights for Canadian engineers and planners
          </h1>
          <p className="mt-6 text-lg text-slate-600">
            Search thousands of Environment Canada stations, access IDF curves, and share reports with your team in seconds. Built for civil engineers, hydrologists, and municipal planning departments.
          </p>
          <div className="mt-8 flex flex-col gap-4 sm:flex-row sm:justify-center md:justify-start">
            <Link
              to={primaryHref}
              className="inline-flex items-center justify-center rounded-full bg-sky-600 px-8 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-700 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2"
            >
              {primaryLabel}
            </Link>
            <button
              type="button"
              onClick={() => setFeaturesOpen(true)}
              className="inline-flex items-center justify-center rounded-full border border-slate-300 px-8 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2"
            >
              Explore features
            </button>
          </div>

          <dl className="mt-12 grid grid-cols-2 gap-6 text-sm text-slate-500 sm:grid-cols-3">
            <div>
              <dt className="font-medium text-slate-800">Stations covered</dt>
              <dd>7,000+ nationwide</dd>
            </div>
            <div>
              <dt className="font-medium text-slate-800">IDF datasets</dt>
              <dd>695 curated records</dd>
            </div>
            <div>
              <dt className="font-medium text-slate-800">Response time</dt>
              <dd>Under 2 seconds</dd>
            </div>
          </dl>
        </div>

        <div className="relative flex w-full max-w-md justify-center">
          <div className="relative overflow-hidden rounded-3xl bg-white shadow-2xl ring-1 ring-slate-200">
            <img
              src="https://images.unsplash.com/photo-1521207418485-99c705420785?auto=format&fit=crop&w=900&q=80"
              alt="Rainfall chart preview"
              className="h-96 w-full object-cover"
            />
            <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent p-6 text-white">
              <p className="text-sm uppercase tracking-wide text-sky-200">Live preview</p>
              <p className="mt-3 text-lg font-semibold">
                Mission, BC — 100 year return period peak intensity
              </p>
              <p className="text-sm text-slate-200/80">
                Retrieve accurate IDF curves for any location in Canada—in just one click.
              </p>
            </div>
          </div>
        </div>
      </div>
      {featuresOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl ring-1 ring-slate-200">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-lg font-semibold text-slate-900">Explore features</h3>
                <p className="mt-1 text-sm text-slate-600">
                  These are on our roadmap. They’ll appear in the app as they’re released.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setFeaturesOpen(false)}
                className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                aria-label="Close"
              >
                Close
              </button>
            </div>

            <ul className="mt-6 space-y-4">
              {features.map((f) => (
                <li key={f.title} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="font-semibold text-slate-900">{f.title}</div>
                    <span className="inline-flex items-center rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">
                      Coming soon
                    </span>
                  </div>
                  <div className="mt-1 text-sm text-slate-600">{f.description}</div>
                </li>
              ))}
            </ul>

            <div className="mt-6 flex justify-end">
              <Link
                to="/pricing"
                onClick={() => setFeaturesOpen(false)}
                className="inline-flex items-center justify-center rounded-full bg-sky-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-sky-700 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2"
              >
                View pricing
              </Link>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default Hero;