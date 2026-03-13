import React, { useEffect, useMemo, useState } from "react";
import Card from "./ui/Card";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { buildApiUrl, readJsonResponse } from "../utils/apiConfig.js";
import { useTranslation } from "react-i18next";




const Pricing = () => {
  const { t } = useTranslation();
  const { user, token } = useAuth();
  const [checkoutPlanKey, setCheckoutPlanKey] = useState(null);
  const [checkoutError, setCheckoutError] = useState("");
  const [trialLoading, setTrialLoading] = useState(false);
  const [trialError, setTrialError] = useState("");
  const [termsOpen, setTermsOpen] = useState(false);
  const [termsTitle, setTermsTitle] = useState("");
  const [termsBody, setTermsBody] = useState("");

  const primaryHref = user ? "/start" : "/signup";
  const loggedOutLabel = t("home.pricing.buttons.createAccount");
  const subscribeLabel = t("home.pricing.buttons.subscribe");
  const trialLabel = t("home.pricing.buttons.verifyTrial");
  const trialOption = {
  name: t("home.pricing.cards.trial.name"),
  price: "$1",
  cadence: t("home.pricing.cards.trial.cadence"),
  description: t("home.pricing.cards.trial.description"),
  termsTitle: t("home.pricing.cards.trial.termsTitle"),
  termsBody: t("home.pricing.terms.trial.body"),
  perks: [
    t("home.pricing.cards.trial.perks.cardRequired"),
    t("home.pricing.cards.trial.perks.refundAfterVerification"),
    t("home.pricing.cards.trial.perks.oneTrialPerEmail")
  ],
  highlight: false
};

const plans = [
  {
    name: t("home.pricing.cards.consultantMonthly.name"),
    price: "$30",
    cadence: t("home.pricing.cards.consultantMonthly.cadence"),
    planKey: "consultant_monthly",
    description: t("home.pricing.cards.consultantMonthly.description"),
    perks: [
      t("home.pricing.cards.consultantMonthly.perks.stationAccess"),
      t("home.pricing.cards.consultantMonthly.perks.exports"),
      t("home.pricing.cards.consultantMonthly.perks.support")
    ]
  },
  {
    name: t("home.pricing.cards.lifetime.name"),
    price: "$300",
    cadence: t("home.pricing.cards.lifetime.cadence"),
    planKey: "lifetime",
    description: t("home.pricing.cards.lifetime.description"),
    termsTitle: t("home.pricing.cards.lifetime.termsTitle"),
    termsBody: t("home.pricing.terms.lifetime.body"),
    perks: [
      t("home.pricing.cards.lifetime.perks.oneTime"),
      t("home.pricing.cards.lifetime.perks.lifetimeOneAccount"),
      t("home.pricing.cards.lifetime.perks.first300")
    ],
      highlight: true
    }
  ];
  const openTerms = (title, body) => {
  setTermsTitle(title || t("home.pricing.buttons.terms"));
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
        const data = await readJsonResponse(res, t("home.pricing.errors.checkoutStart"));
        setCheckoutError(data?.error || t("home.pricing.errors.checkoutStart"));
        return;
      }

      const data = await readJsonResponse(res, t("home.pricing.errors.checkoutStart"));
      if (!data?.url) {
        setCheckoutError(t("home.pricing.errors.checkoutStart"));
        return;
      }

      window.location.assign(data.url);
    } catch (err) {
      setCheckoutError(err?.message || t("home.pricing.errors.checkoutStart"));
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

      const data = await readJsonResponse(res, t("home.pricing.errors.trialStart"));
      if (!res.ok) {
        setTrialError(data?.error || t("home.pricing.errors.trialStart"));
        return;
      }

      if (!data?.url) {
        setTrialError(t("home.pricing.errors.trialStart"));
        return;
      }

      window.location.assign(data.url);
    } catch (err) {
      setTrialError(err?.message || t("home.pricing.errors.trialStart"));
    } finally {
      setTrialLoading(false);
    }
  };

  return (
    <section className="bg-white py-24">
      <div className="mx-auto max-w-6xl px-4 md:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-3xl font-bold text-slate-900 sm:text-4xl">
            {t("home.pricing.title")}
          </h2>
          <p className="mt-4 text-lg text-slate-600">
            {t("home.pricing.subtitle")}
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
              {t("home.pricing.buttons.terms")}
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
                {trialLoading ? t("home.pricing.buttons.openingVerification") : trialLabel}
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
                  {t("home.pricing.labels.popular")}
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
                  {t("home.pricing.buttons.terms")}
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
                  {checkoutPlanKey === plan.planKey ? t("home.pricing.buttons.openingCheckout") : subscribeLabel}
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
          aria-label={termsTitle || t("home.pricing.buttons.terms")}
        >
          <button
            type="button"
            className="absolute inset-0 bg-slate-900/40"
            aria-label={t("home.pricing.buttons.close")}
            onClick={closeTerms}
          />
          <div className="relative w-full max-w-xl rounded-2xl bg-white p-6 shadow-xl">
            <div className="flex items-start justify-between gap-4">
              <h3 className="text-lg font-semibold text-slate-900">{termsTitle || t("home.pricing.buttons.terms")}</h3>
              <button
                type="button"
                onClick={closeTerms}
                className="rounded-lg px-2 py-1 text-sm font-semibold text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              >
                {t("home.pricing.buttons.close")}
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