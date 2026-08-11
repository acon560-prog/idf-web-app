import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { solveNormalDepth } from "../utils/normalDepth.js";

const DEFAULTS = {
  shape: "trapezoid",
  Q: "3.598",
  S0: "0.017",
  n: "0.030",
  b: "0.5",
  z: "2.0",
  D: "2.0",
};

/** b (rect/trap width): 0.1 … 3.0 m */
const B_OPTIONS = Array.from({ length: 30 }, (_, i) => ((i + 1) / 10).toFixed(1));
/** z: 0.5 … 4.0 (H:V) */
const Z_OPTIONS = Array.from({ length: 36 }, (_, i) => ((i + 5) / 10).toFixed(1));
/** D (pipe diameter): 0.2 … 2.0 m by 0.1 */
const D_OPTIONS = Array.from({ length: 19 }, (_, i) => ((i + 2) / 10).toFixed(1));
/** Manning n: 0.010 … 0.050 by 0.001 */
const N_OPTIONS = Array.from({ length: 41 }, (_, i) => ((10 + i) / 1000).toFixed(3));
/** Longitudinal slope S0: 0.001 … 0.100 by 0.001 */
const S0_OPTIONS = Array.from({ length: 100 }, (_, i) => ((i + 1) / 1000).toFixed(3));

const SHAPES = ["trapezoid", "rectangular", "circular"];

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

function FlowLabels({ Q, n, S0 }) {
  return (
    <>
      <text x={16} y={20} fill="#334155" style={{ fontSize: 11, fontFamily: "ui-monospace, monospace" }}>
        {`Q = ${formatNum(Q, 3)} m³/s`}
      </text>
      <text x={16} y={36} fill="#334155" style={{ fontSize: 11, fontFamily: "ui-monospace, monospace" }}>
        {`n = ${formatNum(n, 3)}   S₀ = ${formatNum(S0, 4)}`}
      </text>
    </>
  );
}

function SvgDefs() {
  return (
    <defs>
      <linearGradient id="ndWater" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#7EB6D9" stopOpacity="0.55" />
        <stop offset="100%" stopColor="#3D7EA6" stopOpacity="0.75" />
      </linearGradient>
      <pattern id="ndHatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(35)">
        <line x1="0" y1="0" x2="0" y2="8" stroke="#94A3B8" strokeWidth="1.2" />
      </pattern>
    </defs>
  );
}

function YnArrow({ x, yBed, yWater }) {
  return (
    <>
      <line x1={x} y1={yBed} x2={x} y2={yWater} stroke="#1E8449" strokeWidth="1.5" />
      <polygon points={`${x},${yWater} ${x - 4},${yWater + 8} ${x + 4},${yWater + 8}`} fill="#1E8449" />
      <polygon points={`${x},${yBed} ${x - 4},${yBed - 8} ${x + 4},${yBed - 8}`} fill="#1E8449" />
      <text x={x - 8} y={(yBed + yWater) / 2 + 4} textAnchor="end" fill="#1E8449" style={{ fontSize: 12, fontWeight: 700 }}>
        yn
      </text>
    </>
  );
}

function TrapezoidSketch({ b, z, yn, Q, n, S0, aria }) {
  const padY = 36;
  const W = 420;
  const H = 280;
  const channelTop = padY + 18;
  const channelBottom = H - padY - 28;
  const maxDepthPx = channelBottom - channelTop;

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
  const t = yVis / (yBed - yBank || 1);
  const waterL = bedL - zVis * t;
  const waterR = bedR + zVis * t;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label={aria}>
      <SvgDefs />
      <rect x="0" y="0" width={W} height={H} fill="#F1F5F9" />
      <path
        d={`M 0 ${yBank + 8} L ${topL} ${yBank} L ${bedL} ${yBed} L ${bedR} ${yBed} L ${topR} ${yBank} L ${W} ${yBank + 8} L ${W} ${H} L 0 ${H} Z`}
        fill="#E2E8F0"
        opacity="0.55"
      />
      <motion.path
        d={`M ${waterL} ${yWater} L ${bedL} ${yBed} L ${bedR} ${yBed} L ${waterR} ${yWater} Z`}
        fill="url(#ndWater)"
        initial={false}
        animate={{ d: `M ${waterL} ${yWater} L ${bedL} ${yBed} L ${bedR} ${yBed} L ${waterR} ${yWater} Z` }}
        transition={{ type: "spring", stiffness: 120, damping: 18 }}
      />
      <path d={`M ${topL} ${yBank} L ${bedL} ${yBed} L ${bedR} ${yBed} L ${topR} ${yBank}`} fill="none" stroke="#1E293B" strokeWidth="2.5" strokeLinejoin="round" />
      <line x1={waterL} y1={yWater} x2={waterR} y2={yWater} stroke="#1D4E89" strokeWidth="1.5" strokeDasharray="5 3" />
      <text x={cx} y={yWater - 10} textAnchor="middle" fill="#475569" style={{ fontSize: 11, fontWeight: 600 }}>
        Tw
      </text>
      <line x1={bedL} y1={yBed + 14} x2={bedR} y2={yBed + 14} stroke="#C0392B" strokeWidth="1.5" />
      <text x={cx} y={yBed + 28} textAnchor="middle" fill="#C0392B" style={{ fontSize: 12, fontWeight: 700 }}>
        b
      </text>
      <YnArrow x={bedL - 22} yBed={yBed} yWater={yWater} />
      <text x={(bedR + topR) / 2 + 8} y={(yBed + yBank) / 2} fill="#6C3483" style={{ fontSize: 12, fontWeight: 700 }}>
        z
      </text>
      <FlowLabels Q={Q} n={n} S0={S0} />
    </svg>
  );
}

function RectangularSketch({ b, yn, Q, n, S0, aria }) {
  const W = 420;
  const H = 280;
  const yBank = 54;
  const yBed = H - 64;
  const maxDepthPx = yBed - yBank;
  const bVis = Math.max(50, Math.min(200, 50 + b * 70));
  const yMaxGuess = Math.max(yn || 0.5, 0.4);
  const yVis = Math.max(8, Math.min(maxDepthPx * 0.9, ((yn || 0) / yMaxGuess) * maxDepthPx * 0.85 + 12));
  const cx = W / 2;
  const yWater = yBed - yVis;
  const L = cx - bVis / 2;
  const R = cx + bVis / 2;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label={aria}>
      <SvgDefs />
      <rect x="0" y="0" width={W} height={H} fill="#F1F5F9" />
      <path d={`M 0 ${yBank} L ${L} ${yBank} L ${L} ${yBed} L ${R} ${yBed} L ${R} ${yBank} L ${W} ${yBank} L ${W} ${H} L 0 ${H} Z`} fill="#E2E8F0" opacity="0.55" />
      <motion.rect
        x={L}
        width={bVis}
        fill="url(#ndWater)"
        initial={false}
        animate={{ y: yWater, height: yVis }}
        transition={{ type: "spring", stiffness: 120, damping: 18 }}
      />
      <path d={`M ${L} ${yBank} L ${L} ${yBed} L ${R} ${yBed} L ${R} ${yBank}`} fill="none" stroke="#1E293B" strokeWidth="2.5" strokeLinejoin="round" />
      <line x1={L} y1={yWater} x2={R} y2={yWater} stroke="#1D4E89" strokeWidth="1.5" strokeDasharray="5 3" />
      <text x={cx} y={yWater - 10} textAnchor="middle" fill="#475569" style={{ fontSize: 11, fontWeight: 600 }}>
        Tw = b
      </text>
      <line x1={L} y1={yBed + 14} x2={R} y2={yBed + 14} stroke="#C0392B" strokeWidth="1.5" />
      <text x={cx} y={yBed + 28} textAnchor="middle" fill="#C0392B" style={{ fontSize: 12, fontWeight: 700 }}>
        b
      </text>
      <YnArrow x={L - 22} yBed={yBed} yWater={yWater} />
      <FlowLabels Q={Q} n={n} S0={S0} />
    </svg>
  );
}

function CircularSketch({ D, yn, Q, n, S0, aria }) {
  const W = 420;
  const H = 280;
  const cx = W / 2;
  const cy = H / 2 + 10;
  const r = Math.max(40, Math.min(100, 40 + D * 45));
  const ySafe = Math.min(Math.max(yn || 0, 0), D * 0.999);
  const fill = D > 0 ? ySafe / D : 0;
  // Water surface y from bottom of circle
  const yFromBottom = fill * 2 * r;
  const waterY = cy + r - yFromBottom;
  // Chord half-width
  const dy = cy - waterY;
  const halfChord = Math.sqrt(Math.max(0, r * r - dy * dy));

  // Clip water to circle below waterline
  const clipId = "ndCircClip";

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label={aria}>
      <SvgDefs />
      <defs>
        <clipPath id={clipId}>
          <rect x={cx - r - 2} y={waterY} width={2 * r + 4} height={cy + r - waterY + 2} />
        </clipPath>
      </defs>
      <rect x="0" y="0" width={W} height={H} fill="#F1F5F9" />
      <motion.circle
        cx={cx}
        cy={cy}
        r={r}
        fill="url(#ndWater)"
        clipPath={`url(#${clipId})`}
        initial={false}
        animate={{ r }}
        transition={{ type: "spring", stiffness: 120, damping: 18 }}
      />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#1E293B" strokeWidth="2.5" />
      <line
        x1={cx - halfChord}
        y1={waterY}
        x2={cx + halfChord}
        y2={waterY}
        stroke="#1D4E89"
        strokeWidth="1.5"
        strokeDasharray="5 3"
      />
      <text x={cx} y={waterY - 10} textAnchor="middle" fill="#475569" style={{ fontSize: 11, fontWeight: 600 }}>
        Tw
      </text>
      {/* D dimension */}
      <line x1={cx - r} y1={cy + r + 18} x2={cx + r} y2={cy + r + 18} stroke="#C0392B" strokeWidth="1.5" />
      <text x={cx} y={cy + r + 32} textAnchor="middle" fill="#C0392B" style={{ fontSize: 12, fontWeight: 700 }}>
        D
      </text>
      <YnArrow x={cx - r - 24} yBed={cy + r} yWater={waterY} />
      <FlowLabels Q={Q} n={n} S0={S0} />
    </svg>
  );
}

const yellowFieldClass =
  "w-full rounded-md border border-amber-300 bg-[#FFF59D] px-3 py-2 font-mono text-sm text-slate-900 shadow-inner outline-none ring-amber-400/40 focus:ring-2";

function FieldLabel({ id, label, unit, accent }) {
  return (
    <span className="mb-1 flex items-baseline gap-2 text-sm font-semibold text-slate-800">
      <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: accent }} aria-hidden />
      <label htmlFor={id}>{label}</label>
      {unit ? <span className="font-normal text-slate-500">{unit}</span> : null}
    </span>
  );
}

function YellowInput({ id, label, unit, value, onChange, accent, step = "any", min, max }) {
  return (
    <div className="block">
      <FieldLabel id={id} label={label} unit={unit} accent={accent} />
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

function YellowSelect({ id, label, unit, value, onChange, accent, options }) {
  return (
    <div className="block">
      <FieldLabel id={id} label={label} unit={unit} accent={accent} />
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className={yellowFieldClass}>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </div>
  );
}

export default function NormalDepth() {
  const { t, i18n } = useTranslation();
  const [inputs, setInputs] = useState(DEFAULTS);
  const [submitted, setSubmitted] = useState(DEFAULTS);

  const parsed = useMemo(() => {
    const shape = submitted.shape || "trapezoid";
    const Q = parsePositive(submitted.Q);
    const S0 = parsePositive(submitted.S0);
    const n = parsePositive(submitted.n);
    const b = parsePositive(submitted.b, { allowZero: true });
    const z = parsePositive(submitted.z, { allowZero: true });
    const D = parsePositive(submitted.D);
    return { shape, Q, S0, n, b, z, D };
  }, [submitted]);

  const result = useMemo(() => {
    if (parsed.Q == null || parsed.S0 == null || parsed.n == null) {
      return { yn: null, converged: false, error: "invalid_input" };
    }
    if (parsed.shape === "circular") {
      if (parsed.D == null) return { yn: null, converged: false, error: "invalid_input" };
      return solveNormalDepth({
        shape: "circular",
        Q: parsed.Q,
        n: parsed.n,
        S0: parsed.S0,
        D: parsed.D,
      });
    }
    if (parsed.b == null) return { yn: null, converged: false, error: "invalid_input" };
    if (parsed.shape === "rectangular") {
      return solveNormalDepth({
        shape: "rectangular",
        Q: parsed.Q,
        n: parsed.n,
        S0: parsed.S0,
        b: parsed.b,
      });
    }
    if (parsed.z == null) return { yn: null, converged: false, error: "invalid_input" };
    return solveNormalDepth({
      shape: "trapezoid",
      Q: parsed.Q,
      n: parsed.n,
      S0: parsed.S0,
      b: parsed.b,
      z: parsed.z,
    });
  }, [parsed]);

  const live = useMemo(() => {
    const Q = parsePositive(inputs.Q) ?? parsed.Q ?? 0;
    const S0 = parsePositive(inputs.S0) ?? parsed.S0 ?? 0;
    const n = parsePositive(inputs.n) ?? parsed.n ?? 0;
    const b = parsePositive(inputs.b, { allowZero: true }) ?? parsed.b ?? 0.5;
    const z = parsePositive(inputs.z, { allowZero: true }) ?? parsed.z ?? 1;
    const D = parsePositive(inputs.D) ?? parsed.D ?? 1;
    return { shape: inputs.shape, Q, S0, n, b, z, D };
  }, [inputs, parsed]);

  const setField = (key) => (value) => setInputs((prev) => ({ ...prev, [key]: value }));

  const onShapeChange = (shape) => {
    setInputs((prev) => ({ ...prev, shape }));
  };

  const onCalculate = (e) => {
    e.preventDefault();
    setSubmitted({ ...inputs });
  };

  const lang = i18n.resolvedLanguage?.startsWith("fr") ? "fr" : "en";
  const shapeLabel = t(`normalDepth.shapes.${live.shape}`);

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
          <p className="text-sm font-medium tracking-wide text-slate-500">{t("normalDepth.eyebrow")}</p>
          <h1 className="mt-1 font-serif text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            {t("normalDepth.title")}
          </h1>
          <p className="mt-3 text-base text-slate-600">{t("normalDepth.subtitle")}</p>
          <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
            {t("normalDepth.disclaimer")}
          </p>
        </motion.header>

        <div className="grid gap-6 lg:grid-cols-2">
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
                step="0.001"
                min="0.001"
              />
              <YellowSelect
                id="nd-S0"
                label="S₀"
                unit={`m/m — ${t("normalDepth.slope")} (0.001)`}
                value={inputs.S0}
                onChange={setField("S0")}
                accent="var(--nd-flow)"
                options={S0_OPTIONS}
              />
              <YellowSelect
                id="nd-n"
                label="n"
                unit={`${t("normalDepth.manningN")} (0.001)`}
                value={inputs.n}
                onChange={setField("n")}
                accent="var(--nd-flow)"
                options={N_OPTIONS}
              />
            </fieldset>

            <div className="my-5 border-t border-slate-100 pt-4">
              <p className="mb-3 text-sm font-semibold text-slate-800">{t("normalDepth.section")}</p>
              <div className="mb-4 flex flex-wrap gap-2" role="radiogroup" aria-label={t("normalDepth.section")}>
                {SHAPES.map((shape) => {
                  const active = inputs.shape === shape;
                  return (
                    <button
                      key={shape}
                      type="button"
                      role="radio"
                      aria-checked={active}
                      onClick={() => onShapeChange(shape)}
                      className={`rounded-md border px-3 py-1.5 text-sm font-medium transition ${
                        active
                          ? "border-sky-700 bg-sky-800 text-white"
                          : "border-slate-300 bg-white text-slate-700 hover:border-sky-400"
                      }`}
                    >
                      {t(`normalDepth.shapes.${shape}`)}
                    </button>
                  );
                })}
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                {inputs.shape !== "circular" && (
                  <YellowSelect
                    id="nd-b"
                    label="b"
                    unit={`m — ${t("normalDepth.bottomWidth")} (0.1)`}
                    value={inputs.b}
                    onChange={setField("b")}
                    accent="var(--nd-b)"
                    options={B_OPTIONS}
                  />
                )}
                {inputs.shape === "trapezoid" && (
                  <YellowSelect
                    id="nd-z"
                    label="z"
                    unit={`H:V — ${t("normalDepth.sideSlope")} (0.1)`}
                    value={inputs.z}
                    onChange={setField("z")}
                    accent="var(--nd-z)"
                    options={Z_OPTIONS}
                  />
                )}
                {inputs.shape === "circular" && (
                  <YellowSelect
                    id="nd-D"
                    label="D"
                    unit={`m — ${t("normalDepth.diameter")} (0.1)`}
                    value={inputs.D}
                    onChange={setField("D")}
                    accent="var(--nd-b)"
                    options={D_OPTIONS}
                  />
                )}
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
                {t("normalDepth.results")} · {t(`normalDepth.shapes.${submitted.shape}`)}
              </p>
              {result.error === "invalid_input" ? (
                <p className="mt-2 text-sm text-rose-700">{t("normalDepth.invalid")}</p>
              ) : result.error === "exceeds_capacity" ? (
                <p className="mt-2 text-sm text-rose-700">
                  {t("normalDepth.exceedsCapacity")}
                  {result.QmaxApprox != null ? ` (≈ ${formatNum(result.QmaxApprox, 3)} m³/s)` : ""}
                </p>
              ) : (
                <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-slate-500">yn</dt>
                    <dd className="font-mono text-lg font-bold text-[var(--nd-yn)]">{formatNum(result.yn, 3)} m</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Tw</dt>
                    <dd className="font-mono font-semibold text-slate-800">{formatNum(result.topWidth, 3)} m</dd>
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
                    <dd className="font-mono text-slate-800">{formatNum(result.wettedPerimeter, 3)} m</dd>
                  </div>
                  {submitted.shape === "circular" && result.fillRatio != null && (
                    <div className="col-span-2">
                      <dt className="text-slate-500">yn / D</dt>
                      <dd className="font-mono text-slate-800">{formatNum(result.fillRatio * 100, 1)}%</dd>
                    </div>
                  )}
                </dl>
              )}
            </div>
          </motion.form>

          <motion.div
            className="flex flex-col rounded-xl border border-slate-200 bg-white/90 p-5 shadow-sm backdrop-blur"
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.45, delay: 0.1 }}
          >
            <h2 className="mb-3 text-lg font-semibold text-slate-900">
              {t("normalDepth.sketchTitle")} · {shapeLabel}
            </h2>
            <div className="overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
              {live.shape === "rectangular" ? (
                <RectangularSketch
                  b={live.b}
                  yn={result.yn ?? 0.5}
                  Q={live.Q}
                  n={live.n}
                  S0={live.S0}
                  aria={t("normalDepth.sketchAria")}
                />
              ) : live.shape === "circular" ? (
                <CircularSketch
                  D={live.D}
                  yn={result.yn ?? live.D * 0.4}
                  Q={live.Q}
                  n={live.n}
                  S0={live.S0}
                  aria={t("normalDepth.sketchAria")}
                />
              ) : (
                <TrapezoidSketch
                  b={live.b}
                  z={live.z}
                  yn={result.yn ?? 0.5}
                  Q={live.Q}
                  n={live.n}
                  S0={live.S0}
                  aria={t("normalDepth.sketchAria")}
                />
              )}
            </div>

            <ul className="mt-4 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
              {live.shape !== "circular" && (
                <li className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm bg-[var(--nd-b)]" />
                  <span>b — {t("normalDepth.bottomWidth")}</span>
                </li>
              )}
              {live.shape === "trapezoid" && (
                <li className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm bg-[var(--nd-z)]" />
                  <span>z — {t("normalDepth.sideSlope")}</span>
                </li>
              )}
              {live.shape === "circular" && (
                <li className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm bg-[var(--nd-b)]" />
                  <span>D — {t("normalDepth.diameter")}</span>
                </li>
              )}
              <li className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-[var(--nd-flow)]" />
                <span>Q, n, S₀</span>
              </li>
              <li className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm bg-[var(--nd-yn)]" />
                <span>yn — {t("normalDepth.resultLabel")}</span>
              </li>
            </ul>

            <p className="mt-4 text-xs leading-relaxed text-slate-500">{t("normalDepth.methodNote")}</p>
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
