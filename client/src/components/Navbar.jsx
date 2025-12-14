import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";      // ❶ add this
import { buildApiUrl } from "../utils/apiConfig";

function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [billingLoading, setBillingLoading] = useState(false);
  const { user, logout, authFetch } = useAuth();                     // ❷ get user + logout
  const isAdmin = user?.role === "admin";

  const handleBillingClick = async () => {
    if (!user || !authFetch || billingLoading) return;
    setBillingLoading(true);
    try {
      if (user.subscriptionStatus === "active" && user.stripeCustomerId) {
        const res = await authFetch(buildApiUrl("/billing/create-portal-session"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data?.error || "Failed to open billing portal.");
        }
        window.location.assign(data.url);
        return;
      }

      const res = await authFetch(buildApiUrl("/billing/create-checkout-session"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan: "monthly" }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error || "Failed to start checkout.");
      }
      window.location.assign(data.checkoutUrl);
    } catch (err) {
      console.error(err);
      alert(err?.message || "Billing action failed.");
    } finally {
      setBillingLoading(false);
    }
  };

  return (
    <nav className="bg-gray-800 text-white">
      <div className="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
        <h1 className="text-xl font-bold">CiviSpec</h1>
        <ul className="hidden md:flex space-x-6 items-center">
          <li><Link to="/" className="hover:underline">Home</Link></li>
          <li><Link to="/about" className="hover:underline">About</Link></li>
          <li><Link to="/services" className="hover:underline">Services</Link></li>
          <li><Link to="/contact" className="hover:underline">Contact</Link></li>
          {isAdmin && <li><Link to="/admin" className="hover:underline">Admin</Link></li>}
          <li><Link to="/start" className="hover:underline text-yellow-300 font-semibold">Start</Link></li>
          {user && (
            <li>
              <button
                type="button"
                onClick={handleBillingClick}
                disabled={billingLoading}
                className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {billingLoading ? "Working..." : "Subscribe / Manage billing"}
              </button>
            </li>
          )}
          {user && (                                       // ❸ show logout when logged in
            <li>
              <button type="button" onClick={logout} className="hover:underline">
                Log out
              </button>
            </li>
          )}
        </ul>

        <button
          className="md:hidden text-white focus:outline-none"
          onClick={() => setMenuOpen(!menuOpen)}
        >
          ☰
        </button>
      </div>

      {menuOpen && (
        <ul className="md:hidden px-4 pb-4 space-y-2 bg-gray-700">
          <li><Link to="/" onClick={() => setMenuOpen(false)}>Home</Link></li>
          <li><Link to="/about" onClick={() => setMenuOpen(false)}>About</Link></li>
          <li><Link to="/services" onClick={() => setMenuOpen(false)}>Services</Link></li>
          <li><Link to="/contact" onClick={() => setMenuOpen(false)}>Contact</Link></li>
          {isAdmin && (
            <li><Link to="/admin" onClick={() => setMenuOpen(false)}>Admin</Link></li>
          )}
          <li><Link to="/start" onClick={() => setMenuOpen(false)} className="text-yellow-300 font-semibold">Start</Link></li>
          {user && (
            <li>
              <button
                type="button"
                onClick={() => {
                  handleBillingClick();
                  setMenuOpen(false);
                }}
                disabled={billingLoading}
                className="w-full text-left rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {billingLoading ? "Working..." : "Subscribe / Manage billing"}
              </button>
            </li>
          )}
          {user && (
            <li>
              <button
                type="button"
                onClick={() => {
                  logout();
                  setMenuOpen(false);
                }}
                className="hover:underline"
              >
                Log out
              </button>
            </li>
          )}
        </ul>
      )}
    </nav>
  );
}

export default Navbar;