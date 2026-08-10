/**
 * Manning normal-depth helpers for open-channel preliminary sizing.
 * Trapezoid: bottom width b, side slope z (H:V), depth y.
 */

export function trapezoidGeometry(b, z, y) {
  const area = (b + z * y) * y;
  const wettedPerimeter = b + 2 * y * Math.sqrt(1 + z * z);
  const topWidth = b + 2 * z * y;
  const hydraulicRadius = wettedPerimeter > 0 ? area / wettedPerimeter : 0;
  return { area, wettedPerimeter, topWidth, hydraulicRadius };
}

/** Discharge by Manning (SI): Q = (1/n) A R^(2/3) S^(1/2) */
export function manningDischarge(n, S0, b, z, y) {
  if (n <= 0 || S0 <= 0 || b < 0 || z < 0 || y <= 0) return 0;
  const { area, hydraulicRadius } = trapezoidGeometry(b, z, y);
  if (area <= 0 || hydraulicRadius <= 0) return 0;
  return (1 / n) * area * Math.pow(hydraulicRadius, 2 / 3) * Math.sqrt(S0);
}

/**
 * Solve normal depth yn for given Q (bisection).
 * Returns { yn, converged, iterations } or null fields on bad input.
 */
export function solveNormalDepth({ Q, n, S0, b, z }, opts = {}) {
  const maxIter = opts.maxIter ?? 80;
  const tolQ = opts.tolQ ?? 1e-6;
  const tolY = opts.tolY ?? 1e-6;

  if (!(Q > 0 && n > 0 && S0 > 0 && b >= 0 && z >= 0)) {
    return { yn: null, converged: false, iterations: 0, error: "invalid_input" };
  }

  let yLo = 1e-6;
  let yHi = Math.max(0.05, Math.pow(Q * n / Math.sqrt(S0), 0.6)); // rough seed
  // Expand upper bound until Q(yHi) >= Q
  let qHi = manningDischarge(n, S0, b, z, yHi);
  let expand = 0;
  while (qHi < Q && expand < 40) {
    yHi *= 1.8;
    qHi = manningDischarge(n, S0, b, z, yHi);
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
    const qMid = manningDischarge(n, S0, b, z, yMid);
    yn = yMid;
    if (Math.abs(qMid - Q) < tolQ || yHi - yLo < tolY) {
      const geo = trapezoidGeometry(b, z, yn);
      const V = geo.area > 0 ? Q / geo.area : 0;
      const Fr = geo.topWidth > 0 ? V / Math.sqrt((9.81 * geo.area) / geo.topWidth) : 0;
      return {
        yn,
        converged: true,
        iterations,
        ...geo,
        velocity: V,
        froude: Fr,
        Qcheck: qMid,
      };
    }
    if (qMid < Q) yLo = yMid;
    else yHi = yMid;
  }

  const geo = trapezoidGeometry(b, z, yn);
  const V = geo.area > 0 ? Q / geo.area : 0;
  const Fr = geo.topWidth > 0 ? V / Math.sqrt((9.81 * geo.area) / geo.topWidth) : 0;
  return {
    yn,
    converged: false,
    iterations,
    error: "max_iter",
    ...geo,
    velocity: V,
    froude: Fr,
    Qcheck: manningDischarge(n, S0, b, z, yn),
  };
}
