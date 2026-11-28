"""
Invented channel profile for demo: velocity along a ditch (Manning normal depth).

Data is synthetic (not from AutoCAD) so you can learn the method before DXF arrives.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

G = 9.81
DEMO_DIR = Path(__file__).resolve().parent / "demo_data"


@dataclass
class SectionGeom:
    station_m: float
    offsets: list[float]  # m, left negative → right positive
    elevs: list[float]  # m


@dataclass
class SectionResult:
    station_m: float
    bed_elev: float
    S0: float
    y_m: float  # depth above local min bed
    WSE: float
    A: float
    P: float
    R: float
    V: float
    Fr: float
    Q_check: float
    ok: bool
    note: str


def write_demo_csvs() -> None:
    """Create invented longitudinal + cross-section CSVs."""
    DEMO_DIR.mkdir(parents=True, exist_ok=True)

    # Longitudinal bed (invert) — gentle ditch with a low point near mid-reach
    # station 0 → 100 m
    long_pts = [
        (0.0, 36.50),
        (10.0, 36.35),
        (20.0, 36.15),
        (30.0, 35.90),
        (40.0, 35.60),
        (50.0, 35.40),  # low area
        (60.0, 35.55),
        (70.0, 35.85),
        (80.0, 36.10),
        (90.0, 36.25),
        (100.0, 36.40),
    ]
    with (DEMO_DIR / "Longitudinal_demo.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["station_m", "elev_m"])
        w.writerows(long_pts)

    # Trapezoid-ish sections at selected stations (offset, elev)
    # Bottom ~2 m wide, side slopes ~2H:1V, banks higher
    def trap(station: float, bed: float, b: float = 2.0, z: float = 2.0, bank: float = 2.0):
        # points left bank → right bank
        y_bank = bed + bank
        half = b / 2.0
        pts = [
            (-half - z * bank, y_bank),
            (-half, bed),
            (half, bed),
            (half + z * bank, y_bank),
        ]
        path = DEMO_DIR / f"section_STA{int(station):04d}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["station_m", "offset_m", "elev_m"])
            for off, el in pts:
                w.writerow([station, round(off, 3), round(el, 3)])

    for s, zb in [(0.0, 36.50), (20.0, 36.15), (40.0, 35.60), (50.0, 35.40), (70.0, 35.85), (100.0, 36.40)]:
        # slightly wider at low point
        b = 2.5 if 40 <= s <= 60 else 2.0
        trap(s, zb, b=b, z=2.0, bank=1.8)


def load_longitudinal(path: Path) -> list[tuple[float, float]]:
    rows: list[tuple[float, float]] = []
    with path.open(encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append((float(row["station_m"]), float(row["elev_m"])))
    rows.sort(key=lambda x: x[0])
    return rows


def load_sections(folder: Path) -> list[SectionGeom]:
    sections: list[SectionGeom] = []
    for path in sorted(folder.glob("section_*.csv")):
        offs: list[float] = []
        elevs: list[float] = []
        station = None
        with path.open(encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                station = float(row["station_m"])
                offs.append(float(row["offset_m"]))
                elevs.append(float(row["elev_m"]))
        if station is None or len(offs) < 3:
            continue
        # sort by offset
        pairs = sorted(zip(offs, elevs), key=lambda p: p[0])
        sections.append(
            SectionGeom(station_m=station, offsets=[p[0] for p in pairs], elevs=[p[1] for p in pairs])
        )
    sections.sort(key=lambda s: s.station_m)
    return sections


def bed_slope_at(station: float, long_pts: list[tuple[float, float]]) -> float:
    """Forward/backward difference on longitudinal invert."""
    if len(long_pts) < 2:
        return 1e-4
    # find segment containing station
    for i in range(len(long_pts) - 1):
        s0, z0 = long_pts[i]
        s1, z1 = long_pts[i + 1]
        if s0 - 1e-9 <= station <= s1 + 1e-9:
            ds = max(s1 - s0, 1e-6)
            return max(abs(z0 - z1) / ds, 1e-5)
    # outside: use nearest end segment
    s0, z0 = long_pts[0]
    s1, z1 = long_pts[1]
    return max(abs(z0 - z1) / max(s1 - s0, 1e-6), 1e-5)


def interp_elev(offsets: list[float], elevs: list[float], x: float) -> float:
    if x <= offsets[0]:
        return elevs[0]
    if x >= offsets[-1]:
        return elevs[-1]
    for i in range(len(offsets) - 1):
        if offsets[i] <= x <= offsets[i + 1]:
            t = (x - offsets[i]) / (offsets[i + 1] - offsets[i])
            return elevs[i] + t * (elevs[i + 1] - elevs[i])
    return elevs[-1]


def section_AP(sec: SectionGeom, WSE: float) -> tuple[float, float]:
    """Flow area A and wetted perimeter P at water-surface elevation WSE."""
    xs = sec.offsets
    zs = sec.elevs
    A = 0.0
    P = 0.0

    for i in range(len(xs) - 1):
        x0, z0 = xs[i], zs[i]
        x1, z1 = xs[i + 1], zs[i + 1]
        d0 = WSE - z0
        d1 = WSE - z1

        if d0 <= 0 and d1 <= 0:
            continue

        if d0 >= 0 and d1 >= 0:
            A += 0.5 * (d0 + d1) * abs(x1 - x0)
            P += math.hypot(x1 - x0, z1 - z0)
            continue

        # one end dry: intersect free surface
        t = d0 / (d0 - d1)
        t = min(1.0, max(0.0, t))
        xi = x0 + t * (x1 - x0)
        zi = WSE
        if d0 > 0:
            A += 0.5 * d0 * abs(xi - x0)
            P += math.hypot(xi - x0, zi - z0)
        else:
            A += 0.5 * d1 * abs(x1 - xi)
            P += math.hypot(x1 - xi, z1 - zi)

    return A, P


def manning_Q(n: float, A: float, P: float, S0: float) -> float:
    if n <= 0 or A <= 0 or P <= 0 or S0 <= 0:
        return 0.0
    R = A / P
    return (1.0 / n) * A * (R ** (2.0 / 3.0)) * math.sqrt(S0)


def solve_normal_depth(
    sec: SectionGeom,
    Q: float,
    n: float,
    S0: float,
) -> SectionResult:
    bed = min(sec.elevs)
    top = max(sec.elevs)
    if Q <= 0:
        return SectionResult(sec.station_m, bed, S0, 0, bed, 0, 0, 0, 0, 0, 0, True, "Q=0")

    # bisection on WSE
    lo, hi = bed + 1e-4, top - 1e-4
    A_hi, P_hi = section_AP(sec, hi)
    Q_hi = manning_Q(n, A_hi, P_hi, S0)
    if Q_hi < Q:
        # overtopping banks — report at bankful
        V = Q / A_hi if A_hi > 0 else 0.0
        Fr = V / math.sqrt(G * (A_hi / max(right_width(sec, hi), 1e-6))) if A_hi > 0 else 0.0
        return SectionResult(
            sec.station_m,
            bed,
            S0,
            hi - bed,
            hi,
            A_hi,
            P_hi,
            A_hi / P_hi if P_hi > 0 else 0,
            V,
            Fr,
            Q_hi,
            False,
            "Q > bankful capacity (normal depth would overtop)",
        )

    for _ in range(60):
        mid = 0.5 * (lo + hi)
        A, P = section_AP(sec, mid)
        Qm = manning_Q(n, A, P, S0)
        if Qm < Q:
            lo = mid
        else:
            hi = mid
    WSE = 0.5 * (lo + hi)
    A, P = section_AP(sec, WSE)
    R = A / P if P > 0 else 0.0
    V = Q / A if A > 0 else 0.0
    Tw = right_width(sec, WSE)
    Fr = V / math.sqrt(G * (A / Tw)) if A > 0 and Tw > 0 else 0.0
    Qc = manning_Q(n, A, P, S0)
    return SectionResult(
        sec.station_m,
        bed,
        S0,
        WSE - bed,
        WSE,
        A,
        P,
        R,
        V,
        Fr,
        Qc,
        True,
        "OK",
    )


def right_width(sec: SectionGeom, WSE: float) -> float:
    """Top width at WSE."""
    xs, zs = sec.offsets, sec.elevs
    left = None
    right = None
    for i in range(len(xs) - 1):
        z0, z1 = zs[i], zs[i + 1]
        x0, x1 = xs[i], xs[i + 1]
        if (z0 - WSE) * (z1 - WSE) <= 0 and abs(z1 - z0) > 1e-12:
            t = (WSE - z0) / (z1 - z0)
            x = x0 + t * (x1 - x0)
            if left is None:
                left = x
            right = x
    if left is None or right is None:
        return 1.0
    return max(right - left, 1e-3)


def run_profile(
    Q: float,
    n: float = 0.035,
    long_path: Path | None = None,
    section_dir: Path | None = None,
) -> list[SectionResult]:
    long_path = long_path or (DEMO_DIR / "Longitudinal_demo.csv")
    section_dir = section_dir or DEMO_DIR
    if not long_path.exists():
        write_demo_csvs()
    long_pts = load_longitudinal(long_path)
    sections = load_sections(section_dir)
    out: list[SectionResult] = []
    for sec in sections:
        S0 = bed_slope_at(sec.station_m, long_pts)
        out.append(solve_normal_depth(sec, Q, n, S0))
    return out


def main() -> None:
    write_demo_csvs()
    Q = 2.0
    n = 0.035
    results = run_profile(Q, n)
    print(f"Demo inventé — Q={Q} m³/s, n={n}")
    print(f"{'Sta':>7} {'S0':>8} {'y':>7} {'WSE':>8} {'A':>7} {'V':>7} {'Fr':>6}  note")
    for r in results:
        print(
            f"{r.station_m:7.1f} {r.S0:8.5f} {r.y_m:7.3f} {r.WSE:8.3f} "
            f"{r.A:7.3f} {r.V:7.3f} {r.Fr:6.2f}  {r.note}"
        )


if __name__ == "__main__":
    main()
