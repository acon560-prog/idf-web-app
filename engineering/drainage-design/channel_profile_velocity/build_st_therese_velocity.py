#!/usr/bin/env python3
"""
Ste-Thérèse ditch — real surveyed sections + longitudinal profile.
Compute Manning normal-depth velocity for Q=7.36 m³/s, n=0.035.

Policy on slopes:
  - Display the real signed S0 from the longitudinal survey (adverse stays negative).
  - Compute Manning velocity only where S0 > 0.
  - Where S0 <= 0 or missing: leave y / WSE / V blank (no |S0|).
"""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from profile_velocity import SectionGeom, solve_normal_depth

UPLOADS = Path("/home/ubuntu/.cursor/projects/workspace/uploads")
OUT_DIR = Path(__file__).resolve().parent / "st_therese_data"
OUT_XLSX = Path(__file__).resolve().parent / "SteTherese_Fosse_Vitesse_Q736.xlsx"

Q_DESIGN = 7.36
N_MANNING = 0.035

# Map section labels → cumulative station from Longitudinal_5712.txt
SECTION_STATIONS = {
    "1+000": 0.0,
    "2+000": 13.783,
    "3+000": 23.663,
    "4+000": 35.641,
    "5+000": 45.838,
    "6+000": 59.435,
    "7+000": 71.973,
    "8+000": 89.361,
}

HEADER = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="0F5C5C")
YELLOW = PatternFill("solid", fgColor="FFF59D")
OK = PatternFill("solid", fgColor="D1FAE5")
SKIP = PatternFill("solid", fgColor="FCE4D6")  # adverse / flat — no V
WARN = PatternFill("solid", fgColor="FDE68A")
THIN = Border(
    left=Side(style="thin", color="CBD5E1"),
    right=Side(style="thin", color="CBD5E1"),
    top=Side(style="thin", color="CBD5E1"),
    bottom=Side(style="thin", color="CBD5E1"),
)


def style_header(ws, row: int, cols: int) -> None:
    for c in range(1, cols + 1):
        cell = ws.cell(row, c)
        cell.font = HEADER
        cell.fill = HEADER_FILL


def parse_longitudinal(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    # header: Point, Z fond, ΔL, S0, Station cumulées
    for ln in lines[1:]:
        parts = re.split(r"\t+", ln)
        if len(parts) < 5:
            parts = re.split(r"\s{2,}|\t+", ln)
        if len(parts) < 5:
            parts = ln.replace(",", ".").split()
        point = parts[0]
        z = float(parts[1].replace(",", "."))
        s0_raw = parts[3]
        sta = float(parts[4].replace(",", "."))
        if "—" in s0_raw or s0_raw.strip() in ("—", "-", ""):
            s0 = None
        else:
            s0 = float(s0_raw.replace(",", "."))
        try:
            dL = float(parts[2].replace(",", ".")) if "—" not in parts[2] else None
        except ValueError:
            dL = None
        rows.append({"point": point, "z": z, "dL": dL, "S0": s0, "station": sta})
    return rows


def parse_sections(path: Path) -> dict[str, list[tuple[float, float, str]]]:
    """Return {section_id: [(distance, elev, desc), ...]} sorted by distance."""
    text = path.read_text(encoding="utf-8")
    sections: dict[str, list[tuple[float, float, str]]] = {}
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("Est-ce que"):
            continue
        m = re.match(r"SECTION\s+(\d+\+\d+)", line, re.I)
        if m:
            current = m.group(1)
            sections[current] = []
            continue
        if current is None:
            continue
        if line.lower().startswith("point"):
            continue
        parts = re.split(r"\s+", line)
        if len(parts) < 4:
            continue
        try:
            dist = float(parts[-1].replace(",", "."))
            elev = float(parts[1].replace(",", "."))
        except ValueError:
            continue
        desc = parts[2]
        sections[current].append((dist, elev, desc))
    for k in sections:
        sections[k].sort(key=lambda t: t[0])
    return sections


def s0_at_station(long_rows: list[dict], station: float) -> tuple[float | None, str]:
    """Return real signed S0 at/near station (no abs). None if missing."""
    for r in long_rows:
        if abs(r["station"] - station) < 0.05 and r["S0"] is not None:
            s = r["S0"]
            if s < 0:
                return s, f"S0 réel adverse = {s:.5f} — V non calculée"
            if s == 0:
                return s, "S0 réel = 0 — V non calculée"
            return s, "S0 réel (table long.)"
    candidates = [r for r in long_rows if r["S0"] is not None]
    if not candidates:
        return None, "S0 manquant — V non calculée"
    nearest = min(candidates, key=lambda r: abs(r["station"] - station))
    s = nearest["S0"]
    tag = f"S0 réel nearest @ {nearest['station']:.2f} m = {s:.5f}"
    if s is None or s <= 0:
        return s, f"{tag} — V non calculée"
    return s, tag


def _seg_area_formula(wse_cell: str, x0: str, z0: str, x1: str, z1: str) -> str:
    """Excel formula: wet area of one polyline segment at WSE (same logic as section_AP)."""
    d0 = f"({wse_cell}-{z0})"
    d1 = f"({wse_cell}-{z1})"
    # intersection parameter t = d0/(d0-d1); xi = x0 + t*(x1-x0)
    t = f"({d0}/({d0}-{d1}))"
    xi = f"({x0}+{t}*({x1}-{x0}))"
    both_dry = f"AND({d0}<=0,{d1}<=0)"
    both_wet = f"AND({d0}>=0,{d1}>=0)"
    a_full = f"0.5*({d0}+{d1})*ABS({x1}-{x0})"
    a_left = f"0.5*{d0}*ABS({xi}-{x0})"
    a_right = f"0.5*{d1}*ABS({x1}-{xi})"
    return (
        f'IF({both_dry},0,'
        f'IF({both_wet},{a_full},'
        f'IF({d0}>0,{a_left},{a_right})))'
    )


def _seg_peri_formula(wse_cell: str, x0: str, z0: str, x1: str, z1: str) -> str:
    """Excel formula: wetted length of one polyline segment at WSE."""
    d0 = f"({wse_cell}-{z0})"
    d1 = f"({wse_cell}-{z1})"
    t = f"({d0}/({d0}-{d1}))"
    xi = f"({x0}+{t}*({x1}-{x0}))"
    both_dry = f"AND({d0}<=0,{d1}<=0)"
    both_wet = f"AND({d0}>=0,{d1}>=0)"
    p_full = f"SQRT(({x1}-{x0})^2+({z1}-{z0})^2)"
    p_left = f"SQRT(({xi}-{x0})^2+({wse_cell}-{z0})^2)"
    p_right = f"SQRT(({x1}-{xi})^2+({wse_cell}-{z1})^2)"
    return (
        f'IF({both_dry},0,'
        f'IF({both_wet},{p_full},'
        f'IF({d0}>0,{p_left},{p_right})))'
    )


def add_area_formula_sheets(
    wb: Workbook,
    sections: dict[str, list[tuple[float, float, str]]],
    results: list,
) -> None:
    """One sheet per section with live Excel formulas for A and P vs editable WSE."""
    # Overview / theory
    wsF = wb.create_sheet("Formules_Aire", 1)
    wsF["A1"] = "Comment l'aire A est calculée (formules Excel actives dans les onglets Aire_*)"
    wsF["A1"].font = Font(bold=True, size=13, color="0F5C5C")
    lines = [
        "",
        "Géométrie: chaque coupe = polyligne Distance (x) vs Elev (z) du fichier sections.",
        "On fixe une cote d'eau WSE. Pour chaque segment [i → i+1]:",
        "",
        "  d0 = WSE − z_i     d1 = WSE − z_{i+1}",
        "",
        "  1) Segment totalement sec (d0≤0 et d1≤0):     Ai = 0 ,  Pi = 0",
        "  2) Segment totalement mouillé (d0≥0 et d1≥0):",
        "        Ai = ½ · (d0 + d1) · |x_{i+1} − x_i|     (trapèze)",
        "        Pi = √[(x_{i+1}−x_i)² + (z_{i+1}−z_i)²]  (longueur du fond)",
        "  3) Un bout sec / un bout mouillé: intersection avec WSE en xi,",
        "        Ai = ½ · d_wet · |xi − x_wet|            (triangle)",
        "        Pi = longueur du bout mouillé jusqu'à xi",
        "",
        "  A = Σ Ai     P = Σ Pi     R = A/P",
        "  Si S0 > 0:  Q_manning = (1/n)·A·R^(2/3)·√S0     V = Q / A",
        "",
        "Onglets Aire_1+000 … Aire_8+000: cellule WSE jaune éditable → A et P se recalculent.",
        "La WSE initiale est celle de la profondeur normale (si S0>0), sinon fond+1 m.",
        "Les résultats Resultats_Q736 restent les valeurs Manning résolues par Python.",
    ]
    for i, line in enumerate(lines, start=2):
        wsF.cell(i, 1, line)
    wsF.column_dimensions["A"].width = 110

    wse_by_sid = {}
    for sid, _snote, _S0, computed, r in results:
        if computed and not math.isnan(getattr(r, "WSE", float("nan"))):
            wse_by_sid[sid] = float(r.WSE)
        else:
            wse_by_sid[sid] = None

    s0_by_sid = {sid: S0 for sid, _n, S0, _c, _r in results}

    for sid in sorted(SECTION_STATIONS.keys(), key=lambda x: SECTION_STATIONS[x]):
        pts = sections[sid]
        safe = sid.replace("+", "")
        ws = wb.create_sheet(f"Aire_{safe}")
        bed = min(p[1] for p in pts)
        wse0 = wse_by_sid[sid] if wse_by_sid[sid] is not None else bed + 1.0
        s0 = s0_by_sid.get(sid)

        ws["A1"] = f"Section {sid} — aire / périmètre mouillés (formules Excel)"
        ws["A1"].font = Font(bold=True, size=12, color="0F5C5C")
        ws.merge_cells("A1:G1")

        ws["A2"] = "WSE (m)"
        ws["B2"] = round(wse0, 4)
        ws["B2"].fill = YELLOW
        ws["B2"].border = THIN
        ws["C2"] = "← éditer (jaune) : A et P se recalculent"
        ws["C2"].font = Font(italic=True, color="64748B")

        ws["A3"] = "Station cum. (m)"
        ws["B3"] = SECTION_STATIONS[sid]
        ws["A4"] = "S0 réel"
        ws["B4"] = s0 if s0 is not None else None
        if s0 is not None and s0 <= 0:
            ws["B4"].fill = SKIP
            ws["C4"] = "adverse/nulle — Manning non applicable"
        ws["A5"] = "Q (m³/s)"
        ws["B5"] = Q_DESIGN
        ws["B5"].fill = YELLOW
        ws["A6"] = "n Manning"
        ws["B6"] = N_MANNING
        ws["B6"].fill = YELLOW

        # Point table starts at row 8
        hdr_row = 8
        for j, h in enumerate(
            ["#", "Distance x (m)", "Elev z (m)", "Desc", "d=WSE−z", "Ai segment (m²)", "Pi segment (m)"],
            start=1,
        ):
            ws.cell(hdr_row, j, h)
        style_header(ws, hdr_row, 7)

        first = hdr_row + 1
        for i, (x, z, desc) in enumerate(pts):
            r = first + i
            ws.cell(r, 1, i + 1).border = THIN
            ws.cell(r, 2, round(x, 4)).border = THIN
            ws.cell(r, 3, round(z, 4)).border = THIN
            ws.cell(r, 4, desc).border = THIN
            ws.cell(r, 5, f"=$B$2-C{r}").border = THIN
            if i < len(pts) - 1:
                x0, z0, x1, z1 = f"B{r}", f"C{r}", f"B{r+1}", f"C{r+1}"
                ws.cell(r, 6, f"={_seg_area_formula('$B$2', x0, z0, x1, z1)}").border = THIN
                ws.cell(r, 7, f"={_seg_peri_formula('$B$2', x0, z0, x1, z1)}").border = THIN
            else:
                ws.cell(r, 6, None).border = THIN
                ws.cell(r, 7, None).border = THIN

        last_pt = first + len(pts) - 1
        last_seg = last_pt - 1

        sum_row = last_pt + 2
        ws.cell(sum_row, 1, "Totaux").font = Font(bold=True)
        ws.cell(sum_row, 5, "A = Σ Ai")
        ws.cell(sum_row, 6, f"=SUM(F{first}:F{last_seg})")
        ws.cell(sum_row, 6).fill = OK
        ws.cell(sum_row, 6).font = Font(bold=True)
        ws.cell(sum_row, 6).number_format = "0.0000"
        ws.cell(sum_row, 7, f"=SUM(G{first}:G{last_seg})")
        ws.cell(sum_row, 7).fill = OK
        ws.cell(sum_row, 7).font = Font(bold=True)
        ws.cell(sum_row, 7).number_format = "0.0000"
        ws.cell(sum_row - 1, 7, "P = Σ Pi")

        # Derived
        drow = sum_row + 2
        ws.cell(drow, 1, "Fond min (m)")
        ws.cell(drow, 2, f"=MIN(C{first}:C{last_pt})")
        ws.cell(drow + 1, 1, "y = WSE − fond (m)")
        ws.cell(drow + 1, 2, f"=B2-B{drow}")
        ws.cell(drow + 2, 1, "A (m²)")
        ws.cell(drow + 2, 2, f"=F{sum_row}")
        ws.cell(drow + 2, 2).fill = OK
        ws.cell(drow + 3, 1, "P (m)")
        ws.cell(drow + 3, 2, f"=G{sum_row}")
        ws.cell(drow + 3, 2).fill = OK
        ws.cell(drow + 4, 1, "R = A/P (m)")
        ws.cell(drow + 4, 2, f"=IF(B{drow+3}>0,B{drow+2}/B{drow+3},0)")
        ws.cell(drow + 5, 1, "Q_manning (m³/s)")
        if s0 is not None and s0 > 0:
            # Q = (1/n)*A*R^(2/3)*SQRT(S0)
            ws.cell(
                drow + 5,
                2,
                f'=IF(OR(B6<=0,B{drow+2}<=0,B4<=0),0,(1/B6)*B{drow+2}*(B{drow+4}^(2/3))*SQRT(B4))',
            )
            ws.cell(drow + 6, 1, "V = Q/A (m/s)")
            ws.cell(drow + 6, 2, f"=IF(B{drow+2}>0,B5/B{drow+2},0)")
            ws.cell(drow + 6, 2).fill = OK
            ws.cell(drow + 7, 1, "Note")
            ws.cell(
                drow + 7,
                2,
                "V utilise Q de B5 (débit de projet). Pour la profondeur normale, ajuster WSE jusqu'à Q_manning ≈ Q.",
            )
        else:
            ws.cell(drow + 5, 2, None)
            ws.cell(drow + 5, 3, "S0≤0 → pas de Manning / V")
            ws.cell(drow + 5, 3).fill = SKIP

        for col, w in zip("ABCDEFG", [6, 14, 12, 10, 12, 16, 16]):
            ws.column_dimensions[col].width = w


def export_clean_csvs(long_rows: list[dict], sections: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "Longitudinal_st_therese.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["station_m", "elev_m", "S0_raw", "point"])
        for r in long_rows:
            w.writerow([r["station"], r["z"], r["S0"] if r["S0"] is not None else "", r["point"]])

    for sid, pts in sections.items():
        sta = SECTION_STATIONS[sid]
        name = f"section_{sid.replace('+','')}_sta{sta:.0f}.csv"
        with (OUT_DIR / name).open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["station_m", "offset_m", "elev_m", "desc"])
            for dist, elev, desc in pts:
                w.writerow([sta, dist, elev, desc])


def main() -> None:
    long_path = UPLOADS / "Longitudinal_5712.txt"
    sec_path = UPLOADS / "sections_stetheres_une_par_une_1c79.txt"
    long_rows = parse_longitudinal(long_path)
    sections = parse_sections(sec_path)
    export_clean_csvs(long_rows, sections)

    results = []
    for sid in sorted(SECTION_STATIONS.keys(), key=lambda x: SECTION_STATIONS[x]):
        sta = SECTION_STATIONS[sid]
        pts = sections[sid]
        offs = [p[0] for p in pts]
        elevs = [p[1] for p in pts]
        sec = SectionGeom(station_m=sta, offsets=offs, elevs=elevs)
        S0_real, snote = s0_at_station(long_rows, sta)
        if S0_real is not None and S0_real > 0.0:
            r = solve_normal_depth(sec, Q_DESIGN, N_MANNING, S0_real)
            results.append((sid, snote, S0_real, True, r))
        else:
            # Keep real S0 (negative or None); do not invent |S0| or a velocity
            bed = min(elevs)
            results.append(
                (
                    sid,
                    snote,
                    S0_real,
                    False,
                    type("R", (), {
                        "station_m": sta,
                        "bed_elev": bed,
                        "S0": S0_real,
                        "y_m": float("nan"),
                        "WSE": float("nan"),
                        "A": float("nan"),
                        "P": float("nan"),
                        "R": float("nan"),
                        "V": float("nan"),
                        "Fr": float("nan"),
                        "ok": False,
                        "note": "pente adverse/nulle — Manning non appliqué",
                    })(),
                )
            )

    # Print summary
    print(f"Q={Q_DESIGN} m³/s  n={N_MANNING}")
    print(f"{'Sec':>8} {'Sta':>8} {'S0_reel':>10} {'y':>7} {'WSE':>8} {'A':>7} {'V':>7} {'Fr':>6}  status")
    for sid, snote, S0_real, computed, r in results:
        s0_str = f"{S0_real:10.5f}" if S0_real is not None else f"{'—':>10}"
        if computed and not math.isnan(r.V):
            print(
                f"{sid:>8} {r.station_m:8.2f} {s0_str} {r.y_m:7.3f} {r.WSE:8.3f} "
                f"{r.A:7.3f} {r.V:7.3f} {r.Fr:6.2f}  {r.note}"
            )
        else:
            print(
                f"{sid:>8} {r.station_m:8.2f} {s0_str} {'—':>7} {'—':>8} "
                f"{'—':>7} {'—':>7} {'—':>6}  {snote}"
            )

    # Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Resultats_Q736"
    ws["A1"] = "Fossé Ste-Thérèse — vitesse aux sections réelles (survey)"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = (
        f"Q = {Q_DESIGN} m³/s ; n = {N_MANNING} ; Manning profondeur normale si S0 > 0. "
        "Pentes adverses: S0 réel affiché, V non calculée (pas de |S0|)."
    )
    ws["A2"].font = Font(italic=True, color="64748B")
    ws.merge_cells("A2:L2")

    ws["A4"] = "Q (m³/s)"
    ws["B4"] = Q_DESIGN
    ws["B4"].fill = YELLOW
    ws["A5"] = "n Manning"
    ws["B5"] = N_MANNING
    ws["B5"].fill = YELLOW
    ws["C5"] = "Pour recalculer: éditer build_st_therese_velocity.py puis python build_st_therese_velocity.py"

    hdr = [
        "Section",
        "Station cum. (m)",
        "S0 réel (signé)",
        "y (m)",
        "WSE (m)",
        "Fond min (m)",
        "A (m²)",
        "P (m)",
        "R (m)",
        "V (m/s)",
        "Fr",
        "OK?",
        "Note S0 / capacité",
    ]
    for j, h in enumerate(hdr, start=1):
        ws.cell(7, j, h)
    style_header(ws, 7, len(hdr))

    for i, (sid, snote, S0_real, computed, r) in enumerate(results, start=8):
        note = snote if (computed and r.ok) else (
            snote if not computed else f"{snote} | {r.note}"
        )
        if computed and not math.isnan(r.V):
            vals = [
                sid,
                round(r.station_m, 3),
                round(S0_real, 5) if S0_real is not None else None,
                round(r.y_m, 3),
                round(r.WSE, 3),
                round(r.bed_elev, 3),
                round(r.A, 3),
                round(r.P, 3),
                round(r.R, 3),
                round(r.V, 3),
                round(r.Fr, 2),
                "Oui" if r.ok else "Non",
                note,
            ]
            row_fill = OK if r.ok else WARN
        else:
            vals = [
                sid,
                round(r.station_m, 3),
                round(S0_real, 5) if S0_real is not None else None,
                None,
                None,
                round(r.bed_elev, 3),
                None,
                None,
                None,
                None,
                None,
                "—",
                note,
            ]
            row_fill = SKIP

        for j, v in enumerate(vals, start=1):
            cell = ws.cell(i, j, v)
            cell.border = THIN
            if j == 3 and S0_real is not None and S0_real <= 0:
                cell.fill = SKIP
                cell.number_format = "0.00000"
            elif j == 10:
                cell.fill = row_fill
            elif not computed and j in (4, 5, 7, 8, 9, 10, 11):
                cell.fill = SKIP

    last = 7 + len(results)
    vs = [r.V for _, _, _, computed, r in results if computed and not math.isnan(r.V)]
    ys = [r.y_m for _, _, _, computed, r in results if computed and not math.isnan(r.y_m)]
    ws.cell(last + 2, 1, "V max (S0>0 seulement)")
    ws.cell(last + 2, 2, round(max(vs), 3) if vs else None)
    ws.cell(last + 2, 2).fill = OK
    ws.cell(last + 2, 3, "m/s")
    ws.cell(last + 3, 1, "V min (S0>0 seulement)")
    ws.cell(last + 3, 2, round(min(vs), 3) if vs else None)
    ws.cell(last + 3, 3, "m/s")
    ws.cell(last + 4, 1, "y max (S0>0 seulement)")
    ws.cell(last + 4, 2, round(max(ys), 3) if ys else None)
    ws.cell(last + 4, 3, "m")

    ws.cell(last + 6, 1, "Notes")
    ws.cell(last + 6, 1).font = Font(bold=True)
    notes = [
        "• Coupes réelles (Distance vs Elev), pas un trapèze constant.",
        "• S0 = pente longitudinale RÉELLE signée du survey (adverse reste négative).",
        "• Si S0 ≤ 0 : pas de calcul Manning → y / WSE / V vides. Pas de |S0|.",
        "• Si S0 > 0 : V = Q / A à la profondeur normale.",
        "• Fr > 1 ≈ régime torrentiel local.",
        "• Voir onglets Formules_Aire et Aire_* : formules Excel live pour A et P.",
        "• CSV nettoyés dans st_therese_data/ pour relecture.",
        "• Lignes orange = pente adverse/nulle. Lignes vertes = Manning OK.",
    ]
    for k, line in enumerate(notes):
        ws.cell(last + 7 + k, 1, line)
        ws.merge_cells(start_row=last + 7 + k, start_column=1, end_row=last + 7 + k, end_column=8)

    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 14
    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["M"].width = 48

    # Methode sheet
    wsM = wb.create_sheet("Methode")
    wsM["A1"] = "Méthode"
    wsM["A1"].font = Font(bold=True, size=13)
    for i, line in enumerate(
        [
            "",
            "À chaque section transversale surveyée:",
            "  1) Lire S0 réel (signé) sur le profil longitudinal à la station de la coupe",
            "  2) Si S0 ≤ 0 → arrêter : afficher S0 réel, laisser V / y / WSE vides",
            "  3) Si S0 > 0 → construire A(WSE), P(WSE) sur la polyligne Distance–Elev",
            "  4) Chercher WSE tel que (1/n)·A·R^(2/3)·√S0 = Q",
            "  5) V = Q / A",
            "",
            "Aire mouillée (détail dans Formules_Aire + onglets Aire_*):",
            "  Ai = ½(d0+d1)|Δx| si segment mouillé; triangle si partiellement mouillé; 0 si sec",
            "  A = Σ Ai ; P = Σ Pi ; R = A/P",
            "",
            f"Q = {Q_DESIGN} m³/s, n = {N_MANNING}",
            "Correspondance section → station: 1+000@0, 2+000@13.78, 3+000@23.66, 4+000@35.64,",
            "  5+000@45.84, 6+000@59.44, 7+000@71.97, 8+000@89.36 m",
        ],
        start=2,
    ):
        wsM.cell(i, 1, line)
    wsM.column_dimensions["A"].width = 100

    # Longitudinal sheet
    wsL = wb.create_sheet("Longitudinal")
    wsL["A1"] = "Profil longitudinal (données fournies) — S0 signé tel quel"
    for j, h in enumerate(["Point", "Z fond", "ΔL", "S0 réel", "Station cum."], start=1):
        wsL.cell(3, j, h)
    style_header(wsL, 3, 5)
    for i, r in enumerate(long_rows, start=4):
        for j, v in enumerate([r["point"], r["z"], r["dL"], r["S0"], r["station"]], start=1):
            cell = wsL.cell(i, j, v if v is not None else "—")
            cell.border = THIN
            if j == 4 and isinstance(v, (int, float)) and v <= 0:
                cell.fill = SKIP

    # Live Excel A/P formulas per section
    add_area_formula_sheets(wb, sections, results)

    wb.save(OUT_XLSX)
    print(f"Wrote {OUT_XLSX}")
    print(f"Clean CSV → {OUT_DIR}")


if __name__ == "__main__":
    main()
