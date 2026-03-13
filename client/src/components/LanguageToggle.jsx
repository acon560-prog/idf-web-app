import React from "react";
import { useTranslation } from "react-i18next";

export default function LanguageToggle() {
  const { i18n } = useTranslation();
  const current = i18n.resolvedLanguage?.startsWith("fr") ? "fr" : "en";

  const base =
    "px-2.5 py-1 rounded-md text-xs font-semibold border transition-colors";
  const active = "bg-indigo-500 text-white border-indigo-400";
  const inactive =
    "bg-gray-700 text-gray-200 border-gray-500 hover:bg-gray-600";

  return (
    <div
      className="inline-flex items-center gap-1"
      role="group"
      aria-label="Language switcher"
    >
      <button
        type="button"
        onClick={() => i18n.changeLanguage("en")}
        className={`${base} ${current === "en" ? active : inactive}`}
        aria-pressed={current === "en"}
      >
        EN
      </button>
      <button
        type="button"
        onClick={() => i18n.changeLanguage("fr")}
        className={`${base} ${current === "fr" ? active : inactive}`}
        aria-pressed={current === "fr"}
      >
        FR
      </button>
    </div>
  );
}