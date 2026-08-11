/**
 * Manning normal-depth helpers for open-channel preliminary sizing (SI).
 * Shapes: trapezoid (b, z), rectangular (b), circular (D) — partially full.
 */

export function trapezoidGeometry(b, z, y) {
  const area = (b + z * y) * y;
  const wettedPerimeter = b + 2 * y * Math.sqrt(1 + z * z);
  const topWidth = b + 2 * z * y;
  const hydraulicRadius = wettedPerimeter > 0 ? area / wettedPerimeter : 0;
  return { area, wettedPerimeter, topWidth, hydraulicRadius };
}

export function rectangularGeometry(b, y) {
  const area = b * y;
  const wettedPerimeter = b + 2 * y;
  const topWidth = b;
  const hydraulicRadius = wettedPerimeter > 0 ? area / wettedPerimeter : 0;
  return { area, wettedPerimeter, topWidth, hydraulicRadius };
}

/**
 * Partially full circular section.
 * y = flow depth, D = diameter. Requires 0 < y < D for open-channel free surface.
 */
export function circularGeometry(D, y) {
  if (!(D > 0) || !(y > 0) || y >= D) {
    return { area: 0, wettedPerimeter: 0, topWidth: 0, hydraulicRadius: 0, theta: 0 };
  }
  const r = D / 2;
  const theta = 2 * Math.acos(1 - (2 * y) / D); // central angle (rad)
  const area = (r * r / 2) * (theta - Math.sin(theta));
  const wettedPerimeter = r * theta;
  const topWidth = D * Math.sin(theta / 2);
  const hydraulicRadius = wettedPerimeter > 0 ? area / wettedPerimeter : 0;
  return { area, wettedPerimeter, topWidth, hydraulicRadius, theta };
}

export function sectionGeometry(shape, dims, y) {
  if (shape === "rectangular") return rectangularGeometry(dims.b, y);
  if (shape === "circular") return circularGeometry(dims.D, y);
  return trapezoidGeometry(dims.b, dims.z, y);
}

/** Discharge by Manning (SI): Q = (1/n) A R^(2/3) S^(1/2) */
export function manningDischarge(n, S0, shape, dims, y) {
  if (n <= 0 || S0 <= 0 || y <= 0) return 0;
  const { area, hydraulicRadius } = sectionGeometry(shape, dims, y);
  if (area <= 0 || hydraulicRadius <= 0) return 0;
  return (1 / n) * area * Math.pow(hydraulicRadius, 2 / 3) * Math.sqrt(S0);
}

function packResult(Q, geo, yn, converged, iterations, qMid, extra = {}) {
  const V = geo.area > 0 ? Q / geo.area : 0;
  const Fr = geo.topWidth > 0 ? V / Math.sqrt((9.81 * geo.area) / geo.topWidth) : 0;
  return {
    yn,
    converged,
    iterations,
    ...geo,
    velocity: V,
    froude: Fr,
    Qcheck: qMid,
    ...extra,
  };
}

/**
 * Solve normal depth yn for given Q (bisection).
 * @param {{ shape: 'trapezoid'|'rectangular'|'circular', Q, n, S0, b?, z?, D? }} params
 */
export function solveNormalDepth(params, opts = {}) {
  const maxIter = opts.maxIter ?? 80;
  const tolQ = opts.tolQ ?? 1e-6;
  const tolY = opts.tolY ?? 1e-6;
  const shape = params.shape || "trapezoid";
  const { Q, n, S0 } = params;

  if (!(Q > 0 && n > 0 && S0 > 0)) {
    return { yn: null, converged: false, iterations: 0, error: "invalid_input" };
  }

  let dims;
  let yMax;

  if (shape === "circular") {
    const D = params.D;
    if (!(D > 0)) {
      return { yn: null, converged: false, iterations: 0, error: "invalid_input" };
    }
    dims = { D };
    // Cap just below full (free surface); capacity peaks near ~0.94 D for circular
    yMax = D * (1 - 1e-6);
    const qMax = manningDischarge(n, S0, shape, dims, 0.94 * D);
    if (Q > qMax * 1.001) {
      return {
        yn: null,
        converged: false,
        iterations: 0,
        error: "exceeds_capacity",
        QmaxApprox: qMax,
      };
    }
  } else if (shape === "rectangular") {
    const b = params.b;
    if (!(b >= 0)) {
      return { yn: null, converged: false, iterations: 0, error: "invalid_input" };
    }
    dims = { b };
    yMax = null;
  } else {
    const b = params.b;
    const z = params.z;
    if (!(b >= 0 && z >= 0)) {
      return { yn: null, converged: false, iterations: 0, error: "invalid_input" };
    }
    dims = { b, z };
    yMax = null;
  }

  let yLo = 1e-6;
  let yHi = Math.max(0.05, Math.pow((Q * n) / Math.sqrt(S0), 0.6));
  if (yMax != null) yHi = Math.min(yHi, yMax * 0.5);

  let qHi = manningDischarge(n, S0, shape, dims, yHi);
  let expand = 0;
  while (qHi < Q && expand < 50) {
    if (yMax != null) {
      yHi = Math.min(yMax, yHi * 1.5 + 0.01);
      if (yHi >= yMax * 0.999 && qHi < Q) {
        return {
          yn: null,
          converged: false,
          iterations: 0,
          error: "exceeds_capacity",
          QmaxApprox: manningDischarge(n, S0, shape, dims, 0.94 * dims.D),
        };
      }
    } else {
      yHi *= 1.8;
    }
    qHi = manningDischarge(n, S0, shape, dims, yHi);
    expand += 1;
  }
  if (qHi < Q) {
    return { yn: null, converged: false, iterations: 0, error: "no_bracket" };
  }

  let yn = yHi;
  let iterations = 0;
  for (let i = 0; i < maxIter; i += 1) {
    iterations = i + 1;
    const yMid = 0.5 * (yLo + yHi);
    const qMid = manningDischarge(n, S0, shape, dims, yMid);
    yn = yMid;
    if (Math.abs(qMid - Q) < tolQ || yHi - yLo < tolY) {
      const geo = sectionGeometry(shape, dims, yn);
      const extra =
        shape === "circular" && dims.D
          ? { fillRatio: yn / dims.D, thetaDeg: ((geo.theta || 0) * 180) / Math.PI }
          : {};
      return packResult(Q, geo, yn, true, iterations, qMid, extra);
    }
    if (qMid < Q) yLo = yMid;
    else yHi = yMid;
  }

  const geo = sectionGeometry(shape, dims, yn);
  const extra =
    shape === "circular" && dims.D
      ? { fillRatio: yn / dims.D, thetaDeg: ((geo.theta || 0) * 180) / Math.PI }
      : {};
  return packResult(
    Q,
    geo,
    yn,
    false,
    iterations,
    manningDischarge(n, S0, shape, dims, yn),
    { error: "max_iter", ...extra }
  );
}
