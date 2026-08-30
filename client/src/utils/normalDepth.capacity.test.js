import { solveNormalDepth } from "./normalDepth.js";

describe("solveNormalDepth circular capacity", () => {
  it("flags exceeds_capacity without yn or fillRatio", () => {
    const r = solveNormalDepth({
      shape: "circular",
      Q: 0.389,
      n: 0.013,
      S0: 0.008,
      D: 0.3,
    });
    expect(r.error).toBe("exceeds_capacity");
    expect(r.yn).toBeNull();
    expect(r.fillRatio).toBeUndefined();
    expect(r.QmaxApprox).toBeGreaterThan(0);
    expect(r.QmaxApprox).toBeLessThan(0.389);
  });

  it("returns fillRatio only when converged", () => {
    const r = solveNormalDepth({
      shape: "circular",
      Q: 0.04,
      n: 0.013,
      S0: 0.008,
      D: 0.3,
    });
    expect(r.error).toBeUndefined();
    expect(r.converged).toBe(true);
    expect(r.yn).toBeGreaterThan(0);
    expect(r.fillRatio).toBeGreaterThan(0);
    expect(r.fillRatio).toBeLessThan(1);
  });
});

describe("solveNormalDepth bank height H", () => {
  it("trapezoid without H always finds yn", () => {
    const r = solveNormalDepth({
      shape: "trapezoid",
      Q: 10,
      n: 0.013,
      S0: 0.008,
      b: 0.5,
      z: 2,
    });
    expect(r.error).toBeUndefined();
    expect(r.converged).toBe(true);
    expect(r.yn).toBeGreaterThan(0.5);
    expect(r.fillRatioBank).toBeUndefined();
  });

  it("trapezoid with low H reports exceeds_capacity", () => {
    const r = solveNormalDepth({
      shape: "trapezoid",
      Q: 10,
      n: 0.013,
      S0: 0.008,
      b: 0.5,
      z: 2,
      H: 0.5,
    });
    expect(r.error).toBe("exceeds_capacity");
    expect(r.yn).toBeNull();
    expect(r.bankHeight).toBe(0.5);
    expect(r.QmaxApprox).toBeGreaterThan(0);
    expect(r.QmaxApprox).toBeLessThan(10);
  });

  it("trapezoid with tall H returns yn/H", () => {
    const r = solveNormalDepth({
      shape: "trapezoid",
      Q: 10,
      n: 0.013,
      S0: 0.008,
      b: 0.5,
      z: 2,
      H: 2,
    });
    expect(r.error).toBeUndefined();
    expect(r.converged).toBe(true);
    expect(r.yn).toBeLessThan(2);
    expect(r.fillRatioBank).toBeGreaterThan(0);
    expect(r.fillRatioBank).toBeLessThan(1);
  });

  it("rectangular with low H reports exceeds_capacity", () => {
    const r = solveNormalDepth({
      shape: "rectangular",
      Q: 10,
      n: 0.013,
      S0: 0.008,
      b: 1,
      H: 0.4,
    });
    expect(r.error).toBe("exceeds_capacity");
    expect(r.bankHeight).toBe(0.4);
  });
});
