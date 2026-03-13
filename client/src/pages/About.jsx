import React from 'react';
import { motion } from 'framer-motion';
import { useTranslation } from "react-i18next";

function About() {
  const { t } = useTranslation();
  return (
    <motion.div
      className="p-4"
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}   // ← changed this
      transition={{ duration: 0.8 }}
    >
      <div className="max-w-2xl w-full">
        <h2 className="text-3xl font-bold text-slate-900">{t("about.title")}</h2>
        <p className="mt-4 text-lg text-slate-700 leading-relaxed">
         {t("about.intro")}
        </p>
      </div>
 
      <div className="mt-8 max-w-2xl border-l-4 border-indigo-500 pl-6">
        <section className="pb-5">
          <h3 className="text-xl font-semibold text-slate-900">{t("about.capabilitiesTitle")}</h3>
          <ul className="mt-3 list-disc space-y-1 pl-6 text-slate-700">
            <li>{t("about.capabilities.aqueduct")}</li>
            <li>{t("about.capabilities.hydrology")}</li>
            <li>{t("about.capabilities.grading")}</li>
          </ul>
        </section>
      </div>  
    </motion.div>
  );
}

export default About;

