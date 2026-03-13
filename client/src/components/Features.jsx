import React from "react";
import { MapPin, LineChart, CloudLightning } from "lucide-react";
import { useTranslation } from "react-i18next";
import Card from "./ui/Card.jsx";

const Features = () => {
  const { t } = useTranslation();

  const featureList = [
    {
      icon: MapPin,
      title: t("home.features.items.smartLookup.title"),
      description: t("home.features.items.smartLookup.description"),
    },
    {
      icon: LineChart,
      title: t("home.features.items.instantCurves.title"),
      description: t("home.features.items.instantCurves.description"),
    },
    {
      icon: CloudLightning,
      title: t("home.features.items.shareable.title"),
      description: t("home.features.items.shareable.description"),
    },
  ];

  return (
    <section className="bg-white py-24">
      <div className="mx-auto max-w-6xl px-4 md:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-3xl font-bold text-slate-900 sm:text-4xl">
            {t("home.features.title")}
          </h2>
          <p className="mt-4 text-lg text-slate-600">
            {t("home.features.subtitle")}
          </p>
        </div>

        <div className="mt-16 grid gap-8 md:grid-cols-3">
          {featureList.map((feature) => {
            const Icon = feature.icon;
            return (
              <Card key={feature.title}>
                <Icon className="h-10 w-10 text-sky-600" />
                <h3 className="mt-6 text-lg font-semibold text-slate-800">
                  {feature.title}
                </h3>
                <p className="mt-3 text-sm text-slate-600">
                  {feature.description}
                </p>
              </Card>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default Features;