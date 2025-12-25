import React, { useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import Pricing from "../components/Pricing.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { buildApiUrl, readJsonResponse } from "../utils/apiConfig.js";

function Start() {
  const { user, authFetch } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const hasAccess = useMemo(
    () => user?.role === "admin" || user?.subscriptionStatus === "active",
    [user],
  );

  const fromPath = location.state?.from?.pathname;

  const beginCheckout = async () => {
    setError(null);
    setLoading(true);
    try {
      // Your Flask backend already exposes this route in your local setup:
      // POST /api/billing/create-checkout-session
      const res = await (authFetch
        ? authFetch(buildApiUrl("/billing/create-checkout-session"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({}),
          })
        : fetch(buildApiUrl("/billing/create-checkout-session"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({}),
          }));

      const data = await readJsonResponse(res, "Failed to start checkout.");
      if (!res.ok) {
        throw new Error(data?.error || "Failed to start checkout.");
      }

      const url = data?.url || data?.checkoutUrl || data?.checkout_url;
      if (url) {
        window.location.href = url;
        return;
      }

      // Fallback: if backend returns session id only, you can wire Stripe client later.
      throw new Error(
        "Checkout session created but no redirect URL was returned by the server.",
      );
    } catch (err) {
      setError(err?.message || "Checkout failed.");
    } finally {
      setLoading(false);
    }
  };

  if (hasAccess) {
    // If user already subscribed, send them straight to the viewer.
    const target = fromPath || "/idf-viewer";
    navigate(target, { replace: true });
    return null;
  }

  return (
    <div className="bg-slate-50">
      <div className="mx-auto max-w-6xl px-4 py-10 md:px-8">
        <div className="rounded-2xl bg-white p-6 shadow-sm md:p-10">
          <h1 className="text-3xl font-bold text-slate-900">
            IDF Viewer is a subscriber feature
          </h1>
          <p className="mt-3 max-w-3xl text-slate-600">
            Create an account, then subscribe to unlock full IDF curves and
            downloads.
          </p>

          {!user ? (
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                to="/signup"
                className="inline-flex items-center justify-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
              >
                Create account
              </Link>
              <Link
                to="/login"
                className="inline-flex items-center justify-center rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              >
                Sign in
              </Link>
            </div>
          ) : (
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={beginCheckout}
                disabled={loading}
                className="inline-flex items-center justify-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"
              >
                {loading ? "Redirecting to checkout…" : "Subscribe to unlock"}
              </button>
              <span className="text-sm text-slate-600">
                Signed in as <strong>{user.email || user.username}</strong>
              </span>
            </div>
          )}

          {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
        </div>
      </div>

      {/* Reuse your existing pricing UI below the gate header */}
      <Pricing />
    </div>
  );
}

export default Start;