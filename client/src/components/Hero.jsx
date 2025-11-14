import React from "react";
import { Link } from "react-router-dom";

const Hero = () => (
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
          Search thousands of Environment Canada stations, access IDF curves, and share reports
          with your team in seconds. Built for civil engineers, hydrologists, and municipal planning
          departments.
        </p>
        <div className="mt-8 flex flex-col gap-4 sm:flex-row sm:justify-center md:justify-start">
          <Link
            to="/start"
            className="inline-flex items-center justify-center rounded-full bg-sky-600 px-8 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-700 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2"
          >
            Start analyzing data
          </Link>
          <Link
            to="/services"
            className="inline-flex items-center justify-center rounded-full border border-slate-300 px-8 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2"
          >
            Explore features
          </Link>
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
              Analyze storm profiles, peak intensities, and design rainfall events in one click.
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>
);

export default Hero;
