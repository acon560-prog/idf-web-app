#!/usr/bin/env python3
"""Shared data + level-pool routing for retention Files 2–5."""

from __future__ import annotations

import math
from dataclasses import dataclass

HYDRO_RAW = [
    (0.0, 0.778),
    (5.0, 1.170),
    (10.0, 1.857),
    (15.0, 3.202),
    (20.0, 6.309),
    (22.5, 9.600),
    (27.5, 5.846),
    (32.5, 3.857),
    (37.5, 2.689),
    (42.5, 1.953),
    (47.5, 1.462),
    (52.5, 1.121),
    (57.5, 0.875),
]
QPEAK_REF = 9.60
HYDRO_SHAPE = [(t, q / QPEAK_REF) for t, q in HYDRO_RAW]

N_MANNING = 0.013
D_1200 = 1.20
L_1200 = 31.30
Z_US = 33.60
Z_DS = 33.10
S0 = (Z_US - Z_DS) / L_1200
Z_POND = 34.88
CREST = 37.28
OV_B, OV_N, OV_Z, OV_S, OV_L = 2.0, 0.035, 2.0, 0.0085, 50.1
KE = 0.5
G = 9.81
KU = 1.811
K_IN, M_IN, C_IN, Y_IN = 0.0098, 2.0, 0.0398, 0.67

STAGES = [
    (34.88, 0.0),
    (35.50, 120.0),
    (36.01, 419.0),
    (36.50, 480.0),
    (37.00, 720.0),
    (37.28, 2198.0),
    (37.40, 1516.0),
    (40.00, 3746.0),
]


def stage_storage_curve(stages: list[tuple[float, float]] | None = None) -> list[tuple[float, float]]:
    st = stages or STAGES
    out: list[tuple[float, float]] = []
    v = 0.0
    out.append((st[0][0], 0.0))
    for i in range(1, len(st)):
        w0, a0 = st[i - 1]
        w1, a1 = st[i]
        v += 0.5 * (a0 + a1) * (w1 - w0)
        out.append((w1, v))
    return out


def interp(x: float, xs: list[float], ys: list[float]) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            if xs[i + 1] == xs[i]:
                return ys[i]
            t = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + t * (ys[i + 1] - ys[i])
    return ys[-1]


def q_inlet(hw: float, D: float = D_1200) -> float:
    if hw <= 0:
        return 0.0
    A = math.pi * (D / 2) ** 2
    if hw <= 1.2 * D:
        return KU * A * math.sqrt(D) * (hw / (K_IN * D)) ** (1.0 / M_IN)
    qun_sw = KU * A * math.sqrt(D) * ((1.2 * D) / (K_IN * D)) ** (1.0 / M_IN)
    qsub = KU * A * math.sqrt(D) * math.sqrt(max(0.0, (hw / D - Y_IN) / C_IN))
    return max(qun_sw, qsub)


def q_outlet(hw: float, D: float = D_1200, n: float = N_MANNING, L: float = L_1200, S0_: float = S0, tw: float = 0.0) -> float:
    if hw <= 0:
        return 0.0
    if hw < D:
        ratio = min(0.999, max(1e-6, hw / D))
        theta = 2.0 * math.acos(1.0 - 2.0 * ratio)
        aseg = ((D / 2) ** 2 / 2.0) * (theta - math.sin(theta))
        pwet = (D / 2) * theta
        if pwet <= 0:
            return 0.0
        rh = aseg / pwet
        return (1.0 / n) * aseg * (rh ** (2.0 / 3.0)) * math.sqrt(S0_)
    A = math.pi * (D / 2) ** 2
    rh = D / 4.0
    hloss = hw - tw + S0_ * L
    if hloss <= 0:
        return 0.0
    denom = (1.0 + KE) / (2.0 * G) + (n**2) * L / (rh ** (4.0 / 3.0))
    return A * math.sqrt(hloss / denom)


def q_1200(wse: float, pipe_factor: float = 1.0) -> float:
    hw = max(0.0, wse - Z_US)
    return max(0.0, pipe_factor * min(q_inlet(hw), q_outlet(hw)))


def q_overflow(wse: float, crest: float = CREST) -> float:
    y = wse - crest
    if y <= 0:
        return 0.0
    A = (OV_B + OV_Z * y) * y
    P = OV_B + 2.0 * y * math.sqrt(1.0 + OV_Z**2)
    if P <= 0:
        return 0.0
    R = A / P
    return (1.0 / OV_N) * A * (R ** (2.0 / 3.0)) * math.sqrt(OV_S)


def v_ditch(wse: float, crest: float = CREST) -> float:
    y = max(0.0, wse - crest)
    if y <= 0:
        return 0.0
    return (OV_B + OV_Z * y) * y * OV_L


def v_pond(wse: float, sv: list[tuple[float, float]]) -> float:
    return interp(wse, [p[0] for p in sv], [p[1] for p in sv])


def v_total(wse: float, sv: list[tuple[float, float]], crest: float, with_ditch: bool) -> float:
    return v_pond(wse, sv) + (v_ditch(wse, crest) if with_ditch else 0.0)


def wse_from_v(v: float, sv: list[tuple[float, float]], crest: float, with_ditch: bool) -> float:
    wses = [Z_POND + i * 0.05 for i in range(int((40.0 - Z_POND) / 0.05) + 1)]
    vs: list[float] = []
    ws_clean: list[float] = []
    last = -1.0
    for w in wses:
        vv = v_total(w, sv, crest, with_ditch)
        if vv >= last:
            ws_clean.append(w)
            vs.append(vv)
            last = vv
    return interp(v, vs, ws_clean)


@dataclass
class Step:
    t_min: float
    Qin: float
    WSE: float
    Q_pipe: float
    Q_ov: float
    Q_out: float
    V: float
    dt_s: float


def route(
    qpeak: float = QPEAK_REF,
    crest: float = CREST,
    pipe_factor: float = 1.0,
    with_overflow: bool = True,
) -> list[Step]:
    sv = stage_storage_curve()
    times = [t for t, _ in HYDRO_SHAPE]
    qins = [r * qpeak for _, r in HYDRO_SHAPE]
    steps: list[Step] = []
    V = 0.0
    WSE = Z_POND

    for i, (t, Qin) in enumerate(zip(times, qins)):
        if i == 0:
            qp = min(Qin, q_1200(WSE, pipe_factor))
            qo = 0.0
            qout = qp
            dt = 0.0
        else:
            dt = (times[i] - times[i - 1]) * 60.0
            WSE = wse_from_v(V, sv, crest, with_overflow)
            qp = q_1200(WSE, pipe_factor)
            qo = q_overflow(WSE, crest) if with_overflow else 0.0
            qout = qp + qo
            Qin_avg = 0.5 * (qins[i - 1] + Qin)
            if V <= 0.01:
                qout = min(Qin_avg, qout)
            V = max(0.0, V + (Qin_avg - qout) * dt)
            WSE = wse_from_v(V, sv, crest, with_overflow)
            qp = q_1200(WSE, pipe_factor)
            qo = q_overflow(WSE, crest) if with_overflow else 0.0
            qout = (qp + qo) if with_overflow else qp
        steps.append(
            Step(t, Qin, WSE, qp, qo if with_overflow else 0.0, qout, V, dt)
        )
    return steps


def summarize(steps: list[Step], crest: float = CREST) -> dict:
    Vmax = max(s.V for s in steps)
    WSEmax = max(s.WSE for s in steps)
    Qdown_max = max(s.Q_out for s in steps)
    idx = max(range(len(steps)), key=lambda i: steps[i].Q_out)
    V_ov = sum(s.Q_ov * s.dt_s for s in steps)
    return {
        "V_hold": Vmax,
        "WSEmax": WSEmax,
        "Q_down_max": Qdown_max,
        "Q_pipe_at_peak": steps[idx].Q_pipe,
        "Q_ov_at_peak": steps[idx].Q_ov,
        "V_overflow": V_ov,
        "overflow": WSEmax >= crest - 1e-6,
    }
