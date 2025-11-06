import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { buildApiUrl } from "../utils/apiConfig";

function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const redirectTo = location.state?.from?.pathname || "/";

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const response = await fetch(buildApiUrl("/auth/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: identifier, password }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data.error || "Unable to sign in. Please verify your credentials.",
        );
      }

      if (!data.user || !data.accessToken || !data.refreshToken) {
        throw new Error("Unexpected login response from server.");
      }

      login?.(data.user, data.accessToken, data.refreshToken);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      console.error("Login failed", err);
      setError(err.message || "Unexpected error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-100 px-4">
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow">
        <h1 className="text-2xl font-semibold text-gray-900 mb-6">Sign in</h1>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label
              htmlFor="identifier"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Email or username
            </label>
            <input
              id="identifier"
              type="text"
              autoComplete="email"
              className="w-full rounded border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              required
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              className="w-full rounded border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded bg-indigo-600 py-2 text-white font-medium hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default Login;
