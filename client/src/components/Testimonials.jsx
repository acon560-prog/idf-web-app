import React from "react";
import Card from "./ui/Card.jsx";

const testimonials = [
  {
    quote:
      "We saved days pulling rainfall data for tender packages. The team can access updated IDF curves instantly instead of juggling spreadsheets.",
    name: "Sofia Martinez",
    title: "Hydrology Lead, BlueRiver Engineering",
  },
  {
    quote:
      "Rainfall Data Finder makes municipal storm studies much simpler. We can cross-check stations and generate reports in minutes.",
    name: "Devon Patel",
    title: "Municipal Infrastructure Planner",
  },
];

const Testimonials = () => (
  <section className="bg-sky-50 py-24">
    <div className="mx-auto max-w-6xl px-4 md:px-8">
      <h2 className="text-center text-3xl font-bold text-slate-900 sm:text-4xl">
        Trusted by Canadian engineering teams across the country
      </h2>

      <div className="mt-16 grid gap-8 md:grid-cols-2">
        {testimonials.map((item) => (
          <Card key={item.name} className="bg-white">
            <p className="text-base text-slate-700">“{item.quote}”</p>
            <p className="mt-6 text-sm font-semibold text-slate-900">{item.name}</p>
            <p className="text-xs text-slate-500">{item.title}</p>
          </Card>
        ))}
      </div>
    </div>
  </section>
);

export default Testimonials;
