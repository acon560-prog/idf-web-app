#!/usr/bin/env python3
"""
Build Excel: required retention volume upstream of controlling Ø900 culvert.

System (series):
  Ø1500 (in) → storage zone → Ø900 (control) → Ø1200 (downstream) → outlet

Method A: constant outlet capacity Qout = Qcap_900 (default 1.77 m³/s)
  V(t) = integral max(Qin - Qout, 0) dt   [trapezoidal]
  Vmax = max cumulative storage (storage cannot go negative)

Method B (optional): Qout = f(H) rating for Ø900, with simple level-pool
  using an assumed constant pond area (editable).
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HERE = Path(__file__).resolve().parent
OUT = HERE / "Volume_Retention_Ponceau_900.xlsx"

# Hydrograph (min, m³/s) — includes interpolated Qin=Qcap crossings (~9.37 and ~44.4 min)
HYDRO = [
    (0.0, 0.778),
    (5.0, 1.170),
    (9.37, 1.770),  # début stockage (Qin = Qcap Ø900)
    (10.0, 1.857),
    (15.0, 3.202),
    (20.0, 6.309),
    (22.5, 9.600),
    (27.5, 5.846),
    (32.5, 3.857),
    (37.5, 2.689),
    (42.5, 1.953),
    (44.4, 1.770),  # fin accumulation nette (Qin = Qcap)
    (47.5, 1.462),
    (52.5, 1.121),
    (57.5, 0.875),
]

QCAP_900 = 1.77
QCAP_1200 = 4.93
QPEAK_IN = 9.60

HEADER = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="0F5C5C")
YELLOW = PatternFill("solid", fgColor="FFF59D")
GREEN = PatternFill("solid", fgColor="D1FAE5")
ORANGE = PatternFill("solid", fgColor="FCE4D6")
BLUE = PatternFill("solid", fgColor="DBEAFE")
THIN = Border(
    left=Side(style="thin", color="CBD5E1"),
    right=Side(style="thin", color="CBD5E1"),
    top=Side(style="thin", color="CBD5E1"),
    bottom=Side(style="thin", color="CBD5E1"),
)


def style_header(ws, row: int, ncols: int) -> None:
    for c in range(1, ncols + 1):
        cell = ws.cell(row, c)
        cell.font = HEADER
        cell.fill = HEADER_FILL
        cell.border = THIN


def build() -> Path:
    wb = Workbook()

    # ---------- Parametres ----------
    ws = wb.active
    ws.title = "Parametres"
    ws["A1"] = "Volume de rétention — ponceau Ø900 contrôlant"
    ws["A1"].font = Font(bold=True, size=14, color="0F5C5C")
    ws.merge_cells("A1:F1")

    ws["A3"] = "Configuration (série)"
    ws["A3"].font = Font(bold=True)
    layout = [
        ("Ouvrage", "Rôle", "D (mm)", "Radier amont (m)", "Radier aval (m)", "Longueur (m)", "S0 (-)", "Q capacité donnée (m³/s)"),
        ("Ø1500", "Entrée / amont", 1500, 36.10, 35.05, 57.00, (36.10 - 35.05) / 57.00, QPEAK_IN),
        ("Ø900", "Contrôle sortie rétention", 900, 34.88, 34.45, 50.65, (34.88 - 34.45) / 50.65, QCAP_900),
        ("Ø1200", "Aval du Ø900", 1200, 33.60, 33.10, 31.30, (33.60 - 33.10) / 31.30, QCAP_1200),
    ]
    for j, h in enumerate(layout[0], start=1):
        ws.cell(4, j, h)
    style_header(ws, 4, 8)
    for i, row in enumerate(layout[1:], start=5):
        for j, v in enumerate(row, start=1):
            cell = ws.cell(i, j, v)
            cell.border = THIN
            if j in (4, 5, 6, 7, 8) and isinstance(v, float):
                cell.number_format = "0.000" if j != 7 else "0.00000"
        if row[0] == "Ø900":
            for j in range(1, 9):
                ws.cell(i, j).fill = ORANGE

    ws["A9"] = (
        "Chaîne: Ø1500 → zone de rétention → Ø900 (contrôle) → Ø1200 → exutoire. "
        "Le Ø1200 ne peut pas évacuer plus que ce que le Ø900 lui livre."
    )
    ws.merge_cells("A9:H10")
    ws["A9"].alignment = Alignment(wrap_text=True, vertical="top")

    ws["A12"] = "Entrées de calcul (jaune)"
    ws["A12"].font = Font(bold=True)
    ws["A13"] = "Qout_cap_900 (m³/s)"
    ws["B13"] = QCAP_900
    ws["B13"].fill = YELLOW
    ws["B13"].border = THIN
    ws["B13"].number_format = "0.00"
    ws["C13"] = "Débit sortant constant — Méthode A (capacité Ø900)"
    ws["A14"] = "Facteur_securite (-)"
    ws["B14"] = 1.20
    ws["B14"].fill = YELLOW
    ws["B14"].border = THIN
    ws["B14"].number_format = "0.00"
    ws["C14"] = "Marge sur Vmax (ex. 1.20 = +20%)"
    ws["A15"] = "Aire_bassin_m2"
    ws["B15"] = 2500
    ws["B15"].fill = YELLOW
    ws["B15"].border = THIN
    ws["B15"].number_format = "0"
    ws["C15"] = "Aire plan d'eau approximative pour estimer H = V/A (Méthode B / niveau)"

    ws["A17"] = "Résultats (formules — feuille Calcul_A)"
    ws["A17"].font = Font(bold=True)
    ws["A18"] = "Vmax (m³)"
    ws["B18"] = "=Calcul_A!B3"
    ws["B18"].fill = GREEN
    ws["B18"].number_format = "0"
    ws["A19"] = "V_dimensionnement = Vmax × facteur (m³)"
    ws["B19"] = "=B18*B14"
    ws["B19"].fill = GREEN
    ws["B19"].number_format = "0"
    ws["A20"] = "Hmax approx (m) = Vmax / Aire"
    ws["B20"] = "=IF(B15>0,B18/B15,0)"
    ws["B20"].fill = BLUE
    ws["B20"].number_format = "0.00"
    ws["C20"] = "Estimation grossière si l'aire de bassin est constante"

    ws["A22"] = "Notes"
    ws["A22"].font = Font(bold=True)
    notes = [
        "• Méthode A: Qout fixe = capacité Ø900. Valable comme estimation prudente / enveloppe basse de sortie.",
        "• Le stockage commence quand Qin dépasse Qout; Vmax est le maximum du volume cumulé (pas (Qp-Qout)×durée).",
        "• Méthode B (feuille Calcul_B): Qout augmente un peu avec la charge H (orifice plafonné), plus réaliste si disponible.",
        "• Les capacités 1.77 et 4.93 m³/s sont prises comme données; idéalement remplacer par une courbe Q=f(H) calibrée.",
        "• Vérifier que le radier amont Ø900 (34.88) est bien le fond de la zone de rétention étudiée.",
    ]
    for i, line in enumerate(notes, start=23):
        ws.cell(i, 1, line)
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=8)

    for col, w in zip("ABCDEFGH", [28, 26, 14, 16, 16, 14, 12, 26]):
        ws.column_dimensions[col].width = w

    # ---------- Hydrogramme ----------
    wh = wb.create_sheet("Hydrogramme")
    wh["A1"] = "Hydrogramme d'entrée (point Ø1500 / entrée rétention)"
    wh["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    headers = ["t (min)", "Qin (m³/s)", "Remarque"]
    for j, h in enumerate(headers, start=1):
        wh.cell(3, j, h)
    style_header(wh, 3, 3)
    for i, (t, q) in enumerate(HYDRO, start=4):
        wh.cell(i, 1, t).border = THIN
        wh.cell(i, 1).number_format = "0.0"
        wh.cell(i, 2, q).border = THIN
        wh.cell(i, 2).number_format = "0.000"
        note = ""
        if abs(q - 9.6) < 1e-6:
            note = "Pointe"
            wh.cell(i, 2).fill = ORANGE
        elif abs(q - QCAP_900) < 1e-9:
            note = "Qin = Qcap (croisement)"
            wh.cell(i, 2).fill = BLUE
        wh.cell(i, 3, note).border = THIN
    last_h = 3 + len(HYDRO)
    sum_row = last_h + 2
    wh.cell(sum_row, 1, "Qpointe (m³/s)")
    wh.cell(sum_row, 2, f"=MAX(B4:B{last_h})")
    wh.cell(sum_row, 2).fill = GREEN
    wh.cell(sum_row + 1, 1, "t pointe (min)")
    wh.cell(sum_row + 1, 2, 22.5)
    wh.cell(sum_row + 1, 2).number_format = "0.0"

    chart = LineChart()
    chart.title = "Hydrogramme Qin"
    chart.style = 10
    chart.y_axis.title = "Q (m³/s)"
    chart.x_axis.title = "t (min)"
    chart.add_data(Reference(wh, min_col=2, min_row=3, max_row=last_h), titles_from_data=True)
    chart.set_categories(Reference(wh, min_col=1, min_row=4, max_row=last_h))
    chart.shape = 4
    wh.add_chart(chart, "E3")
    for col, w in zip("ABC", [12, 14, 16]):
        wh.column_dimensions[col].width = w

    # ---------- Calcul_A : constant Qout ----------
    wa = wb.create_sheet("Calcul_A")
    wa["A1"] = "Méthode A — Qout constant = capacité Ø900"
    wa["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wa["A2"] = "Qout (m³/s)"
    wa["B2"] = "=Parametres!B13"
    wa["B2"].fill = YELLOW
    wa["B2"].number_format = "0.00"
    wa["A3"] = "Vmax (m³)"
    n = len(HYDRO)
    first = 8
    last = first + n - 1
    wa["B3"] = f"=MAX(H{first}:H{last})"
    wa["B3"].fill = GREEN
    wa["B3"].number_format = "0.0"
    wa["C3"] = "Maximum du volume stocké cumulé"

    cols = [
        "t (min)",
        "Qin (m³/s)",
        "Qout (m³/s)",
        "Qin−Qout (m³/s)",
        "Δt (s)",
        "ΔVin (m³)",
        "ΔVout (m³)",
        "V stocké (m³)",
        "Stockage?",
    ]
    for j, h in enumerate(cols, start=1):
        wa.cell(7, j, h)
    style_header(wa, 7, len(cols))

    for i, (t, q) in enumerate(HYDRO):
        r = first + i
        # t, Qin from hydro sheet
        wa.cell(r, 1, f"=Hydrogramme!A{4+i}").border = THIN
        wa.cell(r, 1).number_format = "0.0"
        wa.cell(r, 2, f"=Hydrogramme!B{4+i}").border = THIN
        wa.cell(r, 2).number_format = "0.000"
        wa.cell(r, 3, "=$B$2").border = THIN
        wa.cell(r, 3).number_format = "0.00"
        # Signed excess: positive = filling, negative = draining (V floored at 0)
        wa.cell(r, 4, f"=B{r}-C{r}").border = THIN
        wa.cell(r, 4).number_format = "0.000"
        if i == 0:
            wa.cell(r, 5, 0).border = THIN
            wa.cell(r, 6, 0).border = THIN
            wa.cell(r, 7, 0).border = THIN
            wa.cell(r, 8, 0).border = THIN
        else:
            prev = r - 1
            wa.cell(r, 5, f"=(A{r}-A{prev})*60").border = THIN
            wa.cell(r, 5).number_format = "0.0"
            wa.cell(r, 6, f"=0.5*(B{prev}+B{r})*E{r}").border = THIN
            wa.cell(r, 6).number_format = "0.0"
            # Outflow volume consistent with capacity when storing; when empty, limited by Qin
            wa.cell(r, 7, f"=F{r}-(H{r}-H{prev})").border = THIN
            wa.cell(r, 7).number_format = "0.0"
            # Level-pool with constant Qout: V = max(0, V + trap(Qin−Qout)·Δt)
            wa.cell(r, 8, f"=MAX(0,H{prev}+0.5*(D{prev}+D{r})*E{r})").border = THIN
            wa.cell(r, 8).number_format = "0.0"
        wa.cell(r, 8).fill = GREEN
        wa.cell(r, 9, f'=IF(H{r}>0.5,"oui","non")').border = THIN

    wa["A5"] = "t début stockage approx (min)"
    # first time Qin>Qout via match — leave note; formula hard in Excel without helper
    wa["B5"] = "voir courbe / entre 5 et 10 min (~9.4 min)"
    wa["A6"] = "t fin stockage approx (min)"
    wa["B6"] = "entre 42.5 et 47.5 min (~44.4 min)"

    # Chart storage
    ch2 = LineChart()
    ch2.title = "Volume stocké cumulé (Méthode A)"
    ch2.y_axis.title = "V (m³)"
    ch2.x_axis.title = "t (min)"
    ch2.add_data(Reference(wa, min_col=8, min_row=7, max_row=last), titles_from_data=True)
    ch2.set_categories(Reference(wa, min_col=1, min_row=first, max_row=last))
    wa.add_chart(ch2, "K7")

    ch3 = LineChart()
    ch3.title = "Qin vs Qout"
    ch3.y_axis.title = "Q (m³/s)"
    ch3.add_data(Reference(wa, min_col=2, min_row=7, max_row=last), titles_from_data=True)
    ch3.add_data(Reference(wa, min_col=3, min_row=7, max_row=last), titles_from_data=True)
    ch3.set_categories(Reference(wa, min_col=1, min_row=first, max_row=last))
    wa.add_chart(ch3, "K22")

    for col in range(1, 10):
        wa.column_dimensions[get_column_letter(col)].width = 14 if col > 1 else 12
    wa.column_dimensions["D"].width = 20
    wa.column_dimensions["H"].width = 18
    wa.column_dimensions["I"].width = 14

    # ---------- Calcul_B : Qout = f(H) simple orifice capped ----------
    wb2 = wb.create_sheet("Calcul_B")
    wb2["A1"] = "Méthode B — Qout = f(H) approximatif (orifice Ø900, plafonné)"
    wb2["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wb2["A2"] = (
        "Hypothèses: aire de bassin constante (Parametres!B15); "
        "H = V/Aire; Qorifice = Cd·A·√(2gH) avec A=πD²/4, Cd=0.62; "
        "Qout = MIN(Qorifice, Qcap) mais au moins le débit qui passe si H>0. "
        "Si H≈0 et Qin<Qcap, Qout=Qin (pas d'accumulation)."
    )
    wb2.merge_cells("A2:J4")
    wb2["A2"].alignment = Alignment(wrap_text=True, vertical="top")

    wb2["A5"] = "Cd (-)"
    wb2["B5"] = 0.62
    wb2["B5"].fill = YELLOW
    wb2["A6"] = "D_900 (m)"
    wb2["B6"] = 0.9
    wb2["B6"].fill = YELLOW
    wb2["A7"] = "Qcap (m³/s)"
    wb2["B7"] = "=Parametres!B13"
    wb2["B7"].fill = YELLOW
    wb2["A8"] = "Aire (m²)"
    wb2["B8"] = "=Parametres!B15"
    wb2["A9"] = "Vmax_B (m³)"
    wb2["B9"] = "=MAX(I14:I26)"
    wb2["B9"].fill = GREEN
    wb2["B9"].number_format = "0.0"
    wb2["A10"] = "Hmax_B (m)"
    wb2["B10"] = "=IF(B8>0,B9/B8,0)"
    wb2["B10"].fill = BLUE
    wb2["B10"].number_format = "0.00"

    cols_b = [
        "t (min)",
        "Qin",
        "H début (m)",
        "Qorifice",
        "Qout",
        "Δt (s)",
        "ΔV = (Qin−Qout)·Δt",
        "V fin (m³)",
        "V stocké (m³)",
        "H fin (m)",
    ]
    # Actually use simpler columns matching routing
    cols_b = [
        "t (min)",
        "Qin (m³/s)",
        "H (m)",
        "Qorifice (m³/s)",
        "Qout (m³/s)",
        "Δt (s)",
        "ΔV (m³)",
        "V (m³)",
        "V pour max",
    ]
    for j, h in enumerate(cols_b, start=1):
        wb2.cell(13, j, h)
    style_header(wb2, 13, len(cols_b))

    # Level-pool routing with formulas:
    # Row by row: H from previous V; Qout=min(max(orifice,0),Qcap) but if V~0 and Qin<Qcap then Qout=Qin
    # ΔV=(Qin_avg - Qout)*dt — use Qin at end of interval and Qout from H at start (explicit Euler) for Excel simplicity
    g = 9.81
    first_b = 14
    for i in range(n):
        r = first_b + i
        wb2.cell(r, 1, f"=Hydrogramme!A{4+i}").border = THIN
        wb2.cell(r, 1).number_format = "0.0"
        wb2.cell(r, 2, f"=Hydrogramme!B{4+i}").border = THIN
        wb2.cell(r, 2).number_format = "0.000"
        if i == 0:
            wb2.cell(r, 3, 0).border = THIN  # H
            wb2.cell(r, 4, 0).border = THIN  # Qorifice
            wb2.cell(r, 5, f"=MIN(B{r},$B$7)").border = THIN  # Qout
            wb2.cell(r, 6, 0).border = THIN
            wb2.cell(r, 7, 0).border = THIN
            wb2.cell(r, 8, 0).border = THIN
            wb2.cell(r, 9, 0).border = THIN
        else:
            prev = r - 1
            # H from previous V
            wb2.cell(r, 3, f"=IF($B$8>0,H{prev}/$B$8,0)").border = THIN
            wb2.cell(r, 3).number_format = "0.000"
            # Orifice: Cd * (pi D^2/4) * sqrt(2gH)
            wb2.cell(
                r,
                4,
                f'=IF(C{r}<=0,0,$B$5*(PI()*($B$6^2)/4)*SQRT(2*{g}*C{r}))',
            ).border = THIN
            wb2.cell(r, 4).number_format = "0.000"
            # Qout: if no storage and Qin < Qcap → Qin; else min(max(Qorifice, small), Qcap)
            # Better: Qout = MIN($B$7, IF(H{prev}<=1e-6, MIN(B{r},$B$7), MAX(D{r},0)))
            wb2.cell(
                r,
                5,
                f'=MIN($B$7,IF(H{prev}<=0.001,MIN(0.5*(B{prev}+B{r}),$B$7),D{r}))',
            ).border = THIN
            wb2.cell(r, 5).number_format = "0.000"
            wb2.cell(r, 6, f"=(A{r}-A{prev})*60").border = THIN
            wb2.cell(r, 6).number_format = "0.0"
            # ΔV = (Qin_avg - Qout)*dt
            wb2.cell(r, 7, f"=(0.5*(B{prev}+B{r})-E{r})*F{r}").border = THIN
            wb2.cell(r, 7).number_format = "0.0"
            wb2.cell(r, 8, f"=MAX(0,H{prev}+G{r})").border = THIN
            wb2.cell(r, 8).number_format = "0.0"
            wb2.cell(r, 9, f"=H{r}").border = THIN
            wb2.cell(r, 9).number_format = "0.0"
            # Fix: column H is V — I used H for V fin in formula referring to H{prev} as V
            # Rename carefully: col 8 = V, so previous V is H{prev} only if we put V in column H (=8)
            # I referenced H{prev} meaning column H = V. Good.
            # But col 3 formula uses H{prev}/Aire — that's V_prev/Aire. Good.
        for c in range(1, 10):
            if wb2.cell(r, c).value is not None:
                wb2.cell(r, c).border = THIN

    # Fix column 3/8 confusion on row 0: col8 is V named poorly in orifice H reference
    # On i>0, C{r} = H{prev}/Aire where H is column 8 (V). Excel column H = 8. Good.
    # Qout formula uses H{prev} as V — good.

    # Actually bug: first data row col9 =V for max uses column I =9 as copy of H. MAX(I14:I26) but V is in column H (8).
    wb2["B9"] = f"=MAX(H{first_b}:H{first_b+n-1})"

    # Fix orifice/Qout for i>0: column 3 should be water depth from V in column 8 of PREVIOUS row
    # Currently C{r}=H{prev}/$B$8 — H{prev} is previous row column H = V. Correct.

    for col in range(1, 10):
        wb2.column_dimensions[get_column_letter(col)].width = 14
    wb2.column_dimensions["A"].width = 12

    # Rewrite Calcul_B more carefully - the Euler scheme references are messy.
    # Simpler approach for B: precompute in Python a clean table and also put formulas
    # that are easier. Let me rebuild Calcul_B sheet cleanly.
    wb.remove(wb2)
    wb2 = wb.create_sheet("Calcul_B")
    wb2["A1"] = "Méthode B — routage simplifié Qout = f(H) (orifice Ø900 plafonné à Qcap)"
    wb2["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wb2["A2"] = (
        "H = V / Aire_bassin.  Qorifice = Cd·(πD²/4)·√(2gH).  "
        "Qout = MIN(Qcap, Qorifice) si V>0; si V≈0, Qout = MIN(Qin, Qcap).  "
        "ΔV = (Qin_moyenne − Qout)·Δt.  Ajuster Cd, Aire, Qcap (jaune)."
    )
    wb2.merge_cells("A2:I3")
    wb2["A2"].alignment = Alignment(wrap_text=True)

    wb2["A5"] = "Cd"
    wb2["B5"] = 0.62
    wb2["B5"].fill = YELLOW
    wb2["A6"] = "D (m)"
    wb2["B6"] = 0.90
    wb2["B6"].fill = YELLOW
    wb2["A7"] = "Qcap (m³/s)"
    wb2["B7"] = "=Parametres!B13"
    wb2["B7"].fill = YELLOW
    wb2["A8"] = "Aire (m²)"
    wb2["B8"] = "=Parametres!B15"
    wb2["B8"].fill = YELLOW
    r0 = 14
    wb2["A9"] = "Vmax_B (m³)"
    wb2["B9"] = f"=MAX(G{r0}:G{r0+n-1})"
    wb2["B9"].fill = GREEN
    wb2["B9"].number_format = "0.0"
    wb2["A10"] = "Hmax_B (m)"
    wb2["B10"] = "=IF(B8>0,B9/B8,0)"
    wb2["B10"].fill = BLUE
    wb2["B10"].number_format = "0.00"

    hdr_b = ["t (min)", "Qin", "H (m)", "Qorifice", "Qout", "Δt (s)", "V (m³)"]
    for j, h in enumerate(hdr_b, start=1):
        wb2.cell(13, j, h)
    style_header(wb2, 13, 7)

    # Pure formula Euler:
    for i in range(n):
        r = r0 + i
        wb2.cell(r, 1, f"=Hydrogramme!A{4+i}")
        wb2.cell(r, 2, f"=Hydrogramme!B{4+i}")
        if i == 0:
            wb2.cell(r, 3, 0)
            wb2.cell(r, 4, 0)
            wb2.cell(r, 5, f"=MIN(B{r},$B$7)")
            wb2.cell(r, 6, 0)
            wb2.cell(r, 7, 0)
        else:
            p = r - 1
            wb2.cell(r, 3, f"=IF($B$8>0,G{p}/$B$8,0)")  # H from previous V
            wb2.cell(r, 4, f"=IF(C{r}<=0,0,$B$5*(PI()*($B$6^2)/4)*SQRT(2*9.81*C{r}))")
            wb2.cell(r, 5, f"=IF(G{p}<=0.01,MIN(0.5*(B{p}+B{r}),$B$7),MIN($B$7,D{r}))")
            wb2.cell(r, 6, f"=(A{r}-A{p})*60")
            wb2.cell(r, 7, f"=MAX(0,G{p}+(0.5*(B{p}+B{r})-E{r})*F{r})")
        for c in range(1, 8):
            wb2.cell(r, c).border = THIN
            if c in (2, 3, 4, 5):
                wb2.cell(r, c).number_format = "0.000"
            if c in (6, 7):
                wb2.cell(r, c).number_format = "0.0"
        wb2.cell(r, 7).fill = GREEN

    for col, w in zip("ABCDEFG", [10, 10, 10, 12, 10, 10, 12]):
        wb2.column_dimensions[col].width = w

    # ---------- Methode ----------
    wm = wb.create_sheet("Methode")
    wm["A1"] = "Méthode — volume de rétention"
    wm["A1"].font = Font(bold=True, size=13)
    lines = [
        "",
        "1. Hydrogramme Qin(t) à l'entrée de la zone de rétention.",
        "2. Débit sortant contrôlé par le Ø900 (en série avant le Ø1200).",
        "3. Méthode A: Qout = constante = capacité Ø900.",
        "   Pendant chaque pas Δt:  ΔV = 0.5 * ((Qin−Qout)_i + (Qin−Qout)_{i+1}) * Δt",
        "   (excès signé: positif = remplissage, négatif = vidange).",
        "   V(t) = max(0, V(t−Δt) + ΔV).   Vmax = max V(t).",
        "4. Volume de dimensionnement ≈ Vmax × facteur de sécurité (Parametres).",
        "5. Méthode B: même bilan, mais Qout dépend de H = V/Aire (orifice plafonné).",
        "6. Le Ø1200 à 4.93 m³/s est aval: il ne augmente pas la capacité de sortie de la rétention.",
        "",
        "Limites: Q=f(H) réelle du ponceau (entrée/sortie, longueur, n) préférable à Qcap constant;",
        "aire de bassin rarement constante — remplacer par une courbe V(H) de site si disponible.",
    ]
    for i, line in enumerate(lines, start=2):
        wm.cell(i, 1, line)
    wm.column_dimensions["A"].width = 110

    wb.save(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path}")
