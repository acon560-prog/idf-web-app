import React, { useState } from "react";
import Card from "./ui/Card";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { buildApiUrl, readJsonResponse } from "../utils/apiConfig.js";
 
const plans = [
  {
    name: "Consultant Monthly",
    price: "$32",
    cadence: "per month",
    trial: "7-day free trial",
    planKey: "consultant_monthly",
    description: "Unlimited station lookups, IDF curves, and PDF exports.",
    perks: [
      "Unlimited rainfall station access",
      "Metric & imperial exports",
      "Email support response < 24h",
    ],
  },
  {
    name: "Municipal Annual",
    price: "$300",
    cadence: "per year",
    trial: "7-day free trial",
    planKey: "municipal_annual",
    description: "Best for municipalities and agencies needing broad access.",
    perks: [
      "Up to 10 seats included",
      "Priority webhook & API support",
      "Custom reporting templates",
    ],
    highlight: true,
  },
];
 
const Pricing = () => {
  const { user, token } = useAuth();
  const [checkoutPlanKey, setCheckoutPlanKey] = useState(null);
  const [checkoutError, setCheckoutError] = useState("");
 
  const primaryHref = "/signup";
  const loggedOutLabel = "Start 7-day free trial";
  const loggedInLabel = "Continue to checkout";
 
  const startCheckout = async (planKey) => {
    if (!user) return;
    if (!token) {
      window.location.assign("/login");
      return;
    }
 
    try {
      setCheckoutError("");
      setCheckoutPlanKey(planKey);
 
      const res = await fetch(buildApiUrl("/billing/create-checkout-session"), {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ plan: planKey }),
      });
 
      const data = await readJsonResponse(res, "Unable to start checkout.");
 
      if (!res.ok) {
        setCheckoutError(data?.error || "Unable to start checkout.");
        return;
      }
 
      if (!data?.url) {
        setCheckoutError("Unable to start checkout.");
        return;
      }
 
      window.location.assign(data.url);
    } catch (err) {
      setCheckoutError(err?.message || "Unable to start checkout.");
    } finally {
      setCheckoutPlanKey(null);
    }
  };
 
  return (
    <section className="bg-white py-24">
      <div className="mx-auto max-w-6xl px-4 md:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-3xl font-bold text-slate-900 sm:text-4xl">
            Choose the plan that fits your team
          </h2>
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
 
              {plan.trial && (
                <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <div className="text-sm font-semibold text-slate-900">{plan.trial}</div>
                  <div className="mt-0.5 text-xs text-slate-600">
                    Try everything before you’re billed.
                  </div>
                </div>
              )}
 
              <p className="mt-4 text-sm text-slate-600">{plan.description}</p>
 
              <ul className="mt-6 space-y-3 text-sm text-slate-600">
                {plan.perks.map((perk) => (
                  <li key={perk} className="flex items-start gap-2">
                    <span className="mt-1 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
                    <span>{perk}</span>
                  </li>
                ))}
              </ul>
 
              {user ? (
                <button
                  type="button"
                  onClick={() => startCheckout(plan.planKey)}
                  disabled={checkoutPlanKey === plan.planKey}
                  className={`mt-8 inline-flex w-full items-center justify-center rounded-full px-5 py-3 text-sm font-semibold transition focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-70 ${
                    plan.highlight
                      ? "bg-sky-600 text-white hover:bg-sky-700 focus:ring-sky-500"
                      : "border border-slate-300 text-slate-700 hover:border-slate-400 hover:text-slate-900 focus:ring-slate-400"
                  }`}
                >
                  {checkoutPlanKey === plan.planKey ? "Opening checkout…" : loggedInLabel}
                </button>
              ) : (
                <Link
                  to={primaryHref}
                  className={`mt-8 inline-flex w-full items-center justify-center rounded-full px-5 py-3 text-sm font-semibold transition focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                    plan.highlight
                      ? "bg-sky-600 text-white hover:bg-sky-700 focus:ring-sky-500"
                      : "border border-slate-300 text-slate-700 hover:border-slate-400 hover:text-slate-900 focus:ring-slate-400"
                  }`}
                >
                  {loggedOutLabel}
                </Link>
              )}
 
              {checkoutError && user && (
                <p className="mt-3 text-sm text-rose-600" role="alert">
                  {checkoutError}
                </p>
              )}
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
};
 
export default Pricing;