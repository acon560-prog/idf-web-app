/**
 * Drainage Quick Size helpers (SI) — Rational Q, full-flow pipe, ditch table.
 * Preliminary sizing only; no IDF coupling in v1.
 */

/** Typical runoff coefficients for land-cover mix */
export const LAND_COVER_C = {
  roof: 0.9,
  pave: 0.9,
  grass: 0.2,
};

/** Manning n presets (circular pipes) */
export const PIPE_MATERIAL_PRESETS = [
  { id: "pvc", n: 0.011, labelKey: "pvc" },
  { id: "concrete", n: 0.013, labelKey: "concrete" },
  { id: "hdpe", n: 0.012, labelKey: "hdpe" },
  { id: "cmp", n: 0.024, labelKey: "cmp" },
  { id: "custom", n: null, labelKey: "custom" },
];

/** Commercial pipe diameters (m) */
export const COMMERCIAL_DIAMETERS_M = [
  0.2, 0.25, 0.3, 0.375, 0.45, 0.525, 0.6, 0.75, 0.9, 1.05, 1.2, 1.5, 1.8, 2.0,
];

/**
 * Rational method peak discharge.
 * Q (m³/s) = C · i · A_ha / 360
 * @param {{ C: number, i_mm_h: number, A: number, areaUnit: 'ha'|'m2' }}
 */
export function rationalDischarge({ C, i_mm_h, A, areaUnit = "ha" }) {
  if (!(C > 0 && C <= 1.5 && i_mm_h > 0 && A > 0)) {
    return { Q: null, error: "invalid_input" };
  }
  const A_ha = areaUnit === "m2" ? A / 10000 : A;
  const Q = (C * i_mm_h * A_ha) / 360;
  return { Q, A_ha, error: null };
}

/**
 * Composite C from land-cover percentages (must sum ≈ 100).
 */
export function compositeCFromCover({ roofPct = 0, pavePct = 0, grassPct = 0 }) {
  const sum = roofPct + pavePct + grassPct;
  if (!(sum > 0)) return { C: null, error: "invalid_cover" };
  const C =
    (LAND_COVER_C.roof * roofPct + LAND_COVER_C.pave * pavePct + LAND_COVER_C.grass * grassPct) /
    sum;
  return { C, sum, error: null };
}

/** Full-flow circular Manning capacity (m³/s). */
export function pipeFullFlowCapacity({ D, n, S }) {
  if (!(D > 0 && n > 0 && S > 0)) return 0;
  const A = (Math.PI * D * D) / 4;
  const R = D / 4;
  return (1 / n) * A * Math.pow(R, 2 / 3) * Math.sqrt(S);
}

/**
 * Suggest smallest commercial diameter with Qp >= Q.
 * @returns {{ D, Qp, V, ok, candidates }}
 */
export function suggestPipeDiameter({ Q, n, S, diameters = COMMERCIAL_DIAMETERS_M }) {
  if (!(Q > 0 && n > 0 && S > 0)) {
    return { D: null, Qp: null, V: null, ok: false, error: "invalid_input", candidates: [] };
  }
  const candidates = diameters.map((D) => {
    const Qp = pipeFullFlowCapacity({ D, n, S });
    const A = (Math.PI * D * D) / 4;
    const V = A > 0 ? Q / A : 0;
    return { D, Qp, V, ok: Qp >= Q };
  });
  const pick = candidates.find((c) => c.ok) || null;
  if (!pick) {
    const last = candidates[candidates.length - 1];
    return {
      D: last?.D ?? null,
      Qp: last?.Qp ?? null,
      V: last?.V ?? null,
      ok: false,
      error: "no_diameter",
      candidates,
    };
  }
  return { ...pick, error: null, candidates };
}

/** Trapezoid / V-ditch geometry at depth y (b may be 0). */
export function ditchGeometry(b, z, y) {
  const area = (b + z * y) * y;
  const wettedPerimeter = b + 2 * y * Math.sqrt(1 + z * z);
  const topWidth = b + 2 * z * y;
  const sideRun = z * y; // horizontal projection of one bank ("x")
  const hydraulicRadius = wettedPerimeter > 0 ? area / wettedPerimeter : 0;
  return { area, wettedPerimeter, topWidth, sideRun, hydraulicRadius };
}

export function ditchCapacityAtDepth({ b, z, y, n, S }) {
  if (!(y > 0 && n > 0 && S > 0 && b >= 0 && z >= 0)) return 0;
  const { area, hydraulicRadius } = ditchGeometry(b, z, y);
  if (area <= 0 || hydraulicRadius <= 0) return 0;
  return (1 / n) * area * Math.pow(hydraulicRadius, 2 / 3) * Math.sqrt(S);
}

/**
 * Table for target depths: x (side run), Tw, V, Qcap, OK vs design Q.
 */
export function ditchDepthTable({ Q, S, n, b, z, depths }) {
  if (!(Q > 0 && S > 0 && n > 0 && b >= 0 && z >= 0) || !Array.isArray(depths)) {
    return { rows: [], error: "invalid_input" };
  }
  const rows = depths
    .map((y) => Number(y))
    .filter((y) => Number.isFinite(y) && y > 0)
    .map((y) => {
      const geo = ditchGeometry(b, z, y);
      const Qcap = ditchCapacityAtDepth({ b, z, y, n, S });
      const V = geo.area > 0 ? Q / geo.area : 0;
      return {
        y,
        x: geo.sideRun,
        Tw: geo.topWidth,
        A: geo.area,
        V,
        Qcap,
        ok: Qcap >= Q,
      };
    });
  return { rows, error: null };
}

/** Parse percent slope (e.g. 1.5) or decimal (0.015) into m/m. */
export function parseSlope(value, unit = "decimal") {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return null;
  return unit === "percent" ? n / 100 : n;
}
