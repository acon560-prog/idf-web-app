"""
Compound hydraulic model: circular culvert (ponceau) + trapezoidal rockfill fossé.

Behaviour
---------
Q_total(HW) = Q_pipe(HW) + Q_overflow(HW)

- Pipe: FHWA HDS-5 inlet control (Form 2, SI) + outlet control (Manning + losses).
- Overflow (above pipe crown): flow **through porous rockfill** 8–200 mm
  (Wilkins / turbulent porous approximation), optionally plus free-surface
  Manning if water rises above the rock surface.

Default site values (user update 2026-08-16):
  D=1.05 m, L=50.9 m, b=2 m, z=2
  elev_invert_us=35.36, elev_invert_ds=34.47 → S0≈0.0175
  elev_max=37.4, entrance=beveled, TW unknown → free outfall (0)
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Literal, Optional


G = 9.81  # m/s²
KU_SI = 1.811  # FHWA HDS-5 Form-2 SI conversion

EntranceType = Literal["square_edge", "beveled", "groove_headwall"]

# HDS-5 Form-2 coeffs (circular concrete) + Ke
ENTRANCE_PRESETS: dict[str, dict[str, float]] = {
    "square_edge": {"K": 0.0098, "M": 2.0, "c": 0.0398, "Y": 0.67, "Ke": 0.5},
    # 45° bevelled ring / beveled entrance
    "beveled": {"K": 0.0018, "M": 2.5, "c": 0.0300, "Y": 0.74, "Ke": 0.2},
    "groove_headwall": {"K": 0.0078, "M": 2.0, "c": 0.0292, "Y": 0.74, "Ke": 0.2},
}


@dataclass
class CulvertDitchParams:
    # Geometry (m)
    D: float = 1.05
    L: float = 50.9
    b: float = 2.0
    z: float = 2.0  # H:V

    # Elevations (m)
    elev_invert: float = 35.36  # upstream invert
    elev_invert_ds: float = 34.47  # downstream invert
    elev_max: float = 37.4
    # Top of rockfill surface (default = elev_max → rock fills to max stage)
    elev_rock_top: Optional[float] = None

    # Overflow starts at pipe crown unless overridden (m above US invert)
    y_overflow: Optional[float] = None

    # Hydraulics
    S0: Optional[float] = None  # if None → from inverts / L
    n_pipe: float = 0.013
    n_surface: float = 0.045  # free-surface flow above rock (if any)
    entrance: EntranceType = "beveled"
    TW: float = 0.0  # unknown → free-outfall assumption

    # Coarse 8–200 mm: preferential / macropore flow ≈ rough channel (default).
    # Use overflow_mode="porous" for Wilkins seepage-only (much smaller Q).
    overflow_mode: Literal["porous", "surface", "both"] = "surface"
    n_porosity: float = 0.40
    d50: float = 0.05  # m — characteristic size inside 8–200 mm band
    Cd_rock: float = 0.85  # empirical bulk-velocity coefficient (calibrate)

    # Filled from entrance preset unless overridden
    K: float = field(default=0.0018)
    M: float = field(default=2.5)
    c: float = field(default=0.0300)
    Y: float = field(default=0.74)
    Ke: float = field(default=0.2)

    def __post_init__(self) -> None:
        preset = ENTRANCE_PRESETS.get(self.entrance, ENTRANCE_PRESETS["beveled"])
        # Always apply preset for the chosen entrance (keeps coeffs consistent)
        self.K = preset["K"]
        self.M = preset["M"]
        self.c = preset["c"]
        self.Y = preset["Y"]
        self.Ke = preset["Ke"]
        if self.S0 is None:
            if self.L > 0:
                self.S0 = max(1e-6, (self.elev_invert - self.elev_invert_ds) / self.L)
            else:
                self.S0 = 0.017

    def overflow_depth(self) -> float:
        return self.D if self.y_overflow is None else self.y_overflow

    def rock_top_depth(self) -> float:
        top = self.elev_max if self.elev_rock_top is None else self.elev_rock_top
        return max(self.overflow_depth(), top - self.elev_invert)

    def max_depth(self) -> float:
        return max(0.01, self.elev_max - self.elev_invert)

    def area_full(self) -> float:
        return math.pi * (self.D / 2.0) ** 2


@dataclass
class RatingPoint:
    HW: float
    WSE: float
    Q_pipe: float
    Q_ditch: float
    Q_total: float
    control: str


def _trapezoid(b: float, z: float, y: float) -> tuple[float, float, float]:
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


def _porous_rockfill_Q(A_gross: float, p: CulvertDitchParams) -> float:
    """
    Turbulent porous flow through coarse rock (Wilkins-type bulk velocity).

    V_bulk ≈ Cd * n_porosity * sqrt( g * d50 * S0 / (1 - n_porosity) )
    Q = A_gross * V_bulk

    Valid order-of-magnitude for 8–200 mm rock drains; calibrate Cd_rock / d50 on site.
    """
    if A_gross <= 0 or p.S0 <= 0 or p.d50 <= 0:
        return 0.0
    n = min(0.55, max(0.20, p.n_porosity))
    V_bulk = p.Cd_rock * n * math.sqrt(G * p.d50 * p.S0 / (1.0 - n))
    return A_gross * V_bulk


def pipe_inlet_control_HW(Q: float, p: CulvertDitchParams) -> float:
    if Q <= 0:
        return 0.0
    A = p.area_full()
    arg = Q / (KU_SI * A * math.sqrt(p.D))
    hw_un = p.K * (arg ** p.M) * p.D
    hw_sub = (p.c * (arg ** 2) + p.Y) * p.D
    if hw_un < 0.95 * p.D:
        return hw_un
    if hw_sub > 1.2 * p.D:
        return hw_sub
    t = (hw_un / p.D - 0.95) / (1.2 - 0.95)
    t = min(1.0, max(0.0, t))
    return (1 - t) * hw_un + t * hw_sub


def pipe_inlet_control_Q(HW: float, p: CulvertDitchParams) -> float:
    if HW <= 0:
        return 0.0
    Q_hi = 50.0
    for _ in range(60):
        if pipe_inlet_control_HW(0.5 * Q_hi, p) < HW:
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
    if HW <= 1e-6 or p.S0 <= 0:
        return 0.0

    if HW < p.D:
        y = HW
        ratio = max(1e-6, min(0.999, y / p.D))
        theta = 2.0 * math.acos(1.0 - 2.0 * ratio)
        r = p.D / 2.0
        A = (r * r / 2.0) * (theta - math.sin(theta))
        P = r * theta
        Rh = A / P if P > 0 else 0.0
        return _manning_Q(p.n_pipe, A, Rh, p.S0)

    A = p.area_full()
    Rh = p.D / 4.0
    H_loss = HW - p.TW + p.S0 * p.L
    if H_loss <= 0:
        return 0.0
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


def overflow_Q(HW: float, p: CulvertDitchParams) -> float:
    """
    Flow above pipe crown up to elev_max:

    - porous: turbulent seepage through rockfill prism (crown → HW)
    - surface: rough open-channel Manning in the trapezoid above the crown
              (represents preferential / overtopping flow in the rock ditch)
    - both: porous through rock up to elev_rock_top, plus surface above rock top
    """
    y0 = p.overflow_depth()
    if HW <= y0:
        return 0.0

    y_wse = min(HW, p.max_depth())
    y_rock_top = p.rock_top_depth()
    Q = 0.0

    if p.overflow_mode == "porous":
        y_fill = y_wse - y0
        A_fill, _, _ = _trapezoid(p.b, p.z, y_fill)
        Q += _porous_rockfill_Q(A_fill, p)

    elif p.overflow_mode == "surface":
        # Rough channel from crown upward (rock-lined fossé)
        y_ch = y_wse - y0
        A, _, Rh = _trapezoid(p.b, p.z, y_ch)
        Q += _manning_Q(p.n_surface, A, Rh, p.S0)

    elif p.overflow_mode == "both":
        y_fill = min(y_wse, y_rock_top) - y0
        if y_fill > 0:
            A_fill, _, _ = _trapezoid(p.b, p.z, y_fill)
            Q += _porous_rockfill_Q(A_fill, p)
        if y_wse > y_rock_top:
            y_surf = y_wse - y_rock_top
            b_surf = p.b + 2.0 * p.z * max(0.0, y_rock_top - y0)
            A, _, Rh = _trapezoid(b_surf, p.z, y_surf)
            Q += _manning_Q(p.n_surface, A, Rh, p.S0)

    return Q


def rating_at_HW(HW: float, p: CulvertDitchParams) -> RatingPoint:
    qp, ctrl = pipe_Q(HW, p)
    qd = overflow_Q(HW, p)
    qt = qp + qd
    if qd > 0 and qp > 0:
        control = f"compound/{ctrl}+{p.overflow_mode}"
    elif qd > 0:
        control = f"overflow/{p.overflow_mode}"
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


def build_rating_curve(p: CulvertDitchParams, n: int = 81) -> list[RatingPoint]:
    h_max = p.max_depth()
    return [rating_at_HW(h_max * i / (n - 1), p) for i in range(n)]


def solve_HW_for_Q(Q: float, p: CulvertDitchParams, tol: float = 1e-4) -> RatingPoint:
    if Q <= 0:
        return rating_at_HW(0.0, p)
    lo, hi = 0.0, p.max_depth()
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
    return {
        "inputs": asdict(p),
        "design_Q_m3s": Q,
        "result": asdict(r),
        "pipe_capacity_at_crown_m3s": crown.Q_pipe,
        "S0_used": p.S0,
        "overflow_active": r.Q_ditch > 1e-6,
        "exceeds_max_stage": r.Q_total < Q - 1e-3,
    }
