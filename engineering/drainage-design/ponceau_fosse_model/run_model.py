#!/usr/bin/env python3
"""Run compound ponceau + fossé rating and design-Q solution."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from hydraulics import CulvertDitchParams, build_rating_curve, solve_HW_for_Q, summarize


def main() -> int:
    ap = argparse.ArgumentParser(description="Ponceau + fossé compound hydraulic model")
    ap.add_argument("--Q", type=float, default=9.0, help="Incoming discharge (m³/s)")
    ap.add_argument("--S0", type=float, default=0.01, help="Longitudinal slope (m/m)")
    ap.add_argument("--D", type=float, default=1.05, help="Pipe diameter (m)")
    ap.add_argument("--L", type=float, default=50.9, help="Pipe length (m)")
    ap.add_argument("--b", type=float, default=2.0, help="Ditch bottom width (m)")
    ap.add_argument("--z", type=float, default=2.0, help="Ditch side slope z (H:V)")
    ap.add_argument("--n-pipe", type=float, default=0.013, dest="n_pipe")
    ap.add_argument("--n-ditch", type=float, default=0.045, dest="n_ditch")
    ap.add_argument("--elev-invert", type=float, default=35.13, dest="elev_invert")
    ap.add_argument("--elev-max", type=float, default=37.4, dest="elev_max")
    ap.add_argument("--TW", type=float, default=0.0, help="Tailwater depth above outlet invert (m)")
    ap.add_argument("--csv", type=str, default="", help="Optional rating-curve CSV path")
    ap.add_argument("--json", type=str, default="", help="Optional JSON summary path")
    args = ap.parse_args()

    p = CulvertDitchParams(
        D=args.D,
        L=args.L,
        b=args.b,
        z=args.z,
        elev_invert=args.elev_invert,
        elev_max=args.elev_max,
        S0=args.S0,
        n_pipe=args.n_pipe,
        n_ditch=args.n_ditch,
        TW=args.TW,
    )

    summary = summarize(args.Q, p)
    r = solve_HW_for_Q(args.Q, p)

    print("=== Ponceau + fossé (compound) ===")
    print(f"Q design          : {args.Q:.3f} m³/s")
    print(f"S0 (ASSUMED/SET)  : {p.S0:.4f} m/m   ← confirm on drawings")
    print(f"D / L / b / z     : {p.D} m / {p.L} m / {p.b} m / {p.z}")
    print(f"Invert → max      : {p.elev_invert} → {p.elev_max} (Hmax={p.max_depth():.3f} m)")
    print(f"Overflow starts   : y = {p.overflow_depth():.3f} m above invert (default = crown)")
    print("---")
    print(f"HW (depth)        : {r.HW:.3f} m")
    print(f"WSE               : {r.WSE:.3f} m")
    print(f"Q_pipe            : {r.Q_pipe:.3f} m³/s   [{r.control}]")
    print(f"Q_ditch           : {r.Q_ditch:.3f} m³/s")
    print(f"Q_total           : {r.Q_total:.3f} m³/s")
    print(f"Pipe @ crown      : {summary['pipe_capacity_at_crown_m3s']:.3f} m³/s")
    if summary["exceeds_max_stage"]:
        print("WARNING: Q exceeds capacity at elev_max — water would go above Max hauteur d'eau.")
    elif summary["overflow_active"]:
        print("OK: culvert capacity exceeded → fossé (rockfill) conveyance is active.")
    else:
        print("OK: flow conveyed in pipe only (below overflow threshold).")

    if args.csv:
        path = Path(args.csv)
        path.parent.mkdir(parents=True, exist_ok=True)
        pts = build_rating_curve(p)
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["HW_m", "WSE_m", "Q_pipe_m3s", "Q_ditch_m3s", "Q_total_m3s", "control"])
            for pt in pts:
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
        print(f"Rating curve written: {path}")

    if args.json:
        path = Path(args.json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"JSON summary written: {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
