import React from "react";
import { MapPin, LineChart, CloudLightning } from "lucide-react";
import Card from "./ui/Card.jsx";

const featureList = [
  {
    icon: MapPin,
    title: "Smart Station Lookup",
    description:
      "Search thousands of Environment Canada stations by municipality, postal code, or GPS coordinates.",
  },
  {
    icon: LineChart,
    title: "Instant IDF Curves",
    description:
      "Generate intensity-duration-frequency charts in both metric and imperial units, ready for design work.",
  },
  {
    icon: CloudLightning,
    title: "Shareable Deliverables",
    description:
      "Export reports for plan submissions, consultant reviews, and GIS collaborators in a single click.",
  },
];

const Features = () => (
  <section className="bg-white py-24">
    <div className="mx-auto max-w-6xl px-4 md:px-8">
      <div className="mx-auto max-w-3xl text-center">
        <h2 className="text-3xl font-bold text-slate-900 sm:text-4xl">
          All the tools you need for rainfall design on one screen
        </h2>
        <p className="mt-4 text-lg text-slate-600">
          Built for civil engineers, water resource specialists, hydrologists, and municipal planners
          who need quick, defensible design rainfall data.
        </p>
      </div>

      <div className="mt-16 grid gap-8 md:grid-cols-3">
        {featureList.map((feature) => (
          <Card key={feature.title}>
            <feature.icon className="h-10 w-10 text-sky-600" />
            <h3 className="mt-6 text-lg font-semibold text-slate-800">{feature.title}</h3>
            <p className="mt-3 text-sm text-slate-600">{feature.description}</p>
          </Card>
        ))}
      </div>
    </div>
  </section>
);

export default Features;
