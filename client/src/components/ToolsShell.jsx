import React from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

/**
 * Shared chrome for drainage tools: Quick Size (default) + Normal Depth.
 */
export default function ToolsShell({ children }) {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const quickSizeActive = pathname === "/tools" || pathname === "/tools/quick-size";

  const tabClass = (active) =>
    `rounded-md px-3 py-1.5 text-sm font-semibold transition ${
      active
        ? "bg-sky-800 text-white"
        : "border border-slate-300 bg-white text-slate-700 hover:border-sky-400"
    }`;

  return (
    <div className="tools-shell min-h-[calc(100vh-8rem)] bg-gradient-to-b from-slate-100 via-teal-50/30 to-slate-100">
      <style>{`
        .tools-shell {
          --qs-ink: #0f172a;
          --qs-accent: #0f5c5c;
          --qs-flow: #1d6a8a;
          --qs-ok: #1e8449;
          --qs-warn: #b45309;
        }
      `}</style>
      <div className="mx-auto max-w-6xl px-4 pt-8 md:px-8">
        <div className="mb-6 flex flex-wrap items-center gap-2" role="navigation" aria-label={t("tools.hubNav")}>
          <NavLink to="/tools" className={tabClass(quickSizeActive)} aria-current={quickSizeActive ? "page" : undefined}>
            {t("tools.quickSizeTab")}
          </NavLink>
          <NavLink to="/tools/normal-depth" className={({ isActive }) => tabClass(isActive)}>
            {t("tools.normalDepthTab")}
          </NavLink>
        </div>
      </div>
      {children}
    </div>
  );
}
