import React from "react";
import { useTranslation } from "react-i18next";

function Disclaimer() {
  const { t } = useTranslation();

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-3xl font-bold mb-4">{t("disclaimer.title")}</h1>
      <p className="text-slate-700 mb-6">{t("disclaimer.shortNotice")}</p>

      <section className="mb-5">
        <h2 className="text-xl font-semibold">{t("disclaimer.sections.purpose.title")}</h2>
        <p className="text-slate-700">{t("disclaimer.sections.purpose.body")}</p>
      </section>
    </div>
  );
}

export default Disclaimer;