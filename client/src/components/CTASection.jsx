import React from "react";
import { Link } from "react-router-dom";

const CTASection = () => (
  <section className="relative overflow-hidden bg-sky-600 py-20">
    <div className="absolute inset-0 opacity-60">
      <img
        src="https://images.unsplash.com/photo-1573164713988-8665fc963095?auto=format&fit=crop&w=1400&q=80"
        alt=""
        className="h-full w-full object-cover"
      />
    </div>
    <div className="relative mx-auto flex max-w-4xl flex-col items-center gap-6 px-4 text-center text-white md:px-8">
      <h2 className="text-3xl font-bold sm:text-4xl">
        Deliver rainfall data with confidence every time
      </h2>
      <p className="max-w-2xl text-base text-slate-100/90">
        Rainfall Data Finder aggregates Environment Canada datasets, cleans them, and gives your
        engineering team a single place to retrieve up-to-date IDF curves, rainfall station metadata,
        and ready-to-share reports.
      </p>
      <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
        <Link
          to="/start"
          className="inline-flex items-center justify-center rounded-full bg-white px-6 py-3 text-sm font-semibold text-sky-700 shadow-sm transition hover:bg-sky-50 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-sky-600"
        >
          Launch the viewer
        </Link>
        <Link
          to="/contact"
          className="inline-flex items-center justify-center rounded-full border border-white/60 px-6 py-3 text-sm font-semibold text-white transition hover:border-white focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-sky-600"
        >
          Book a walkthrough
        </Link>
      </div>
    </div>
  </section>
);

export default CTASection;
