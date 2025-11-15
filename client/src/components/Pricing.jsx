import React from "react";
import Card from "./ui/Card";
import { Link } from "react-router-dom";

const plans = [
  {
    name: "Consultant Monthly",
    price: "$59",
    cadence: "per month",
    description: "Unlimited station lookups, IDF curves, and PDF exports.",
    perks: [
      "Unlimited rainfall station access",
      "Metric & imperial exports",
      "Email support response < 24h",
    ],
  },
  {
    name: "Municipal Annual",
    price: "$499",
    cadence: "per year",
    description: "Best for municipalities and agencies needing broad access.",
    perks: [
      "Up to 10 seats included",
      "Priority webhook & API support",
      "Custom reporting templates",
    ],
    highlight: true,
  },
];

const Pricing = () => (
  <section className="bg-white py-24">
    <div className="mx-auto max-w-6xl px-4 md:px-8">
      <div className="mx-auto max-w-3xl text-center">
        <h2 className="text-3xl font-bold text-slate-900 sm:text-4xl">Choose the plan that fits your team</h2>
        <p className="mt-4 text-lg text-slate-600">
          Simple subscription tiers for individual consultants, engineering firms, and municipal departments. Cancel anytime.
        </p>
      </div>

      <div className="mt-16 grid gap-8 md:grid-cols-2">
        {plans.map((plan) => (
          <Card
            key={plan.name}
            className={`relative ${plan.highlight ? "border-sky-500 shadow-lg" : ""}`}
          >
            {plan.highlight && (
              <span className="absolute -top-3 right-6 rounded-full bg-sky-100 px-3 py-1 text-xs font-semibold text-sky-700 shadow">
                Popular
              </span>
            )}

            <h3 className="text-xl font-semibold text-slate-900">{plan.name}</h3>
            <div className="mt-4 flex items-end gap-1 text-slate-900">
              <span className="text-4xl font-bold">{plan.price}</span>
              <span className="text-sm text-slate-500">{plan.cadence}</span>
            </div>
            <p className="mt-4 text-sm text-slate-600">{plan.description}</p>

            <ul className="mt-6 space-y-3 text-sm text-slate-600">
              {plan.perks.map((perk) => (
                <li key={perk} className="flex items-start gap-2">
                  <span className="mt-1 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
                  <span>{perk}</span>
                </li>
              ))}
            </ul>

            <Link
              to="/signup"
              className={`mt-8 inline-flex w-full items-center justify-center rounded-full px-5 py-3 text-sm font-semibold transition focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                plan.highlight
                  ? "bg-sky-600 text-white hover:bg-sky-700 focus:ring-sky-500"
                  : "border border-slate-300 text-slate-700 hover:border-slate-400 hover:text-slate-900 focus:ring-slate-400"
              }`}
            >
              Start free trial
            </Link>
          </Card>
        ))}
      </div>
    </div>
  </section>
);

export default Pricing;