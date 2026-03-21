import React from "react";
import { motion } from "framer-motion";
import permitImg from '../assets/permit-drawings.jpg';
import gradingImg from '../assets/grading-drainage.jpg';
import { useTranslation } from "react-i18next";
function Services() {
  const { t } = useTranslation();
  return (
    <motion.div
      className="mx-auto max-w-6xl px-4 py-16 md:px-8"
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8 }}
    >
      <div className="mx-auto max-w-3xl text-center">
        <h2 className="text-3xl font-bold text-slate-900 sm:text-4xl">{t("services.title")}</h2>
        <p className="mt-4 text-lg text-slate-600">
          {t("services.intro")}
        </p>
      </div>
      
      <div className="mt-12 grid gap-8 md:grid-cols-2">
        {/*}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-xl font-semibold text-slate-900">{t("services.structural.title")}</h3>
          <p className="mt-3 text-sm text-slate-600">
            {t("services.structural.description")}
          </p>
          <ul className="mt-4 space-y-2 text-sm text-slate-600">
            <li className="flex gap-2">
              <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
              <span>{t("services.structural.bullets.memberSizing")}</span>
            </li>
            <li className="flex gap-2">
              <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
              <span>{t("services.structural.bullets.foundationChecks")}</span>
            </li>
            <li className="flex gap-2">
              <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
              <span>{t("services.structural.bullets.retrofit")}</span>
            </li>
          </ul>
        </section>
        */}  
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-xl font-semibold text-slate-900">{t("services.permit.title")}</h3>
          <p className="mt-3 text-sm text-slate-600">
            {t("services.permit.description")}
          </p>
          <div className="mt-4 overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
            
           
              <img
                src={permitImg}
                alt={t("services.permit.imageAlt")}
                className="h-48 w-full object-cover"
              />
            
          </div>
          <ul className="mt-4 space-y-2 text-sm text-slate-600">
            <li className="flex gap-2">
              <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
              <span>{t("services.permit.bullets.notesDetails")}</span>
            </li>
            <li className="flex gap-2">
              <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
              <span>{t("services.permit.bullets.coordination")}</span>
            </li>
            <li className="flex gap-2">
              <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
              <span>{t("services.permit.bullets.revisions")}</span>
            </li>
          </ul>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-xl font-semibold text-slate-900">{t("services.grading.title")}</h3>
          <p className="mt-3 text-sm text-slate-600">
            {t("services.grading.description")}
          </p>
          <div className="mt-4 overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
            
					    <img
						    src={gradingImg}
						    alt={t("services.grading.imageAlt")}
						    className="h-48 w-full object-cover"
			      />
		        
          </div>
          <ul className="mt-4 space-y-2 text-sm text-slate-600">
            <li className="flex gap-2">
              <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
              <span>{t("services.grading.bullets.spotElevations")}</span>
            </li>
            <li className="flex gap-2">
              <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
              <span>{t("services.grading.bullets.catchBasins")}</span>
            </li>
            <li className="flex gap-2">
              <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" />
              <span>{t("services.grading.bullets.erosionControl")}</span>
            </li>
          </ul>
        </section>
      </div>

      <div className="mt-12 rounded-2xl border border-slate-200 bg-slate-50 p-6">
        <h3 className="text-lg font-semibold text-slate-900">{t("services.sitePlanning.title")}</h3>
        <p className="mt-2 text-sm text-slate-600">
          {t("services.sitePlanning.description")}
        </p>
      </div>
    </motion.div>
  );
}

export default Services;
