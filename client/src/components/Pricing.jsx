import React, { useEffect, useMemo, useState } from "react";
import Card from "./ui/Card";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { buildApiUrl, readJsonResponse } from "../utils/apiConfig.js";

const TRIAL_TERMS = `Trial terms

A valid credit/debit card is required to start the 7-day trial. A temporary $1 verification charge will be placed and refunded after successful verification.

Trial access is limited to one per email/account. We may decline or revoke trial access for suspected abuse or fraud.

Your trial ends after 7 days unless you purchase a paid plan.`;

const LIFETIME_TERMS = `Lifetime terms

Lifetime membership is a one-time purchase that grants access to the Civispec application for one account, for as long as the service is offered.

Offer is limited to the first 300 completed purchases and may be modified or ended at any time before purchase.

Membership is non-transferable and intended for a single account/user. Access may be suspended for violations of our Terms of Service or suspected fraud. Taxes may apply. Refunds are subject to our refund policy.`;

const trialOption = {
  name: "7-day trial",
  price: "$1",
  cadence: "refundable verification",
  description: "Start a 7-day trial after verifying your card. We refund the $1 after verification.",
  termsTitle: "Trial terms",
  termsBody: TRIAL_TERMS,
  perks: ["Card required", "Refunded after verification", "One trial per email"],
  highlight: false,
};

const plans = [
  {
    name: "Consultant Monthly",
    price: "$59",
    cadence: "per month",
    planKey: "consultant_monthly",
    description: "Unlimited station lookups, IDF curves, and PDF exports.",
    perks: [
      "Unlimited rainfall station access",
      "Metric & imperial exports",
      "Email support response < 24h",
    ],
  },
  {
    name: "Lifetime Membership (limited-time)",
    price: "$300",
    cadence: "one-time",
    planKey: "lifetime",
    description: "Lifetime access for the first 300 purchasers. Conditions apply.",
    termsTitle: "Lifetime terms",
    termsBody: LIFETIME_TERMS,
    perks: [
      "One-time payment (no renewal)",
      "Lifetime access for 1 account",
      "Limited to first 300 purchasers",
    ],
    highlight: true,
  },
];

const Pricing = () => {
  const { user, token } = useAuth();
  const [checkoutPlanKey, setCheckoutPlanKey] = useState(null);
  const [checkoutError, setCheckoutError] = useState("");
  const [trialLoading, setTrialLoading] = useState(false);
  const [trialError, setTrialError] = useState("");
  const [termsOpen, setTermsOpen] = useState(false);
  const [termsTitle, setTermsTitle] = useState("");
  const [termsBody, setTermsBody] = useState("");

  const primaryHref = user ? "/start" : "/signup";
  const loggedOutLabel = "Create account";
  const subscribeLabel = "Subscribe";
  const trialLabel = "Verify card & start 7-day trial";

  const openTerms = (title, body) => {
    setTermsTitle(title || "Terms");
    setTermsBody(body || "");
    setTermsOpen(true);
  };

  const closeTerms = () => {
    setTermsOpen(false);
  };

  useEffect(() => {
    if (!termsOpen) return;
    const onKeyDown = (e) => {
      if (e.key === "Escape") {
        closeTerms();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [termsOpen]);

  useEffect(() => {
    if (termsOpen) {
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = "";
      };
    }
  }, [termsOpen]);

  const termsLines = useMemo(() => (termsBody ? termsBody.split("\n") : []), [termsBody]);

  const startCheckout = async (planKey) => {
    if (!user) return;
    if (!token) {
      window.location.assign("/login");
      return;
    }

    try {
      setCheckoutError("");
      setCheckoutPlanKey(planKey || "consultant_monthly");

      const res = await fetch(buildApiUrl("/billing/create-checkout-session"), {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ plan: planKey || "consultant_monthly" }),
      });

      if (!res.ok) {
        const data = await readJsonResponse(res, "Unable to start checkout.");
        setCheckoutError(data?.error || "Unable to start checkout.");
        return;
      }

      const data = await readJsonResponse(res, "Unable to start checkout.");
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

  const startTrialVerification = async () => {
    if (!user) return;
    if (!token) {
      window.location.assign("/login");
      return;
    }

    try {
      setTrialError("");
      setTrialLoading(true);

      const res = await fetch(buildApiUrl("/billing/create-trial-verification-session"), {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({}),
      });

      const data = await readJsonResponse(res, "Unable to start trial verification.");
      if (!res.ok) {
        setTrialError(data?.error || "Unable to start trial verification.");
        return;
      }

      if (!data?.url) {
        setTrialError("Unable to start trial verification.");
        return;
      }

      window.location.assign(data.url);
    } catch (err) {
      setTrialError(err?.message || "Unable to start trial verification.");
    } finally {
      setTrialLoading(false);
    }
  };

  return (
    <section className="bg-white py-24">
      <div className="mx-auto max-w-6xl px-4 md:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-3xl font-bold text-slate-900 sm:text-4xl">Choose the plan that fits your team</h2>
          <p className="mt-4 text-lg text-slate-600">
            Simple subscription tiers for individual consultants, engineering firms, and municipal departments. Cancel
            anytime.
          </p>
        </div>

        <div className="mt-16 grid gap-8 md:grid-cols-3">
          <Card className="relative">
            <h3 className="text-xl font-semibold text-slate-900">{trialOption.name}</h3>
            <div className="mt-4 flex items-end gap-1 text-slate-900">
              <span className="text-4xl font-bold">{trialOption.price}</span>
              <span className="text-sm text-slate-500">{trialOption.cadence}</span>
            </div>
            <p className="mt-4 text-sm text-slate-600">{trialOption.description}</p>
            <button
              type="button"
              onClick={() => openTerms(trialOption.termsTitle, trialOption.termsBody)}
              className="mt-2 inline-flex text-sm font-semibold text-sky-700 underline decoration-sky-300 underline-offset-4 hover:text-sky-800"
            >
              Terms
            </button>

            <ul className="mt-6 space-y-3 text-sm text-slate-600">
              {trialOption.perks.map((perk) => (
                <li key={perk} className="flex items-start gap-2">
                  <span className="mt-1 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
                  <span>{perk}</span>
                </li>
              ))}
            </ul>

            {user ? (
              <button
                type="button"
                onClick={startTrialVerification}
                disabled={trialLoading}
                className="mt-8 inline-flex w-full items-center justify-center rounded-full border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {trialLoading ? "Opening verification…" : trialLabel}
              </button>
            ) : (
              <Link
                to={primaryHref}
                className="mt-8 inline-flex w-full items-center justify-center rounded-full border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2"
              >
                {loggedOutLabel}
              </Link>
            )}

            {trialError && user && (
              <p className="mt-3 text-sm text-rose-600" role="alert">
                {trialError}
              </p>
            )}
          </Card>

          {plans.map((plan) => (
            <Card key={plan.name} className={`relative ${plan.highlight ? "border-sky-500 shadow-lg" : ""}`}>
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
              {plan.termsBody && (
                <button
                  type="button"
                  onClick={() => openTerms(plan.termsTitle, plan.termsBody)}
                  className="mt-2 inline-flex text-sm font-semibold text-sky-700 underline decoration-sky-300 underline-offset-4 hover:text-sky-800"
                >
                  Terms
                </button>
              )}

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
                  {checkoutPlanKey === plan.planKey ? "Opening checkout…" : subscribeLabel}
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

      {termsOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center px-4"
          role="dialog"
          aria-modal="true"
          aria-label={termsTitle || "Terms"}
        >
          <button
            type="button"
            className="absolute inset-0 bg-slate-900/40"
            aria-label="Close terms"
            onClick={closeTerms}
          />
          <div className="relative w-full max-w-xl rounded-2xl bg-white p-6 shadow-xl">
            <div className="flex items-start justify-between gap-4">
              <h3 className="text-lg font-semibold text-slate-900">{termsTitle || "Terms"}</h3>
              <button
                type="button"
                onClick={closeTerms}
                className="rounded-lg px-2 py-1 text-sm font-semibold text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              >
                Close
              </button>
            </div>
            <div className="mt-4 space-y-3 text-sm text-slate-700">
              {termsLines.map((line, idx) => {
                const trimmed = line.trim();
                if (!trimmed) return <div key={idx} />;
                return <p key={idx}>{trimmed}</p>;
              })}
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default Pricing;