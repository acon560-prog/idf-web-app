import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { buildApiUrl } from "../utils/apiConfig";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
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
          data.error || t("login.errors.invalidCredentials")
        );
      }

      if (!data.user || !data.accessToken || !data.refreshToken) {
        throw new Error(t("login.errors.unexpectedResponse"));
      }

      login?.(data.user, data.accessToken, data.refreshToken);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      console.error("Login failed", err);
      setError(err.message || t("login.errors.unexpected"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-100 px-4">
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow">
        <h1 className="text-2xl font-semibold text-gray-900 mb-6">{t("login.title")}</h1>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label
              htmlFor="identifier"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              {t("login.fields.identifier")}
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
              {t("login.fields.password")}
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                className="w-full rounded border border-gray-300 px-3 py-2 pr-16 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                className="absolute inset-y-0 right-3 flex items-center text-sm font-medium text-indigo-600 hover:text-indigo-700 focus:outline-none"
              >
                {showPassword ? t("login.buttons.hide") : t("login.buttons.show")}
              </button>
            </div>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded bg-indigo-600 py-2 text-white font-medium hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? t("login.buttons.signingIn") : t("login.buttons.signIn")}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-gray-600">
          {t("login.links.needAccount")}
          <Link to="/signup" className="text-indigo-600 hover:text-indigo-700">
            {t("login.links.signUp")}
          </Link>
        </p>
      </div>
    </div>
  );
}

export default Login;
