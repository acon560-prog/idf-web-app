import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { solveNormalDepth } from "../utils/normalDepth.js";

const DEFAULTS = {
  Q: "3.598",
  S0: "0.0173",
  n: "0.030",
  b: "0.50",
  z: "2",
};

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

/** Live trapezoid cross-section SVG; scales with b, z, yn */
function TrapezoidSketch({ b, z, yn, Q, n, S0, labels }) {
  const padY = 36;
  const W = 420;
  const H = 280;
  const channelTop = padY + 18;
  const channelBottom = H - padY - 28;
  const maxDepthPx = channelBottom - channelTop;

  // Visual proportions (not 1:1 engineering scale — readable sketch)
  const bVis = Math.max(40, Math.min(160, 40 + b * 80));
  const zVis = Math.max(20, Math.min(100, 20 + z * 28));
  const yMaxGuess = Math.max(yn || 0.5, 0.4);
  const yVis = Math.max(8, Math.min(maxDepthPx * 0.92, ((yn || 0) / yMaxGuess) * maxDepthPx * 0.85 + 12));

  const cx = W / 2;
  const yBank = channelTop;
  const yBed = channelBottom;
  const yWater = yBed - yVis;

  const bedL = cx - bVis / 2;
  const bedR = cx + bVis / 2;
  const topL = bedL - zVis;
  const topR = bedR + zVis;

  // Water surface intersects side slopes
  const t = yVis / (yBed - yBank || 1);
  const waterL = bedL - zVis * t;
  const waterR = bedR + zVis * t;

  const channelPath = `M ${topL} ${yBank} L ${bedL} ${yBed} L ${bedR} ${yBed} L ${topR} ${yBank}`;
  const waterPath = `M ${waterL} ${yWater} L ${bedL} ${yBed} L ${bedR} ${yBed} L ${waterR} ${yWater} Z`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label={labels.sketchAria}>
      <defs>
        <linearGradient id="ndWater" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#7EB6D9" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#3D7EA6" stopOpacity="0.75" />
        </linearGradient>
        <pattern id="ndHatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(35)">
          <line x1="0" y1="0" x2="0" y2="8" stroke="#94A3B8" strokeWidth="1.2" />
        </pattern>
      </defs>

      {/* Ground / banks */}
      <rect x="0" y="0" width={W} height={H} fill="#F1F5F9" />
      <path d={`M 0 ${yBank + 8} L ${topL} ${yBank} L ${bedL} ${yBed} L ${bedR} ${yBed} L ${topR} ${yBank} L ${W} ${yBank + 8} L ${W} ${H} L 0 ${H} Z`} fill="url(#ndHatch)" opacity="0.35" />
      <path d={`M 0 ${yBank + 8} L ${topL} ${yBank} L ${bedL} ${yBed} L ${bedR} ${yBed} L ${topR} ${yBank} L ${W} ${yBank + 8} L ${W} ${H} L 0 ${H} Z`} fill="#E2E8F0" opacity="0.5" />

      {/* Water */}
      <motion.path
        d={waterPath}
        fill="url(#ndWater)"
        initial={false}
        animate={{ d: waterPath }}
        transition={{ type: "spring", stiffness: 120, damping: 18 }}
      />

      {/* Channel outline */}
      <path d={channelPath} fill="none" stroke="#1E293B" strokeWidth="2.5" strokeLinejoin="round" />

      {/* Water surface line */}
      <line x1={waterL} y1={yWater} x2={waterR} y2={yWater} stroke="#1D4E89" strokeWidth="1.5" strokeDasharray="5 3" />

      {/* Tw label */}
      <line x1={waterL} y1={yWater - 14} x2={waterR} y2={yWater - 14} stroke="#475569" strokeWidth="1" />
      <text x={cx} y={yWater - 18} textAnchor="middle" className="fill-slate-600" style={{ fontSize: 11, fontWeight: 600 }}>
        Tw
      </text>

      {/* b dimension */}
      <line x1={bedL} y1={yBed + 14} x2={bedR} y2={yBed + 14} stroke="#C0392B" strokeWidth="1.5" />
      <line x1={bedL} y1={yBed + 10} x2={bedL} y2={yBed + 18} stroke="#C0392B" strokeWidth="1.5" />
      <line x1={bedR} y1={yBed + 10} x2={bedR} y2={yBed + 18} stroke="#C0392B" strokeWidth="1.5" />
      <text x={cx} y={yBed + 28} textAnchor="middle" fill="#C0392B" style={{ fontSize: 12, fontWeight: 700 }}>
        b
      </text>

      {/* yn arrow */}
      <line x1={bedL - 22} y1={yBed} x2={bedL - 22} y2={yWater} stroke="#1E8449" strokeWidth="1.5" markerEnd="url(#ndArrow)" />
      <polygon points={`${bedL - 22},${yWater} ${bedL - 26},${yWater + 8} ${bedL - 18},${yWater + 8}`} fill="#1E8449" />
      <polygon points={`${bedL - 22},${yBed} ${bedL - 26},${yBed - 8} ${bedL - 18},${yBed - 8}`} fill="#1E8449" />
      <text x={bedL - 30} y={(yBed + yWater) / 2 + 4} textAnchor="end" fill="#1E8449" style={{ fontSize: 12, fontWeight: 700 }}>
        yn
      </text>

      {/* z on side slope */}
      <text x={(bedR + topR) / 2 + 8} y={(yBed + yBank) / 2} fill="#6C3483" style={{ fontSize: 12, fontWeight: 700 }}>
        z
      </text>

      {/* Flow params as text */}
      <text x={16} y={20} fill="#334155" style={{ fontSize: 11, fontFamily: "ui-monospace, monospace" }}>
        {`Q = ${formatNum(Q, 3)} m³/s`}
      </text>
      <text x={16} y={36} fill="#334155" style={{ fontSize: 11, fontFamily: "ui-monospace, monospace" }}>
        {`n = ${formatNum(n, 3)}   S₀ = ${formatNum(S0, 4)}`}
      </text>
    </svg>
  );
}

function YellowInput({ id, label, unit, value, onChange, accent }) {
  return (
    <label htmlFor={id} className="block">
      <span className="mb-1 flex items-baseline gap-2 text-sm font-semibold text-slate-800">
        <span
          className="inline-block h-2.5 w-2.5 rounded-sm"
          style={{ backgroundColor: accent }}
          aria-hidden
        />
        {label}
        {unit ? <span className="font-normal text-slate-500">{unit}</span> : null}
      </span>
      <input
        id={id}
        type="number"
        step="any"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-amber-300 bg-[#FFF59D] px-3 py-2 font-mono text-sm text-slate-900 shadow-inner outline-none ring-amber-400/40 focus:ring-2"
      />
    </label>
  );
}

export default function NormalDepth() {
  const { t, i18n } = useTranslation();
  const [inputs, setInputs] = useState(DEFAULTS);
  // Calculate once with defaults so the preview shows yn immediately
  const [submitted, setSubmitted] = useState(DEFAULTS);

  const parsed = useMemo(() => {
    const Q = parsePositive(submitted.Q);
    const S0 = parsePositive(submitted.S0);
    const n = parsePositive(submitted.n);
    const b = parsePositive(submitted.b, { allowZero: true });
    const z = parsePositive(submitted.z, { allowZero: true });
    return { Q, S0, n, b, z };
  }, [submitted]);

  const result = useMemo(() => {
    if ([parsed.Q, parsed.S0, parsed.n, parsed.b, parsed.z].some((v) => v == null)) {
      return { yn: null, converged: false, error: "invalid_input" };
    }
    return solveNormalDepth(parsed);
  }, [parsed]);

  // Live sketch uses current form values (preview) with last calculated yn
  const live = useMemo(() => {
    const Q = parsePositive(inputs.Q) ?? parsed.Q ?? 0;
    const S0 = parsePositive(inputs.S0) ?? parsed.S0 ?? 0;
    const n = parsePositive(inputs.n) ?? parsed.n ?? 0;
    const b = parsePositive(inputs.b, { allowZero: true }) ?? parsed.b ?? 0.5;
    const z = parsePositive(inputs.z, { allowZero: true }) ?? parsed.z ?? 1;
    return { Q, S0, n, b, z };
  }, [inputs, parsed]);

  const setField = (key) => (value) => setInputs((prev) => ({ ...prev, [key]: value }));

  const onCalculate = (e) => {
    e.preventDefault();
    setSubmitted({ ...inputs });
  };

  const lang = i18n.resolvedLanguage?.startsWith("fr") ? "fr" : "en";

  return (
    <div className="nd-page min-h-[calc(100vh-8rem)] bg-gradient-to-b from-slate-100 via-sky-50/40 to-slate-100">
      <style>{`
        .nd-page {
          --nd-ink: #0f172a;
          --nd-accent: #1d4e89;
          --nd-b: #c0392b;
          --nd-z: #6c3483;
          --nd-yn: #1e8449;
          --nd-flow: #2471a3;
        }
      `}</style>

      <div className="mx-auto max-w-6xl px-4 py-10 md:px-8">
        <motion.header
          className="mb-8 max-w-3xl"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
        >
          <p className="text-sm font-medium tracking-wide text-slate-500">
            {t("normalDepth.eyebrow")}
          </p>
          <h1 className="mt-1 font-serif text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            {t("normalDepth.title")}
          </h1>
          <p className="mt-3 text-base text-slate-600">{t("normalDepth.subtitle")}</p>
          <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
            {t("normalDepth.disclaimer")}
          </p>
        </motion.header>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* INPUTS */}
          <motion.form
            onSubmit={onCalculate}
            className="rounded-xl border border-slate-200 bg-white/90 p-5 shadow-sm backdrop-blur"
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.45, delay: 0.05 }}
          >
            <div className="mb-4 flex items-center justify-between gap-2">
              <h2 className="text-lg font-semibold text-slate-900">{t("normalDepth.inputsTitle")}</h2>
              <span className="rounded bg-[#FFF59D] px-2 py-0.5 text-xs font-medium text-slate-700">
                {t("normalDepth.yellowHint")}
              </span>
            </div>

            <fieldset className="space-y-3">
              <YellowInput
                id="nd-Q"
                label="Q"
                unit="m³/s"
                value={inputs.Q}
                onChange={setField("Q")}
                accent="var(--nd-flow)"
              />
              <YellowInput
                id="nd-S0"
                label="S₀"
                unit="m/m"
                value={inputs.S0}
                onChange={setField("S0")}
                accent="var(--nd-flow)"
              />
              <YellowInput
                id="nd-n"
                label="n"
                unit={t("normalDepth.manningN")}
                value={inputs.n}
                onChange={setField("n")}
                accent="var(--nd-flow)"
              />
            </fieldset>

            <div className="my-5 border-t border-slate-100 pt-4">
              <p className="mb-3 text-sm font-semibold text-slate-800">
                {t("normalDepth.section")}{" "}
                <span className="font-normal text-slate-500">({t("normalDepth.trapezoid")})</span>
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                <YellowInput
                  id="nd-b"
                  label="b"
                  unit={`m — ${t("normalDepth.bottomWidth")}`}
                  value={inputs.b}
                  onChange={setField("b")}
                  accent="var(--nd-b)"
                />
                <YellowInput
                  id="nd-z"
                  label="z"
                  unit={`H:V — ${t("normalDepth.sideSlope")}`}
                  value={inputs.z}
                  onChange={setField("z")}
                  accent="var(--nd-z)"
                />
              </div>
            </div>

            <button
              type="submit"
              className="mt-2 w-full rounded-md bg-[var(--nd-accent)] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-sky-900 focus:outline-none focus:ring-2 focus:ring-sky-400"
            >
              {t("normalDepth.calculate")}
            </button>

            <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t("normalDepth.results")}
              </p>
              {result.error === "invalid_input" ? (
                <p className="mt-2 text-sm text-rose-700">{t("normalDepth.invalid")}</p>
              ) : (
                <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-slate-500">yn</dt>
                    <dd className="font-mono text-lg font-bold text-[var(--nd-yn)]">
                      {formatNum(result.yn, 3)} m
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Tw</dt>
                    <dd className="font-mono font-semibold text-slate-800">
                      {formatNum(result.topWidth, 3)} m
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">A</dt>
                    <dd className="font-mono text-slate-800">{formatNum(result.area, 3)} m²</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">V</dt>
                    <dd className="font-mono text-slate-800">{formatNum(result.velocity, 3)} m/s</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Fr</dt>
                    <dd className="font-mono text-slate-800">{formatNum(result.froude, 3)}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">P</dt>
                    <dd className="font-mono text-slate-800">
                      {formatNum(result.wettedPerimeter, 3)} m
                    </dd>
                  </div>
                </dl>
              )}
            </div>
          </motion.form>

          {/* LIVE SKETCH */}
          <motion.div
            className="flex flex-col rounded-xl border border-slate-200 bg-white/90 p-5 shadow-sm backdrop-blur"
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.45, delay: 0.1 }}
          >
            <h2 className="mb-3 text-lg font-semibold text-slate-900">{t("normalDepth.sketchTitle")}</h2>
            <div className="overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
              <TrapezoidSketch
                b={live.b}
                z={live.z}
                yn={result.yn ?? 0.5}
                Q={live.Q}
                n={live.n}
                S0={live.S0}
                labels={{ sketchAria: t("normalDepth.sketchAria") }}
              />
            </div>

            <ul className="mt-4 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
              <li className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-[var(--nd-b)]" />
                <span>b — {t("normalDepth.bottomWidth")}</span>
              </li>
              <li className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-[var(--nd-z)]" />
                <span>z — {t("normalDepth.sideSlope")}</span>
              </li>
              <li className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-[var(--nd-flow)]" />
                <span>Q, n, S₀</span>
              </li>
              <li className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-[var(--nd-yn)]" />
                <span>yn — {t("normalDepth.resultLabel")}</span>
              </li>
            </ul>

            <p className="mt-4 text-xs leading-relaxed text-slate-500">
              {t("normalDepth.methodNote")}
            </p>
          </motion.div>
        </div>

        <p className="mt-8 text-center text-sm text-slate-500">
          <Link to="/" className="underline hover:text-slate-800">
            {lang === "fr" ? "Retour à l’accueil" : "Back to home"}
          </Link>
          <span className="mx-2">·</span>
          <span className="font-mono text-xs">/tools/normal-depth</span>
        </p>
      </div>
    </div>
  );
}
