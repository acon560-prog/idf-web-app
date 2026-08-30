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
