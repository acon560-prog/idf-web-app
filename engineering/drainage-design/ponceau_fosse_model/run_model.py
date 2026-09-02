#!/usr/bin/env python3
"""Run compound ponceau + porous-rockfill fossé model."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from hydraulics import CulvertDitchParams, build_rating_curve, solve_HW_for_Q, summarize


def main() -> int:
    ap = argparse.ArgumentParser(description="Ponceau + fossé (porous rockfill) model")
    ap.add_argument("--Q", type=float, default=9.0)
    ap.add_argument("--S0", type=float, default=None, help="Override slope (default from inverts)")
    ap.add_argument("--D", type=float, default=1.05)
    ap.add_argument("--L", type=float, default=50.9)
    ap.add_argument("--b", type=float, default=2.0)
    ap.add_argument("--z", type=float, default=2.0)
    ap.add_argument("--n-pipe", type=float, default=0.013, dest="n_pipe")
    ap.add_argument("--elev-invert", type=float, default=35.36, dest="elev_invert")
    ap.add_argument("--elev-invert-ds", type=float, default=34.47, dest="elev_invert_ds")
    ap.add_argument("--elev-max", type=float, default=37.4, dest="elev_max")
    ap.add_argument("--entrance", choices=["beveled", "square_edge", "groove_headwall"], default="beveled")
    ap.add_argument("--mode", choices=["porous", "surface", "both"], default="surface",
                    help="surface=rough rock ditch (default); porous=Wilkins seepage only")
    ap.add_argument("--d50", type=float, default=0.05, help="Rock d50 (m)")
    ap.add_argument("--porosity", type=float, default=0.40)
    ap.add_argument("--Cd-rock", type=float, default=0.85, dest="Cd_rock")
    ap.add_argument("--TW", type=float, default=0.0, help="Tailwater depth above DS invert (unknown→0)")
    ap.add_argument("--csv", type=str, default="")
    ap.add_argument("--json", type=str, default="")
    args = ap.parse_args()

    p = CulvertDitchParams(
        D=args.D,
        L=args.L,
        b=args.b,
        z=args.z,
        elev_invert=args.elev_invert,
        elev_invert_ds=args.elev_invert_ds,
        elev_max=args.elev_max,
        S0=args.S0,
        n_pipe=args.n_pipe,
        entrance=args.entrance,
        overflow_mode=args.mode,
        d50=args.d50,
        n_porosity=args.porosity,
        Cd_rock=args.Cd_rock,
        TW=args.TW,
    )

    summary = summarize(args.Q, p)
    r = solve_HW_for_Q(args.Q, p)

    print("=== Ponceau + fossé (porous rockfill overflow) ===")
    print(f"Q design            : {args.Q:.3f} m³/s")
    print(f"S0                  : {p.S0:.5f} m/m  (from Δz/L unless overridden)")
    print(f"Inverts US → DS     : {p.elev_invert} → {p.elev_invert_ds}")
    print(f"Entrance            : {p.entrance} (Ke={p.Ke})")
    print(f"Overflow mode       : {p.overflow_mode}  d50={p.d50} m  n_por={p.n_porosity}")
    print(f"TW (assumed)        : {p.TW:.3f} m above DS invert  ← unknown on site")
    print(f"D / L / b / z       : {p.D} / {p.L} / {p.b} / {p.z}")
    print(f"Crown elev          : {p.elev_invert + p.D:.3f} m")
    print(f"Max WSE             : {p.elev_max} m  (Hmax={p.max_depth():.3f} m)")
    print("---")
    print(f"HW (depth)          : {r.HW:.3f} m")
    print(f"WSE                 : {r.WSE:.3f} m")
    print(f"Q_pipe              : {r.Q_pipe:.3f} m³/s")
    print(f"Q_overflow (rock)   : {r.Q_ditch:.3f} m³/s")
    print(f"Q_total             : {r.Q_total:.3f} m³/s   [{r.control}]")
    print(f"Pipe @ crown        : {summary['pipe_capacity_at_crown_m3s']:.3f} m³/s")
    if summary["exceeds_max_stage"]:
        print("WARNING: Q exceeds capacity at elev_max=37.4 — stage would go above Max hauteur d'eau.")
    elif summary["overflow_active"]:
        print("OK: culvert overloaded → flow through rockfill is active.")
    else:
        print("OK: pipe-only (below crown).")

    if args.csv:
        path = Path(args.csv)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["HW_m", "WSE_m", "Q_pipe_m3s", "Q_overflow_m3s", "Q_total_m3s", "control"])
            for pt in build_rating_curve(p):
                w.writerow(
                    [
                        f"{pt.HW:.4f}",
                        f"{pt.WSE:.4f}",
                        f"{pt.Q_pipe:.4f}",
                        f"{pt.Q_ditch:.4f}",
                        f"{pt.Q_total:.4f}",
                        pt.control,
                    ]
                )
        print(f"Rating curve: {path}")

    if args.json:
        path = Path(args.json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"JSON: {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
