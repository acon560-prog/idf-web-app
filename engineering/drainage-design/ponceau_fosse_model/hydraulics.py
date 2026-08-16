"""
Compound hydraulic model: circular culvert (ponceau) + trapezoidal ditch (fossé).

Behaviour
---------
For a given upstream water-surface elevation (or target discharge Q):
  Q_total = Q_pipe(HW) + Q_ditch(HW)

- Pipe: FHWA HDS-5 inlet control (Form 2, SI) and outlet control (Manning + losses);
  governing capacity = min(Qinlet, Qoutlet) at the same headwater.
- Ditch: starts when HW exceeds the overflow threshold (default = pipe crown);
  trapezoidal Manning conveyance in the fossé (rockfill → high n).

This is a preliminary 1D engineering tool — not a substitute for HEC-RAS.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Optional


G = 9.81  # m/s²
KU_SI = 1.811  # FHWA HDS-5 Form-2 SI conversion


@dataclass
class CulvertDitchParams:
    # Geometry (m)
    D: float = 1.05
    L: float = 50.9
    b: float = 2.0
    z: float = 2.0  # H:V horizontal run per 1 vertical

    # Elevations (m)
    elev_invert: float = 35.13
    elev_max: float = 37.4

    # When ditch conveyance starts (m above invert). Default = crown = D.
    y_overflow: Optional[float] = None

    # Hydraulics
    S0: float = 0.01  # longitudinal slope (m/m) — PLEASE CONFIRM ON SITE
    n_pipe: float = 0.013  # concrete / smooth
    n_ditch: float = 0.045  # coarse rockfill 8–200 mm (adjust 0.035–0.080)
    Ke: float = 0.5  # entrance loss (square edge w/ headwall ≈ 0.5)
    TW: float = 0.0  # tailwater depth above outlet invert (0 = free outfall approx.)

    # FHWA HDS-5 Form-2 coeffs — circular concrete, square edge w/ headwall
    K: float = 0.0098
    M: float = 2.0
    c: float = 0.0398
    Y: float = 0.67

    def overflow_depth(self) -> float:
        return self.D if self.y_overflow is None else self.y_overflow

    def max_depth(self) -> float:
        return max(0.01, self.elev_max - self.elev_invert)

    def area_full(self) -> float:
        return math.pi * (self.D / 2.0) ** 2


@dataclass
class RatingPoint:
    HW: float  # headwater depth above invert (m)
    WSE: float  # water-surface elev (m)
    Q_pipe: float
    Q_ditch: float
    Q_total: float
    control: str  # "inlet" | "outlet" | "ditch_only" | "compound"


def _trapezoid(b: float, z: float, y: float) -> tuple[float, float, float]:
    """Return A, P, Rh for trapezoid depth y."""
    if y <= 0:
        return 0.0, 0.0, 0.0
    A = (b + z * y) * y
    P = b + 2.0 * y * math.sqrt(1.0 + z * z)
    Rh = A / P if P > 0 else 0.0
    return A, P, Rh


def _manning_Q(n: float, A: float, Rh: float, S0: float) -> float:
    if n <= 0 or A <= 0 or Rh <= 0 or S0 <= 0:
        return 0.0
    return (1.0 / n) * A * (Rh ** (2.0 / 3.0)) * math.sqrt(S0)


def pipe_inlet_control_HW(Q: float, p: CulvertDitchParams) -> float:
    """
    FHWA HDS-5 Form-2 (SI): solve is not needed — return HW for given Q.
    Unsubmerged: HW/D = K [Q/(Ku A sqrt(D))]^M
    Submerged:   HW/D = c [Q/(Ku A sqrt(D))]^2 + Y
    Transition blended near HW/D ≈ 1.0–1.2
    """
    if Q <= 0:
        return 0.0
    A = p.area_full()
    arg = Q / (KU_SI * A * math.sqrt(p.D))
    hw_un = p.K * (arg ** p.M) * p.D
    hw_sub = (p.c * (arg ** 2) + p.Y) * p.D
    # Smooth handoff around HW/D = 1.0
    if hw_un < 0.95 * p.D:
        return hw_un
    if hw_sub > 1.2 * p.D:
        return hw_sub
    # Blend
    t = (hw_un / p.D - 0.95) / (1.2 - 0.95)
    t = min(1.0, max(0.0, t))
    return (1 - t) * hw_un + t * hw_sub


def pipe_inlet_control_Q(HW: float, p: CulvertDitchParams) -> float:
    """Invert inlet-control rating by bisection on Q."""
    if HW <= 0:
        return 0.0
    # Upper bound: orifice-like
    Q_hi = 50.0
    for _ in range(60):
        mid = 0.5 * Q_hi
        if pipe_inlet_control_HW(mid, p) < HW:
            # need larger Q upper bound
            Q_hi *= 2.0
            if Q_hi > 500:
                break
        else:
            break
    lo, hi = 0.0, Q_hi
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if pipe_inlet_control_HW(mid, p) < HW:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def pipe_outlet_control_Q(HW: float, p: CulvertDitchParams) -> float:
    """
    Full-barrel outlet control (conservative pressurized assumption when HW > D).
    Energy: HW + S0*L = TW + (1+Ke) V^2/(2g) + (n^2 V^2 L)/Rh^(4/3)
    with Rh = D/4 for full circle.
    For HW < D, use partially full Manning (approximate free-surface barrel).
    """
    if HW <= 1e-6 or p.S0 <= 0:
        return 0.0

    if HW < p.D:
        # Partially full circular — use geometric theta
        # y/D = HW/D; theta = 2 acos(1 - 2y/D)
        y = HW
        ratio = max(1e-6, min(0.999, y / p.D))
        theta = 2.0 * math.acos(1.0 - 2.0 * ratio)
        r = p.D / 2.0
        A = (r * r / 2.0) * (theta - math.sin(theta))
        P = r * theta
        Rh = A / P if P > 0 else 0.0
        return _manning_Q(p.n_pipe, A, Rh, p.S0)

    # Full barrel pressurized outlet control — solve for V
    A = p.area_full()
    Rh = p.D / 4.0
    # Available head for losses along barrel (approx.)
    # HW = TW + H_loss - S0*L  =>  H_loss = HW - TW + S0*L
    H_loss = HW - p.TW + p.S0 * p.L
    if H_loss <= 0:
        return 0.0
    # H_loss = (1+Ke) V^2/(2g) + n^2 V^2 L / Rh^(4/3)
    friction_coef = (p.n_pipe**2) * p.L / (Rh ** (4.0 / 3.0))
    entrance_coef = (1.0 + p.Ke) / (2.0 * G)
    denom = entrance_coef + friction_coef
    if denom <= 0:
        return 0.0
    V2 = H_loss / denom
    if V2 <= 0:
        return 0.0
    return A * math.sqrt(V2)


def pipe_Q(HW: float, p: CulvertDitchParams) -> tuple[float, str]:
    Qi = pipe_inlet_control_Q(HW, p)
    Qo = pipe_outlet_control_Q(HW, p)
    if Qi <= Qo:
        return Qi, "inlet"
    return Qo, "outlet"


def ditch_Q(HW: float, p: CulvertDitchParams) -> float:
    """Trapezoidal overflow above y_overflow (parallel to pipe)."""
    y0 = p.overflow_depth()
    y = HW - y0
    if y <= 0:
        return 0.0
    y_max = p.max_depth() - y0
    y = min(y, max(0.0, y_max))
    A, _, Rh = _trapezoid(p.b, p.z, y)
    return _manning_Q(p.n_ditch, A, Rh, p.S0)


def rating_at_HW(HW: float, p: CulvertDitchParams) -> RatingPoint:
    qp, ctrl = pipe_Q(HW, p)
    qd = ditch_Q(HW, p)
    qt = qp + qd
    if qd > 0 and qp > 0:
        control = f"compound/{ctrl}"
    elif qd > 0:
        control = "ditch_only"
    else:
        control = ctrl
    return RatingPoint(
        HW=HW,
        WSE=p.elev_invert + HW,
        Q_pipe=qp,
        Q_ditch=qd,
        Q_total=qt,
        control=control,
    )


def build_rating_curve(
    p: CulvertDitchParams, n: int = 81
) -> list[RatingPoint]:
    h_max = p.max_depth()
    pts = []
    for i in range(n):
        HW = h_max * i / (n - 1)
        pts.append(rating_at_HW(HW, p))
    return pts


def solve_HW_for_Q(Q: float, p: CulvertDitchParams, tol: float = 1e-4) -> RatingPoint:
    """Find HW such that Q_pipe + Q_ditch ≈ Q (bisection)."""
    if Q <= 0:
        return rating_at_HW(0.0, p)
    lo, hi = 0.0, p.max_depth()
    # If even at max depth capacity is too small, return max
    top = rating_at_HW(hi, p)
    if top.Q_total < Q:
        return top
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        r = rating_at_HW(mid, p)
        if r.Q_total < Q:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return rating_at_HW(0.5 * (lo + hi), p)


def summarize(Q: float, p: CulvertDitchParams) -> dict:
    r = solve_HW_for_Q(Q, p)
    crown = rating_at_HW(p.D, p)
    overflow_start = rating_at_HW(p.overflow_depth(), p)
    return {
        "inputs": asdict(p),
        "design_Q_m3s": Q,
        "result": asdict(r),
        "pipe_capacity_at_crown_m3s": crown.Q_pipe,
        "Q_at_overflow_threshold_m3s": overflow_start.Q_total,
        "overflow_active": r.Q_ditch > 1e-6,
        "exceeds_max_stage": r.Q_total < Q - 1e-3,
    }
