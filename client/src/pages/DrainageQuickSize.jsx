import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import ToolsShell from "../components/ToolsShell.jsx";
import {
  PIPE_MATERIAL_PRESETS,
  COMMERCIAL_DIAMETERS_M,
  rationalDischarge,
  LAND_COVER_C,
  compositeCFromCover,
  suggestPipeDiameter,
  ditchDepthTable,
  ditchGeometry,
  parseSlope,
} from "../utils/drainageQuickSize.js";

const MODES = ["rational", "pipe", "ditch"];

const N_OPTIONS = Array.from({ length: 41 }, (_, i) => ((10 + i) / 1000).toFixed(3));
const Z_OPTIONS = Array.from({ length: 36 }, (_, i) => ((i + 5) / 10).toFixed(1));
const B_OPTIONS = Array.from({ length: 31 }, (_, i) => (i / 10).toFixed(1)); // 0.0 … 3.0
const DEFAULT_DEPTHS = ["0.3", "0.4", "0.5", "0.6", "0.8", "1.0"];

const yellowFieldClass =
  "w-full rounded-md border border-amber-300 bg-[#FFF59D] px-3 py-2 font-mono text-sm text-slate-900 shadow-inner outline-none ring-amber-400/40 focus:ring-2";

function parsePositive(value, { allowZero = false } = {}) {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  if (allowZero ? n < 0 : n <= 0) return null;
  return n;
}

function formatNum(value, digits = 3) {
  if (value == null || !Number.isFinite(value)) return "—";
  return value.toFixed(digits);
}

function FieldLabel({ id, label, unit }) {
  return (
    <span className="mb-1 flex items-baseline gap-2 text-sm font-semibold text-slate-800">
      <label htmlFor={id}>{label}</label>
      {unit ? <span className="font-normal text-slate-500">{unit}</span> : null}
    </span>
  );
}

function YellowInput({ id, label, unit, value, onChange, step = "any", min, max }) {
  return (
    <div className="block">
      <FieldLabel id={id} label={label} unit={unit} />
      <input
        id={id}
        type="number"
        step={step}
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={yellowFieldClass}
      />
    </div>
  );
}

function YellowSelect({ id, label, unit, value, onChange, options, optionLabels }) {
  return (
    <div className="block">
      <FieldLabel id={id} label={label} unit={unit} />
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className={yellowFieldClass}>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {optionLabels?.[opt] ?? opt}
          </option>
        ))}
      </select>
    </div>
  );
}

function downloadText(filename, text, mime = "text/plain;charset=utf-8") {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function DitchSketch({ b, z, y, aria }) {
  const W = 420;
  const H = 220;
  const padY = 28;
  const channelTop = padY + 10;
  const channelBottom = H - padY - 24;
  const maxDepthPx = channelBottom - channelTop;
  const bVis = Math.max(8, Math.min(140, 20 + b * 60));
  const zVis = Math.max(16, Math.min(90, 16 + z * 24));
  const yMaxGuess = Math.max(y || 0.5, 0.4);
  const yVis = Math.max(6, Math.min(maxDepthPx * 0.9, ((y || 0) / yMaxGuess) * maxDepthPx * 0.85 + 10));
  const cx = W / 2;
  const yBank = channelTop;
  const yBed = channelBottom;
  const yWater = yBed - yVis;
  const bedL = cx - bVis / 2;
  const bedR = cx + bVis / 2;
  const topL = bedL - zVis;
  const topR = bedR + zVis;
  const t = yVis / (yBed - yBank || 1);
  const waterL = bedL - zVis * t;
  const waterR = bedR + zVis * t;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label={aria}>
      <defs>
        <linearGradient id="qsWater" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#7EB6D9" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#3D7EA6" stopOpacity="0.75" />
        </linearGradient>
      </defs>
      <rect x="0" y="0" width={W} height={H} fill="#F1F5F9" />
      <path
        d={`M ${waterL} ${yWater} L ${bedL} ${yBed} L ${bedR} ${yBed} L ${waterR} ${yWater} Z`}
        fill="url(#qsWater)"
      />
      <path
        d={`M ${topL} ${yBank} L ${bedL} ${yBed} L ${bedR} ${yBed} L ${topR} ${yBank}`}
        fill="none"
        stroke="#1E293B"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />
      <line x1={waterL} y1={yWater} x2={waterR} y2={yWater} stroke="#1D4E89" strokeWidth="1.5" strokeDasharray="5 3" />
      <text x={cx} y={yWater - 8} textAnchor="middle" fill="#475569" style={{ fontSize: 11, fontWeight: 600 }}>
        Tw
      </text>
      <text x={cx} y={yBed + 18} textAnchor="middle" fill="#C0392B" style={{ fontSize: 11, fontWeight: 700 }}>
        {`b=${formatNum(b, 2)}  z=${formatNum(z, 1)}  y=${formatNum(y, 2)}`}
      </text>
    </svg>
  );
}

export default function DrainageQuickSize() {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage?.startsWith("fr") ? "fr" : "en";

  const [mode, setMode] = useState("rational");

  // Shared hydraulic draft (Mode 1 → Pipe / Ditch)
  const [sharedQ, setSharedQ] = useState("0.05");
  const [sharedN, setSharedN] = useState("0.013");

  // Rational
  const [areaUnit, setAreaUnit] = useState("ha");
  const [area, setArea] = useState("0.5");
  const [cMode, setCMode] = useState("direct"); // direct | cover
  const [C, setC] = useState("0.6");
  const [roofPct, setRoofPct] = useState("20");
  const [pavePct, setPavePct] = useState("40");
  const [gravelPct, setGravelPct] = useState("0");
  const [grassPct, setGrassPct] = useState("40");
  const [woodsPct, setWoodsPct] = useState("0");
  const [intensity, setIntensity] = useState("80");

  // Pipe
  const [materialId, setMaterialId] = useState("concrete");
  const [pipeN, setPipeN] = useState("0.013");
  const [pipeQ, setPipeQ] = useState("0.05");
  const [pipeS, setPipeS] = useState("0.005");
  const [pipeSUnit, setPipeSUnit] = useState("decimal");

  // Ditch
  const [ditchQ, setDitchQ] = useState("0.05");
  const [ditchS, setDitchS] = useState("0.005");
  const [ditchSUnit, setDitchSUnit] = useState("decimal");
  const [ditchN, setDitchN] = useState("0.030");
  const [ditchZ, setDitchZ] = useState("2.0");
  const [ditchB, setDitchB] = useState("0.5");
  const [depthList, setDepthList] = useState(DEFAULT_DEPTHS.join(", "));
  const [sketchY, setSketchY] = useState("0.5");

  const effectiveC = useMemo(() => {
    if (cMode === "cover") {
      const cover = compositeCFromCover({
        roofPct: parsePositive(roofPct, { allowZero: true }) ?? 0,
        pavePct: parsePositive(pavePct, { allowZero: true }) ?? 0,
        gravelPct: parsePositive(gravelPct, { allowZero: true }) ?? 0,
        grassPct: parsePositive(grassPct, { allowZero: true }) ?? 0,
        woodsPct: parsePositive(woodsPct, { allowZero: true }) ?? 0,
      });
      return cover;
    }
    const cVal = parsePositive(C);
    return { C: cVal, sum: null, error: cVal == null ? "invalid_input" : null };
  }, [cMode, C, roofPct, pavePct, gravelPct, grassPct, woodsPct]);

  const rational = useMemo(() => {
    const A = parsePositive(area);
    const i = parsePositive(intensity);
    if (effectiveC.C == null || A == null || i == null) {
      return { Q: null, error: "invalid_input" };
    }
    return rationalDischarge({ C: effectiveC.C, i_mm_h: i, A, areaUnit });
  }, [effectiveC, area, intensity, areaUnit]);

  const pipeResult = useMemo(() => {
    const Q = parsePositive(pipeQ);
    const S = parseSlope(pipeS, pipeSUnit);
    const n = parsePositive(pipeN);
    return suggestPipeDiameter({ Q, n, S, diameters: COMMERCIAL_DIAMETERS_M });
  }, [pipeQ, pipeS, pipeSUnit, pipeN]);

  const ditchResult = useMemo(() => {
    const Q = parsePositive(ditchQ);
    const S = parseSlope(ditchS, ditchSUnit);
    const n = parsePositive(ditchN);
    const b = parsePositive(ditchB, { allowZero: true });
    const z = parsePositive(ditchZ, { allowZero: true });
    const depths = depthList
      .split(/[,;\s]+/)
      .map((s) => s.trim())
      .filter(Boolean)
      .map(Number)
      .filter((y) => Number.isFinite(y) && y > 0);
    return ditchDepthTable({ Q, S, n, b: b ?? 0, z: z ?? 0, depths });
  }, [ditchQ, ditchS, ditchSUnit, ditchN, ditchB, ditchZ, depthList]);

  const sketchDepth = parsePositive(sketchY) ?? ditchResult.rows[0]?.y ?? 0.5;
  const sketchGeo = ditchGeometry(
    parsePositive(ditchB, { allowZero: true }) ?? 0.5,
    parsePositive(ditchZ, { allowZero: true }) ?? 2,
    sketchDepth
  );

  const applyRationalQ = () => {
    if (rational.Q == null) return;
    const qStr = rational.Q.toFixed(4);
    setSharedQ(qStr);
    setPipeQ(qStr);
    setDitchQ(qStr);
    setMode("pipe");
  };

  const syncSharedToPipe = () => {
    setPipeQ(sharedQ);
    setPipeN(sharedN);
  };

  const onMaterialChange = (id) => {
    setMaterialId(id);
    const preset = PIPE_MATERIAL_PRESETS.find((p) => p.id === id);
    if (preset?.n != null) {
      setPipeN(preset.n.toFixed(3));
      setSharedN(preset.n.toFixed(3));
    }
  };

  const exportRational = () => {
    const lines = [
      "Drainage Quick Size — Rational Q",
      `C,${formatNum(effectiveC.C, 3)}`,
      `i_mm_h,${intensity}`,
      `A,${area},${areaUnit}`,
      `Q_m3s,${formatNum(rational.Q, 4)}`,
    ];
    downloadText("rational-Q.csv", lines.join("\n"), "text/csv;charset=utf-8");
  };

  const exportPipe = () => {
    const header = "D_m,Qp_m3s,V_m_s,OK";
    const rows = (pipeResult.candidates || []).map(
      (c) => `${c.D},${formatNum(c.Qp, 4)},${formatNum(c.V, 3)},${c.ok ? "OK" : "NO"}`
    );
    downloadText(
      "pipe-sizing.csv",
      [header, ...rows, "", `suggested_D,${pipeResult.D}`, `design_Q,${pipeQ}`].join("\n"),
      "text/csv;charset=utf-8"
    );
  };

  const exportDitch = () => {
    const header = "y_m,x_m,Tw_m,A_m2,V_m_s,Qcap_m3s,OK";
    const rows = ditchResult.rows.map(
      (r) =>
        `${formatNum(r.y, 3)},${formatNum(r.x, 3)},${formatNum(r.Tw, 3)},${formatNum(r.A, 3)},${formatNum(r.V, 3)},${formatNum(r.Qcap, 4)},${r.ok ? "OK" : "NO"}`
    );
    downloadText("ditch-table.csv", [header, ...rows].join("\n"), "text/csv;charset=utf-8");
  };

  return (
    <ToolsShell>
      <div className="mx-auto max-w-6xl px-4 pb-12 md:px-8">
        <motion.header
          className="mb-6 max-w-3xl"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <p className="text-sm font-medium tracking-wide text-slate-500">{t("quickSize.eyebrow")}</p>
          <h1 className="mt-1 font-serif text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            {t("quickSize.title")}
          </h1>
          <p className="mt-3 text-base text-slate-600">{t("quickSize.subtitle")}</p>
          <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
            {t("quickSize.disclaimer")}
          </p>
        </motion.header>

        <div className="mb-5 flex flex-wrap gap-2" role="tablist" aria-label={t("quickSize.modesLabel")}>
          {MODES.map((m) => {
            const active = mode === m;
            return (
              <button
                key={m}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => setMode(m)}
                className={`rounded-md border px-3 py-1.5 text-sm font-medium transition ${
                  active
                    ? "border-teal-800 bg-[var(--qs-accent)] text-white"
                    : "border-slate-300 bg-white text-slate-700 hover:border-teal-500"
                }`}
              >
                {t(`quickSize.modes.${m}`)}
              </button>
            );
          })}
        </div>

        {mode === "rational" && (
          <motion.div
            className="grid gap-6 lg:grid-cols-2"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
          >
            <div className="rounded-xl border border-slate-200 bg-white/90 p-5 shadow-sm">
              <div className="mb-4 flex items-center justify-between gap-2">
                <h2 className="text-lg font-semibold text-slate-900">{t("quickSize.inputsTitle")}</h2>
                <span className="rounded bg-[#FFF59D] px-2 py-0.5 text-xs font-medium text-slate-700">
                  {t("quickSize.yellowHint")}
                </span>
              </div>

              <div className="mb-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setAreaUnit("ha")}
                  className={`rounded-md border px-2.5 py-1 text-xs font-semibold ${
                    areaUnit === "ha" ? "border-teal-700 bg-teal-800 text-white" : "border-slate-300"
                  }`}
                >
                  ha
                </button>
                <button
                  type="button"
                  onClick={() => setAreaUnit("m2")}
                  className={`rounded-md border px-2.5 py-1 text-xs font-semibold ${
                    areaUnit === "m2" ? "border-teal-700 bg-teal-800 text-white" : "border-slate-300"
                  }`}
                >
                  m²
                </button>
              </div>

              <div className="space-y-3">
                <YellowInput
                  id="qs-A"
                  label="A"
                  unit={areaUnit === "ha" ? "ha" : "m²"}
                  value={area}
                  onChange={setArea}
                  step="0.001"
                  min="0"
                />
                <YellowInput
                  id="qs-i"
                  label="i"
                  unit="mm/h"
                  value={intensity}
                  onChange={setIntensity}
                  step="0.1"
                  min="0"
                />
              </div>

              <div className="mt-4 border-t border-slate-100 pt-4">
                <p className="mb-2 text-sm font-semibold text-slate-800">{t("quickSize.cSource")}</p>
                <div className="mb-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => setCMode("direct")}
                    className={`rounded-md border px-2.5 py-1 text-xs font-semibold ${
                      cMode === "direct" ? "border-teal-700 bg-teal-800 text-white" : "border-slate-300"
                    }`}
                  >
                    {t("quickSize.cDirect")}
                  </button>
                  <button
                    type="button"
                    onClick={() => setCMode("cover")}
                    className={`rounded-md border px-2.5 py-1 text-xs font-semibold ${
                      cMode === "cover" ? "border-teal-700 bg-teal-800 text-white" : "border-slate-300"
                    }`}
                  >
                    {t("quickSize.cCover")}
                  </button>
                </div>
                {cMode === "direct" ? (
                  <YellowInput id="qs-C" label="C" unit="—" value={C} onChange={setC} step="0.01" min="0" max="1" />
                ) : (
                  <div className="space-y-4">
                    <p className="text-xs leading-relaxed text-slate-600">{t("quickSize.weightedCHelp")}</p>
                    <div>
                      <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-700">
                        {t("quickSize.imperviousGroup")}
                      </p>
                      <div className="grid gap-3 sm:grid-cols-3">
                        <YellowInput
                          id="qs-roof"
                          label={`${t("quickSize.roof")} (C=${LAND_COVER_C.roof})`}
                          unit="%"
                          value={roofPct}
                          onChange={setRoofPct}
                          step="1"
                          min="0"
                        />
                        <YellowInput
                          id="qs-pave"
                          label={`${t("quickSize.pave")} (C=${LAND_COVER_C.pave})`}
                          unit="%"
                          value={pavePct}
                          onChange={setPavePct}
                          step="1"
                          min="0"
                        />
                        <YellowInput
                          id="qs-gravel"
                          label={`${t("quickSize.gravel")} (C≈${LAND_COVER_C.gravel})`}
                          unit="%"
                          value={gravelPct}
                          onChange={setGravelPct}
                          step="1"
                          min="0"
                        />
                      </div>
                    </div>
                    <div>
                      <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-700">
                        {t("quickSize.perviousGroup")}
                      </p>
                      <div className="grid gap-3 sm:grid-cols-2">
                        <YellowInput
                          id="qs-grass"
                          label={`${t("quickSize.grass")} (C=${LAND_COVER_C.grass})`}
                          unit="%"
                          value={grassPct}
                          onChange={setGrassPct}
                          step="1"
                          min="0"
                        />
                        <YellowInput
                          id="qs-woods"
                          label={`${t("quickSize.woods")} (C=${LAND_COVER_C.woods})`}
                          unit="%"
                          value={woodsPct}
                          onChange={setWoodsPct}
                          step="1"
                          min="0"
                        />
                      </div>
                    </div>
                    <p className="text-xs text-slate-500">
                      {t("quickSize.coverSum")}:{" "}
                      <span className="font-mono font-semibold text-slate-800">
                        {formatNum(effectiveC.sum, 0)}%
                      </span>
                      {effectiveC.sum != null && Math.abs(effectiveC.sum - 100) > 0.5 ? (
                        <span className="ml-1 text-amber-700">({t("quickSize.coverSumHint")})</span>
                      ) : null}
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white/90 p-5 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-900">{t("quickSize.outputsTitle")}</h2>
              <dl className="mt-4 space-y-3 text-sm">
                <div>
                  <dt className="text-slate-500">
                    {cMode === "cover" ? t("quickSize.weightedCLabel") : "C"}
                  </dt>
                  <dd className="font-mono text-xl font-bold text-slate-900">{formatNum(effectiveC.C, 3)}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Q</dt>
                  <dd className="font-mono text-2xl font-bold text-[var(--qs-flow)]">
                    {formatNum(rational.Q, 4)} <span className="text-base font-semibold text-slate-600">m³/s</span>
                  </dd>
                </div>
                <p className="text-xs text-slate-500">{t("quickSize.rationalNote")}</p>
              </dl>
              <div className="mt-6 flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={rational.Q == null}
                  onClick={applyRationalQ}
                  className="rounded-md bg-[var(--qs-accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
                >
                  {t("quickSize.useInPipe")}
                </button>
                <button
                  type="button"
                  disabled={rational.Q == null}
                  onClick={exportRational}
                  className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 disabled:opacity-40"
                >
                  {t("quickSize.exportSummary")}
                </button>
              </div>
            </div>
          </motion.div>
        )}

        {mode === "pipe" && (
          <motion.div
            className="grid gap-6 lg:grid-cols-2"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
          >
            <div className="rounded-xl border border-slate-200 bg-white/90 p-5 shadow-sm">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-lg font-semibold text-slate-900">{t("quickSize.inputsTitle")}</h2>
                <button
                  type="button"
                  onClick={syncSharedToPipe}
                  className="text-xs font-semibold text-teal-800 underline"
                >
                  {t("quickSize.useSharedQ")} ({sharedQ} m³/s)
                </button>
              </div>
              <div className="space-y-3">
                <YellowInput id="pipe-Q" label="Q" unit="m³/s" value={pipeQ} onChange={setPipeQ} step="0.001" min="0" />
                <div className="grid gap-3 sm:grid-cols-2">
                  <YellowInput
                    id="pipe-S"
                    label="S"
                    unit={pipeSUnit === "percent" ? "%" : "m/m"}
                    value={pipeS}
                    onChange={setPipeS}
                    step="0.001"
                    min="0"
                  />
                  <YellowSelect
                    id="pipe-Sunit"
                    label={t("quickSize.slopeUnit")}
                    value={pipeSUnit}
                    onChange={setPipeSUnit}
                    options={["decimal", "percent"]}
                    optionLabels={{ decimal: "m/m", percent: "%" }}
                  />
                </div>
                <YellowSelect
                  id="pipe-mat"
                  label={t("quickSize.material")}
                  value={materialId}
                  onChange={onMaterialChange}
                  options={PIPE_MATERIAL_PRESETS.map((p) => p.id)}
                  optionLabels={Object.fromEntries(
                    PIPE_MATERIAL_PRESETS.map((p) => [p.id, t(`quickSize.materials.${p.labelKey}`)])
                  )}
                />
                <YellowSelect
                  id="pipe-n"
                  label="n"
                  unit={t("quickSize.manningN")}
                  value={pipeN}
                  onChange={(v) => {
                    setPipeN(v);
                    setMaterialId("custom");
                  }}
                  options={N_OPTIONS}
                />
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white/90 p-5 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-900">{t("quickSize.outputsTitle")}</h2>
              {pipeResult.error === "invalid_input" ? (
                <p className="mt-3 text-sm text-rose-700">{t("quickSize.invalid")}</p>
              ) : (
                <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <dt className="text-slate-500">{t("quickSize.minD")}</dt>
                    <dd className="font-mono text-xl font-bold text-slate-900">
                      {pipeResult.D != null ? `${Math.round(pipeResult.D * 1000)} mm` : "—"}
                    </dd>
                    <dd className="font-mono text-xs text-slate-500">{formatNum(pipeResult.D, 3)} m</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Qp</dt>
                    <dd className="font-mono text-lg font-bold text-[var(--qs-flow)]">
                      {formatNum(pipeResult.Qp, 4)} m³/s
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">V</dt>
                    <dd className="font-mono font-semibold text-slate-800">{formatNum(pipeResult.V, 3)} m/s</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">{t("quickSize.status")}</dt>
                    <dd
                      className={`font-semibold ${
                        pipeResult.ok ? "text-[var(--qs-ok)]" : "text-[var(--qs-warn)]"
                      }`}
                    >
                      {pipeResult.ok ? t("quickSize.ok") : t("quickSize.increaseD")}
                    </dd>
                  </div>
                </dl>
              )}
              <button
                type="button"
                onClick={exportPipe}
                className="mt-6 rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800"
              >
                {t("quickSize.exportTable")}
              </button>
              <p className="mt-3 text-xs text-slate-500">{t("quickSize.pipeNote")}</p>
            </div>
          </motion.div>
        )}

        {mode === "ditch" && (
          <motion.div
            className="grid gap-6 lg:grid-cols-2"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
          >
            <div className="rounded-xl border border-slate-200 bg-white/90 p-5 shadow-sm">
              <h2 className="mb-4 text-lg font-semibold text-slate-900">{t("quickSize.inputsTitle")}</h2>
              <div className="space-y-3">
                <YellowInput id="ditch-Q" label="Q" unit="m³/s" value={ditchQ} onChange={setDitchQ} step="0.001" min="0" />
                <div className="grid gap-3 sm:grid-cols-2">
                  <YellowInput
                    id="ditch-S"
                    label="S"
                    unit={ditchSUnit === "percent" ? "%" : "m/m"}
                    value={ditchS}
                    onChange={setDitchS}
                    step="0.001"
                    min="0"
                  />
                  <YellowSelect
                    id="ditch-Sunit"
                    label={t("quickSize.slopeUnit")}
                    value={ditchSUnit}
                    onChange={setDitchSUnit}
                    options={["decimal", "percent"]}
                    optionLabels={{ decimal: "m/m", percent: "%" }}
                  />
                </div>
                <YellowSelect
                  id="ditch-n"
                  label="n"
                  unit={t("quickSize.manningN")}
                  value={ditchN}
                  onChange={setDitchN}
                  options={N_OPTIONS}
                />
                <div className="grid gap-3 sm:grid-cols-2">
                  <YellowSelect
                    id="ditch-z"
                    label="z"
                    unit={`H:V — ${t("quickSize.sideSlope")}`}
                    value={ditchZ}
                    onChange={setDitchZ}
                    options={Z_OPTIONS}
                  />
                  <YellowSelect
                    id="ditch-b"
                    label="b"
                    unit={`m — ${t("quickSize.bottomWidth")}`}
                    value={ditchB}
                    onChange={setDitchB}
                    options={B_OPTIONS}
                  />
                </div>
                <div>
                  <FieldLabel id="ditch-ys" label={t("quickSize.depthList")} unit="m" />
                  <input
                    id="ditch-ys"
                    type="text"
                    value={depthList}
                    onChange={(e) => setDepthList(e.target.value)}
                    className={yellowFieldClass}
                    placeholder="0.3, 0.4, 0.5, 0.6"
                  />
                </div>
                <YellowInput
                  id="ditch-sketch-y"
                  label={t("quickSize.sketchDepth")}
                  unit="m"
                  value={sketchY}
                  onChange={setSketchY}
                  step="0.05"
                  min="0"
                />
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white/90 p-5 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-slate-900">{t("quickSize.outputsTitle")}</h2>
              <div className="mb-4 overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
                <DitchSketch
                  b={parsePositive(ditchB, { allowZero: true }) ?? 0.5}
                  z={parsePositive(ditchZ, { allowZero: true }) ?? 2}
                  y={sketchDepth}
                  aria={t("quickSize.sketchAria")}
                />
              </div>
              <p className="mb-2 text-xs text-slate-500">
                Tw ≈ {formatNum(sketchGeo.topWidth, 3)} m · x ≈ {formatNum(sketchGeo.sideRun, 3)} m
              </p>
              <div className="max-h-64 overflow-auto rounded-md border border-slate-200">
                <table className="min-w-full text-left text-xs">
                  <thead className="sticky top-0 bg-slate-100 font-semibold text-slate-700">
                    <tr>
                      <th className="px-2 py-1.5">y</th>
                      <th className="px-2 py-1.5">x</th>
                      <th className="px-2 py-1.5">Tw</th>
                      <th className="px-2 py-1.5">V</th>
                      <th className="px-2 py-1.5">Qcap</th>
                      <th className="px-2 py-1.5">OK</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ditchResult.rows.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-2 py-3 text-slate-500">
                          {t("quickSize.invalid")}
                        </td>
                      </tr>
                    ) : (
                      ditchResult.rows.map((r) => (
                        <tr key={r.y} className="border-t border-slate-100 font-mono">
                          <td className="px-2 py-1">{formatNum(r.y, 2)}</td>
                          <td className="px-2 py-1">{formatNum(r.x, 3)}</td>
                          <td className="px-2 py-1">{formatNum(r.Tw, 3)}</td>
                          <td className="px-2 py-1">{formatNum(r.V, 3)}</td>
                          <td className="px-2 py-1">{formatNum(r.Qcap, 4)}</td>
                          <td className={`px-2 py-1 font-sans font-semibold ${r.ok ? "text-[var(--qs-ok)]" : "text-[var(--qs-warn)]"}`}>
                            {r.ok ? "OK" : "—"}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              <button
                type="button"
                onClick={exportDitch}
                disabled={ditchResult.rows.length === 0}
                className="mt-4 rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 disabled:opacity-40"
              >
                {t("quickSize.exportTableFigure")}
              </button>
              <p className="mt-3 text-xs text-slate-500">{t("quickSize.ditchNote")}</p>
            </div>
          </motion.div>
        )}

        <p className="mt-8 text-center text-sm text-slate-500">
          <Link to="/" className="underline hover:text-slate-800">
            {lang === "fr" ? "Retour à l’accueil" : "Back to home"}
          </Link>
          <span className="mx-2">·</span>
          <span className="font-mono text-xs">/tools</span>
        </p>
      </div>
    </ToolsShell>
  );
}
