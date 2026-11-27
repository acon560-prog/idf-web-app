import React, { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { buildApiUrl } from "../utils/apiConfig";

function ResetPassword() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = useMemo(
    () => (searchParams.get("token") || "").trim(),
    [searchParams]
  );

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    if (!token) {
      setError(t("resetPassword.errors.missingToken"));
      return;
    }
    if (password.length < 8) {
      setError(t("resetPassword.errors.tooShort"));
      return;
    }
    if (password !== confirmPassword) {
      setError(t("resetPassword.errors.mismatch"));
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(buildApiUrl("/auth/reset-password"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data.error || t("resetPassword.errors.resetFailed")
        );
      }

      setSuccess(data.message || t("resetPassword.success"));
      setTimeout(() => {
        navigate("/login", { replace: true });
      }, 1500);
    } catch (err) {
      console.error("Reset password failed", err);
      setError(err.message || t("resetPassword.errors.unexpected"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-100 px-4">
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow">
        <h1 className="mb-2 text-2xl font-semibold text-gray-900">
          {t("resetPassword.title")}
        </h1>
        <p className="mb-6 text-sm text-gray-600">
          {t("resetPassword.subtitle")}
        </p>

        {!token ? (
          <div className="space-y-4">
            <p className="text-sm text-red-600">
              {t("resetPassword.errors.missingToken")}
            </p>
            <Link
              to="/forgot-password"
              className="inline-block text-sm text-indigo-600 hover:text-indigo-700"
            >
              {t("resetPassword.links.requestNew")}
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label
                htmlFor="password"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                {t("resetPassword.fields.password")}
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="new-password"
                  className="w-full rounded border border-gray-300 px-3 py-2 pr-16 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  minLength={8}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute inset-y-0 right-3 flex items-center text-sm font-medium text-indigo-600 hover:text-indigo-700 focus:outline-none"
                >
                  {showPassword
                    ? t("login.buttons.hide")
                    : t("login.buttons.show")}
                </button>
              </div>
            </div>

            <div>
              <label
                htmlFor="confirmPassword"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                {t("resetPassword.fields.confirmPassword")}
              </label>
              <input
                id="confirmPassword"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                className="w-full rounded border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
                minLength={8}
              />
            </div>

            {error && <p className="text-sm text-red-600">{error}</p>}
            {success && <p className="text-sm text-green-700">{success}</p>}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded bg-indigo-600 py-2 font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading
                ? t("resetPassword.buttons.saving")
                : t("resetPassword.buttons.save")}
            </button>
          </form>
        )}

        <p className="mt-4 text-center text-sm text-gray-600">
          <Link to="/login" className="text-indigo-600 hover:text-indigo-700">
            {t("resetPassword.links.backToSignIn")}
          </Link>
        </p>
      </div>
    </div>
  );
}

export default ResetPassword;
