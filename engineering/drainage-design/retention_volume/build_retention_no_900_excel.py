#!/usr/bin/env python3
"""
Build Excel: retention WITHOUT Ø900 control.

New layout (client):
  Ø1500 (in) → larger retention pond → Ø1200 (outlet control) [+ optional berm overflow]

No Ø900 in series. Live formulas; yellow = inputs; green = results.
"""

from __future__ import annotations

import math
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HERE = Path(__file__).resolve().parent
OUT = HERE / "Volume_Retention_Sans_900.xlsx"

# Inflow hydrograph shape (same project storm; Qin = ratio × Qpointe)
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

# Ø1200 outlet (defaults — editable in Excel)
N_MANNING = 0.013
D_1200 = 1.20
L_1200 = 31.30
Z_US_1200 = 33.60
Z_DS_1200 = 33.10
S0_1200 = (Z_US_1200 - Z_DS_1200) / L_1200

# Pond floor / stage-storage start (old Ø900 invert was pond control floor)
Z_POND = 34.88

# Optional berm / overflow channel above a crest (not a Ø900 crown)
CREST_DEFAULT = 37.28  # former boss limit — editable
OV_B, OV_N, OV_Z, OV_S, OV_L = 2.0, 0.035, 2.0, 0.0085, 50.1


def q_full_manning(D: float, S0: float, n: float) -> float:
    A = math.pi * D**2 / 4.0
    R = D / 4.0
    return (1.0 / n) * A * (R ** (2.0 / 3.0)) * (S0**0.5)


Q_FULL_1200 = q_full_manning(D_1200, S0_1200, N_MANNING)

YELLOW = PatternFill("solid", fgColor="FFF59D")
GREEN = PatternFill("solid", fgColor="C8E6C9")
BLUE = PatternFill("solid", fgColor="BBDEFB")
ORANGE = PatternFill("solid", fgColor="FFE0B2")
HEADER_FILL = PatternFill("solid", fgColor="0F5C5C")
HEADER = Font(bold=True, color="FFFFFF")
THIN = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)


def style_header(ws, row: int, ncols: int) -> None:
    for c in range(1, ncols + 1):
        cell = ws.cell(row, c)
        cell.font = HEADER
        cell.fill = HEADER_FILL
        cell.border = THIN


def build() -> Path:
    wb = Workbook()

    # ========== Parametres ==========
    ws = wb.active
    ws.title = "Parametres"
    ws["A1"] = "Retention SANS Ø900 — control = Ø1200 (+ overflow optionnel)"
    ws["A1"].font = Font(bold=True, size=14, color="0F5C5C")
    ws.merge_cells("A1:F1")
    ws["A2"] = (
        "Hypotheses: le Ø900 est elimine; plus d'aire de retention. "
        "Entree = hydrogramme (Ø1500). Sortie = Ø1200. "
        "Option: fossé/berme au-dessus d'une cote crest. Cellules JAUNES = entrees."
    )
    ws.merge_cells("A2:F3")
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")

    ws["A5"] = "Schema"
    ws["A5"].font = Font(bold=True)
    ws["A6"] = "Ø1500 (in)  →  bassin de retention (agrandi)  →  Ø1200 (controle)  →  exutoire"
    ws["A7"] = "Ø900: SUPPRIME (plus de goulot amont du Ø1200)"
    ws["A7"].fill = ORANGE

    # --- Ø1200 geometry / Manning ---
    ws["A9"] = "Ø1200 — geometrie et Manning (jaune)"
    ws["A9"].font = Font(bold=True)
    rows1200 = [
        (10, "n Manning (-)", N_MANNING, "0.000"),
        (11, "D (m)", D_1200, "0.00"),
        (12, "L (m)", L_1200, "0.00"),
        (13, "Radier amont Zin (m)", Z_US_1200, "0.00"),
        (14, "Radier aval Zout (m)", Z_DS_1200, "0.00"),
    ]
    for r, lab, val, fmt in rows1200:
        ws.cell(r, 1, lab)
        c = ws.cell(r, 2, val)
        c.fill = YELLOW
        c.border = THIN
        c.number_format = fmt
    ws["A15"] = "S0 = (Zin-Zout)/L"
    ws["B15"] = "=(B13-B14)/B12"
    ws["B15"].fill = BLUE
    ws["B15"].number_format = "0.00000"
    ws["A16"] = "A = PI()*D^2/4 (m2)"
    ws["B16"] = "=PI()*B11^2/4"
    ws["B16"].fill = BLUE
    ws["B16"].number_format = "0.000"
    ws["A17"] = "R = D/4 (m)"
    ws["B17"] = "=B11/4"
    ws["B17"].fill = BLUE
    ws["B17"].number_format = "0.000"
    ws["A18"] = "Q_plein = (1/n)*A*R^(2/3)*SQRT(S0)"
    ws["B18"] = "=(1/B10)*B16*(B17^(2/3))*SQRT(B15)"
    ws["B18"].fill = GREEN
    ws["B18"].border = THIN
    ws["B18"].number_format = "0.000"
    ws["C18"] = "m3/s — formule live"
    ws["A19"] = "Fond bassin / NSE min (m)"
    ws["B19"] = Z_POND
    ws["B19"].fill = YELLOW
    ws["B19"].border = THIN
    ws["B19"].number_format = "0.00"
    ws["C19"] = "Depart Stage_Storage (ex-radier zone Ø900)"

    # Routing inputs
    ws["A21"] = "Entrees routage (jaune)"
    ws["A21"].font = Font(bold=True)
    ws["A22"] = "Qout_cap (m3/s) Methode A"
    ws["B22"] = "=B18"
    ws["B22"].fill = YELLOW
    ws["B22"].border = THIN
    ws["B22"].number_format = "0.000"
    ws["C22"] = "Par defaut = Q_plein Ø1200; ecraser si besoin"
    ws["A23"] = "Facteur_securite (-)"
    ws["B23"] = 1.20
    ws["B23"].fill = YELLOW
    ws["B23"].border = THIN
    ws["B23"].number_format = "0.00"
    ws["A24"] = "Aire_plan_eau_m2 (approx Methode B)"
    ws["B24"] = 4000
    ws["B24"].fill = YELLOW
    ws["B24"].border = THIN
    ws["B24"].number_format = "0"
    ws["C24"] = "Plus grande qu'avant (plus d'aire retention) — affiner avec le leve"

    # Overflow optional
    ws["A26"] = "Overflow optionnel — fosse/berme au-dessus d'un crest (jaune)"
    ws["A26"].font = Font(bold=True)
    ws["A27"] = "Crest (m)"
    ws["B27"] = CREST_DEFAULT
    ws["B27"].fill = YELLOW
    ws["B27"].border = THIN
    ws["B27"].number_format = "0.00"
    ws["C27"] = "Si WSE < crest → Q_overflow = 0"
    for r, lab, val, fmt in [
        (28, "b fond (m)", OV_B, "0.00"),
        (29, "n fosse (-)", OV_N, "0.000"),
        (30, "z (H:V)", OV_Z, "0.0"),
        (31, "S fosse (-)", OV_S, "0.0000"),
        (32, "L fosse (m)", OV_L, "0.0"),
    ]:
        ws.cell(r, 1, lab)
        c = ws.cell(r, 2, val)
        c.fill = YELLOW
        c.border = THIN
        c.number_format = fmt
    ws["C31"] = "Pente fosse (pas 0.085)"
    ws["A33"] = "Qout compose"
    ws["B33"] = "Q_1200(WSE) + Q_overflow(WSE)"
    ws["C33"] = "V = V_pond + V_ditch — Compose_1200 + Calcul_C"

    def wse_from_v(cell: str) -> str:
        return (
            f'=IF({cell}<=Stage_Storage!E11,Stage_Storage!A11,'
            f'IF({cell}>=Stage_Storage!E18,"Hors table — etendre leve",'
            f'INDEX(Stage_Storage!$A$11:$A$18,MATCH({cell},Stage_Storage!$E$11:$E$18,1))'
            f'+({cell}-INDEX(Stage_Storage!$E$11:$E$18,MATCH({cell},Stage_Storage!$E$11:$E$18,1)))'
            f'/(INDEX(Stage_Storage!$E$11:$E$18,MATCH({cell},Stage_Storage!$E$11:$E$18,1)+1)'
            f'-INDEX(Stage_Storage!$E$11:$E$18,MATCH({cell},Stage_Storage!$E$11:$E$18,1)))'
            f'*(INDEX(Stage_Storage!$A$11:$A$18,MATCH({cell},Stage_Storage!$E$11:$E$18,1)+1)'
            f'-INDEX(Stage_Storage!$A$11:$A$18,MATCH({cell},Stage_Storage!$E$11:$E$18,1)))))'
        )

    # Results A
    ws["A35"] = "Resultats Methode A — Qout constant Ø1200 (Calcul_A)"
    ws["A35"].font = Font(bold=True)
    ws["A36"] = "Vmax_A (m3)"
    ws["B36"] = "=Calcul_A!B3"
    ws["B36"].fill = GREEN
    ws["B36"].number_format = "0"
    ws["A37"] = "V_dim_A = Vmax_A * facteur"
    ws["B37"] = "=B36*B23"
    ws["B37"].fill = GREEN
    ws["B37"].number_format = "0"
    ws["A38"] = "WSEmax_A (m) depuis leve"
    ws["B38"] = wse_from_v("B36")
    ws["B38"].fill = GREEN
    ws["B38"].number_format = "0.00"
    ws["A39"] = "HW_A = WSEmax_A - Zin_1200 (m)"
    ws["B39"] = '=IF(ISNUMBER(B38),B38-B13,"")'
    ws["B39"].fill = GREEN
    ws["B39"].number_format = "0.00"

    # Results B
    ws["A41"] = "Resultats Methode B — Q=f(H) pipe Ø1200 (Calcul_B)"
    ws["A41"].font = Font(bold=True)
    ws["A42"] = "Vmax_B (m3)"
    ws["B42"] = "=Calcul_B!B7"
    ws["B42"].fill = GREEN
    ws["B42"].number_format = "0"
    ws["A43"] = "V_dim_B"
    ws["B43"] = "=B42*B23"
    ws["B43"].fill = GREEN
    ws["B43"].number_format = "0"
    ws["A44"] = "WSEmax_B (m) depuis leve"
    ws["B44"] = wse_from_v("B42")
    ws["B44"].fill = GREEN
    ws["B44"].number_format = "0.00"
    ws["A45"] = "Hmax_B approx = Vmax_B / Aire (m)"
    ws["B45"] = "=IF(B24>0,B42/B24,0)"
    ws["B45"].fill = BLUE
    ws["B45"].number_format = "0.00"

    # Results C
    ws["A47"] = "Resultats Methode C — Ø1200 + overflow (Calcul_C)"
    ws["A47"].font = Font(bold=True)
    ws["A48"] = "Vmax_C (m3) = max(V_pond+V_ditch)"
    ws["B48"] = "=Calcul_C!B7"
    ws["B48"].fill = GREEN
    ws["B48"].number_format = "0"
    ws["A49"] = "V_dim_C"
    ws["B49"] = "=B48*B23"
    ws["B49"].fill = GREEN
    ws["B49"].number_format = "0"
    ws["A50"] = "WSEmax_C (m) routage"
    ws["B50"] = "=Calcul_C!B8"
    ws["B50"].fill = GREEN
    ws["B50"].number_format = "0.00"
    ws["A51"] = "HW_C = WSEmax_C - Zin_1200 (m)"
    ws["B51"] = '=IF(ISNUMBER(B50),B50-B13,"")'
    ws["B51"].fill = GREEN
    ws["B51"].number_format = "0.00"
    ws["C51"] = "Overflow actif si WSEmax_C > crest (B27)"

    ws["A53"] = "Notes dynamiques"
    ws["A53"].font = Font(bold=True)
    notes = [
        "• Sans Ø900: le goulot est le Ø1200 (Q_plein ~4.9 m3/s vs ~1.7 avant) → moins de stockage force, plus de pointe aval.",
        "• Plus d'aire de bassin: augmenter les surfaces jaunes sur Stage_Storage (et/ou Aire B24).",
        "• Methode A: 1re estimation. B: rating FHWA pipe. C: pipe + fosse si WSE depasse le crest.",
        "• Verifier la capacite/vitesse aval avec Qout(t) de Calcul_B ou C (pointe plus haute qu'avec Ø900).",
    ]
    for i, line in enumerate(notes, start=54):
        ws.cell(i, 1, line)
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=6)

    for col, w in zip("ABCDEF", [42, 14, 55, 14, 14, 14]):
        ws.column_dimensions[col].width = w

    # ========== Hydrogramme ==========
    wh = wb.create_sheet("Hydrogramme")
    wh["A1"] = "Hydrogramme d'entree (Ø1500 / entree retention) — LIVE"
    wh["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wh["A2"] = "Qin(t) = ratio(t) × Qpointe. Changez B4 (jaune) → Calcul_A/B/C se mettent a jour."
    wh.merge_cells("A2:E2")
    wh["A4"] = "Qpointe (m3/s)"
    wh["B4"] = QPEAK_REF
    wh["B4"].fill = YELLOW
    wh["B4"].border = THIN
    wh["B4"].number_format = "0.000"
    hdr = ["t (min)", "ratio", "Qin (m3/s)"]
    for j, h in enumerate(hdr, 1):
        wh.cell(6, j, h)
    style_header(wh, 6, 3)
    for i, (t, ratio) in enumerate(HYDRO_SHAPE):
        r = 7 + i
        wh.cell(r, 1, t).number_format = "0.0"
        wh.cell(r, 2, round(ratio, 6)).number_format = "0.000"
        wh.cell(r, 3, f"=B{r}*$B$4").number_format = "0.000"
        for c in range(1, 4):
            wh.cell(r, c).border = THIN
        if abs(t - 22.5) < 1e-9:
            wh.cell(r, 3).fill = ORANGE
    n = len(HYDRO_SHAPE)
    last_h = 6 + n
    wh["A22"] = "Qin max"
    wh["B22"] = f"=MAX(C7:C{last_h})"
    wh["B22"].fill = GREEN

    ch_h = LineChart()
    ch_h.title = "Hydrogramme Qin(t)"
    ch_h.y_axis.title = "Qin (m3/s)"
    ch_h.x_axis.title = "t (min)"
    ch_h.add_data(Reference(wh, min_col=3, min_row=6, max_row=last_h), titles_from_data=True)
    ch_h.set_categories(Reference(wh, min_col=1, min_row=7, max_row=last_h))
    wh.add_chart(ch_h, "E4")
    for col, w in zip("ABC", [12, 12, 14]):
        wh.column_dimensions[col].width = w

    # ========== Calcul_A ==========
    wa = wb.create_sheet("Calcul_A")
    wa["A1"] = "Methode A — Qout constant = Qout_cap (Ø1200)"
    wa["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wa["A2"] = "Qout"
    wa["B2"] = "=Parametres!B22"
    wa["B2"].fill = YELLOW
    wa["B2"].number_format = "0.000"
    wa["A3"] = "Vmax_A (m3)"
    wa["B3"] = f"=MAX(E8:E{7+n})"
    wa["B3"].fill = GREEN
    wa["B3"].number_format = "0.0"

    for j, h in enumerate(["t (min)", "Qin", "Qout", "dt (s)", "V (m3)"], 1):
        wa.cell(7, j, h)
    style_header(wa, 7, 5)
    for i in range(n):
        r = 8 + i
        wa.cell(r, 1, f"=Hydrogramme!A{7+i}")
        wa.cell(r, 2, f"=Hydrogramme!C{7+i}")
        wa.cell(r, 3, "=$B$2")
        if i == 0:
            wa.cell(r, 4, 0)
            wa.cell(r, 5, 0)
        else:
            p = r - 1
            wa.cell(r, 4, f"=(A{r}-A{p})*60")
            wa.cell(r, 5, f"=MAX(0,E{p}+(0.5*(B{p}+B{r})-C{r})*D{r})")
        for c in range(1, 6):
            wa.cell(r, c).border = THIN
            wa.cell(r, c).number_format = "0.000" if c < 4 else "0.0"
        wa.cell(r, 5).fill = GREEN

    ch_a = LineChart()
    ch_a.title = "Methode A — V(t) et Qin"
    ch_a.y_axis.title = "V (m3) / Qin"
    ch_a.add_data(Reference(wa, min_col=5, min_row=7, max_row=7 + n), titles_from_data=True)
    ch_a.add_data(Reference(wa, min_col=2, min_row=7, max_row=7 + n), titles_from_data=True)
    ch_a.set_categories(Reference(wa, min_col=1, min_row=8, max_row=7 + n))
    wa.add_chart(ch_a, "G3")

    # ========== Courbe_QH_1200 (FHWA simplified live) ==========
    wq = wb.create_sheet("Courbe_QH_1200")
    wq["A1"] = "Courbe Q=f(H) Ø1200 — FHWA HDS-5 (inlet + outlet) LIVE"
    wq["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wq["A2"] = "Parametres lies a Parametres!B10–B14. Q_gouvernant = MIN(Qinlet, Qoutlet)."
    wq.merge_cells("A2:F2")

    wq["A4"] = "n"
    wq["B4"] = "=Parametres!B10"
    wq["A5"] = "D (m)"
    wq["B5"] = "=Parametres!B11"
    wq["A6"] = "L (m)"
    wq["B6"] = "=Parametres!B12"
    wq["A7"] = "Zin (m)"
    wq["B7"] = "=Parametres!B13"
    wq["A8"] = "Zout (m)"
    wq["B8"] = "=Parametres!B14"
    wq["A9"] = "S0"
    wq["B9"] = "=Parametres!B15"
    wq["A10"] = "TW au-dessus Zout (m)"
    wq["B10"] = 0.0
    wq["B10"].fill = YELLOW
    wq["B10"].border = THIN
    wq["A11"] = "Entree"
    wq["B11"] = "square_edge"
    wq["B11"].fill = YELLOW
    wq["B11"].border = THIN
    wq["C11"] = "square_edge | beveled | groove_headwall"

    # coeff table
    wq["E4"] = "entree"
    wq["F4"] = "K"
    wq["G4"] = "M"
    wq["H4"] = "c"
    wq["I4"] = "Y"
    wq["J4"] = "Ke"
    style_header(wq, 4, 6)
    # shift header to E
    for j, h in enumerate(["entree", "K", "M", "c", "Y", "Ke"], start=5):
        wq.cell(4, j, h)
        wq.cell(4, j).font = HEADER
        wq.cell(4, j).fill = HEADER_FILL
    coeffs = [
        ("square_edge", 0.0098, 2.0, 0.0398, 0.67, 0.5),
        ("beveled", 0.0018, 2.5, 0.0300, 0.74, 0.2),
        ("groove_headwall", 0.0078, 2.0, 0.0292, 0.74, 0.2),
    ]
    for i, rowv in enumerate(coeffs):
        for j, v in enumerate(rowv):
            wq.cell(5 + i, 5 + j, v).border = THIN

    wq["A13"] = "K"
    wq["B13"] = '=IFERROR(VLOOKUP(B11,$E$5:$J$7,2,FALSE),0.0098)'
    wq["A14"] = "M"
    wq["B14"] = '=IFERROR(VLOOKUP(B11,$E$5:$J$7,3,FALSE),2)'
    wq["A15"] = "c"
    wq["B15"] = '=IFERROR(VLOOKUP(B11,$E$5:$J$7,4,FALSE),0.0398)'
    wq["A16"] = "Y"
    wq["B16"] = '=IFERROR(VLOOKUP(B11,$E$5:$J$7,5,FALSE),0.67)'
    wq["A17"] = "Ke"
    wq["B17"] = '=IFERROR(VLOOKUP(B11,$E$5:$J$7,6,FALSE),0.5)'

    D, L, S0, TW = "$B$5", "$B$6", "$B$9", "$B$10"
    nref, K, M, c, Y, Ke = "$B$4", "$B$13", "$B$14", "$B$15", "$B$16", "$B$17"
    Zin = "$B$7"
    KU, G = "1.811", "9.81"

    def f_qinlet(hw: str) -> str:
        A = f"(PI()*({D}/2)^2)"
        qun = f"{KU}*{A}*SQRT({D})*IF({K}*{D}<=0,0,({hw}/({K}*{D}))^(1/{M}))"
        qun_sw = f"{KU}*{A}*SQRT({D})*IF({K}*{D}<=0,0,((1.2*{D})/({K}*{D}))^(1/{M}))"
        qsub = f"{KU}*{A}*SQRT({D})*SQRT(MAX(0,({hw}/{D}-{Y})/{c}))"
        return f"IF({hw}<=0,0,IF({hw}<=1.2*{D},{qun},MAX({qun_sw},{qsub})))"

    def f_qoutlet(hw: str) -> str:
        ratio = f"MIN(0.999,MAX(1E-6,{hw}/{D}))"
        theta = f"2*ACOS(1-2*({ratio}))"
        aseg = f"(({D}/2)^2/2)*(({theta})-SIN({theta}))"
        pwet = f"({D}/2)*({theta})"
        rh_p = f"IF(({pwet})<=0,0,({aseg})/({pwet}))"
        q_part = (
            f"IF({nref}<=0,0,(1/{nref})*({aseg})"
            f"*IF(({rh_p})<=0,0,({rh_p})^(2/3))*SQRT({S0}))"
        )
        a_full = f"(PI()*({D}/2)^2)"
        rh_f = f"{D}/4"
        hloss = f"{hw}-{TW}+{S0}*{L}"
        denom = f"(1+{Ke})/(2*{G})+({nref}^2)*{L}/(({rh_f})^(4/3))"
        q_full = f"IF(({hloss})<=0,0,{a_full}*SQRT(({hloss})/({denom})))"
        return f"IF({hw}<{D},{q_part},{q_full})"

    for j, h in enumerate(["HW (m)", "WSE (m)", "Qinlet", "Qoutlet", "Q gouvernant"], 1):
        wq.cell(19, j, h)
    style_header(wq, 19, 5)

    first_q, n_hw = 20, 61
    for i in range(n_hw):
        r = first_q + i
        hw_val = round(i * 0.05, 2)
        wq.cell(r, 1, hw_val).number_format = "0.00"
        hw = f"A{r}"
        wq.cell(r, 2, f"={Zin}+{hw}").number_format = "0.00"
        wq.cell(r, 3, f"={f_qinlet(hw)}").number_format = "0.000"
        wq.cell(r, 4, f"={f_qoutlet(hw)}").number_format = "0.000"
        wq.cell(r, 5, f"=MIN(C{r},D{r})").number_format = "0.000"
        wq.cell(r, 5).fill = GREEN
        for c in range(1, 6):
            wq.cell(r, c).border = THIN
    last_q = first_q + n_hw - 1

    ch_q = LineChart()
    ch_q.title = "Q gouvernant vs HW (Ø1200)"
    ch_q.y_axis.title = "Q (m3/s)"
    ch_q.x_axis.title = "HW (m)"
    ch_q.add_data(Reference(wq, min_col=5, min_row=19, max_row=last_q), titles_from_data=True)
    ch_q.add_data(Reference(wq, min_col=3, min_row=19, max_row=last_q), titles_from_data=True)
    ch_q.add_data(Reference(wq, min_col=4, min_row=19, max_row=last_q), titles_from_data=True)
    ch_q.set_categories(Reference(wq, min_col=1, min_row=first_q, max_row=last_q))
    wq.add_chart(ch_q, "L4")

    # ========== Calcul_B ==========
    wb2 = wb.create_sheet("Calcul_B")
    wb2["A1"] = "Methode B — routage Qout = f(H) depuis Courbe_QH_1200"
    wb2["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wb2["A2"] = "H = V / Aire_plan_eau. Qout interpole sur Q gouvernant."
    wb2.merge_cells("A2:G2")
    wb2["A4"] = "Aire (m2)"
    wb2["B4"] = "=Parametres!B24"
    wb2["B4"].fill = YELLOW
    wb2["A5"] = "Q_plein ref"
    wb2["B5"] = "=Parametres!B22"
    wb2["B5"].fill = YELLOW

    hw_rng = f"Courbe_QH_1200!$A${first_q}:$A${last_q}"
    q_rng = f"Courbe_QH_1200!$E${first_q}:$E${last_q}"

    def q_from_h(h_cell: str) -> str:
        m = f"MATCH({h_cell},{hw_rng},1)"
        return (
            f'IF({h_cell}<=0,0,'
            f'IF({h_cell}>=INDEX({hw_rng},ROWS({hw_rng})),INDEX({q_rng},ROWS({q_rng})),'
            f'INDEX({q_rng},{m})+'
            f'({h_cell}-INDEX({hw_rng},{m}))/'
            f'(INDEX({hw_rng},{m}+1)-INDEX({hw_rng},{m}))*'
            f'(INDEX({q_rng},{m}+1)-INDEX({q_rng},{m}))))'
        )

    r0 = 10
    wb2["A7"] = "Vmax_B (m3)"
    wb2["B7"] = f"=MAX(G{r0}:G{r0+n-1})"
    wb2["B7"].fill = GREEN
    wb2["B7"].number_format = "0.0"
    wb2["A8"] = "Hmax_B (m)"
    wb2["B8"] = "=IF(B4>0,B7/B4,0)"
    wb2["B8"].fill = BLUE
    wb2["B8"].number_format = "0.00"

    for j, h in enumerate(["t (min)", "Qin", "H (m)", "Q_courbe", "Qout", "dt (s)", "V (m3)"], 1):
        wb2.cell(9, j, h)
    style_header(wb2, 9, 7)

    for i in range(n):
        r = r0 + i
        wb2.cell(r, 1, f"=Hydrogramme!A{7+i}")
        wb2.cell(r, 2, f"=Hydrogramme!C{7+i}")
        if i == 0:
            wb2.cell(r, 3, 0)
            wb2.cell(r, 4, 0)
            wb2.cell(r, 5, f"=MIN(B{r},$B$5)")
            wb2.cell(r, 6, 0)
            wb2.cell(r, 7, 0)
        else:
            p = r - 1
            wb2.cell(r, 3, f"=IF($B$4>0,G{p}/$B$4,0)")
            wb2.cell(r, 4, f"={q_from_h(f'C{r}')}")
            wb2.cell(r, 5, f"=IF(G{p}<=0.01,MIN(0.5*(B{p}+B{r}),$B$5),D{r})")
            wb2.cell(r, 6, f"=(A{r}-A{p})*60")
            wb2.cell(r, 7, f"=MAX(0,G{p}+(0.5*(B{p}+B{r})-E{r})*F{r})")
        for c in range(1, 8):
            wb2.cell(r, c).border = THIN
            wb2.cell(r, c).number_format = "0.000" if c < 6 else "0.0"
        wb2.cell(r, 7).fill = GREEN

    ch_b = LineChart()
    ch_b.title = "Methode B — V(t)"
    ch_b.add_data(Reference(wb2, min_col=7, min_row=9, max_row=r0 + n - 1), titles_from_data=True)
    ch_b.add_data(Reference(wb2, min_col=2, min_row=9, max_row=r0 + n - 1), titles_from_data=True)
    ch_b.set_categories(Reference(wb2, min_col=1, min_row=r0, max_row=r0 + n - 1))
    wb2.add_chart(ch_b, "I3")

    # ========== Stage_Storage ==========
    wss = wb.create_sheet("Stage_Storage")
    wss["A1"] = "Stage–storage du leve (bassin AGRANDI sans Ø900) — editer surfaces jaunes"
    wss["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wss["A2"] = (
        "V_pas = 0.5*(A_bas+A_haut)*dWSE. Remplacez les aires par votre nouveau leve "
        "(plus d'aire attendue sans emprise Ø900). 37.28 m = ancienne limite patron."
    )
    wss.merge_cells("A2:F3")
    wss["A2"].alignment = Alignment(wrap_text=True)

    for j, h in enumerate(
        ["WSE (m)", "Surface A (m2) EDIT", "dWSE (m)", "V_pas (m3)", "V_cumul (m3)", "Role"], 1
    ):
        wss.cell(10, j, h)
    style_header(wss, 10, 6)

    # Slightly larger placeholder areas than old Ø900 pond (illustrative)
    stages = [
        (Z_POND, 0, "Fond bassin"),
        (35.50, 120, "Placeholder — remplacer"),
        (36.00, 280, "Placeholder — remplacer"),
        (36.50, 480, "Placeholder — remplacer"),
        (37.00, 720, "Placeholder — remplacer"),
        (37.28, 850, "Limite patron (ex) — a recalibrer"),
        (37.50, 1100, "Placeholder — remplacer"),
        (39.50, 2800, "Placeholder haut — remplacer"),
    ]
    for i, (wse, area, role) in enumerate(stages):
        r = 11 + i
        wss.cell(r, 1, wse).number_format = "0.00"
        wss.cell(r, 2, area).fill = YELLOW
        wss.cell(r, 2).number_format = "0"
        if i == 0:
            wss.cell(r, 3, 0)
            wss.cell(r, 4, 0)
            wss.cell(r, 5, 0)
        else:
            prev = r - 1
            wss.cell(r, 3, f"=A{r}-A{prev}").number_format = "0.00"
            wss.cell(r, 4, f"=0.5*(B{prev}+B{r})*C{r}").number_format = "0.0"
            wss.cell(r, 5, f"=E{prev}+D{r}").number_format = "0.0"
            wss.cell(r, 5).fill = GREEN
        wss.cell(r, 6, role)
        for c in range(1, 7):
            wss.cell(r, c).border = THIN
        if abs(wse - 37.28) < 1e-9:
            for c in range(1, 7):
                if c != 2:
                    wss.cell(r, c).fill = ORANGE

    wss["A21"] = "Vmax_A / WSEmax_A"
    wss["B21"] = "=Parametres!B36"
    wss["C21"] = "=Parametres!B38"
    wss["A22"] = "Vmax_B / WSEmax_B"
    wss["B22"] = "=Parametres!B42"
    wss["C22"] = "=Parametres!B44"
    wss["A23"] = "V @ 37.28 m"
    wss["B23"] = "=E16"
    wss["B23"].fill = BLUE

    ch_s = LineChart()
    ch_s.title = "V cumul vs WSE (leve)"
    ch_s.y_axis.title = "V (m3)"
    ch_s.x_axis.title = "WSE (m)"
    ch_s.add_data(Reference(wss, min_col=5, min_row=10, max_row=18), titles_from_data=True)
    ch_s.set_categories(Reference(wss, min_col=1, min_row=11, max_row=18))
    wss.add_chart(ch_s, "H6")
    for col, w in zip("ABCDEF", [12, 18, 12, 12, 14, 40]):
        wss.column_dimensions[col].width = w

    # ========== Compose_1200 ==========
    wc = wb.create_sheet("Compose_1200")
    wc["A1"] = "Methode C — Q_1200 + Q_overflow; V_pond + V_ditch"
    wc["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wc["A2"] = "Lie a Parametres (crest, b, n, z, S, L). Overflow si WSE >= crest."
    wc.merge_cells("A2:K2")

    for r, lab, ref in [
        (4, "Crest", "=Parametres!B27"),
        (5, "b", "=Parametres!B28"),
        (6, "n", "=Parametres!B29"),
        (7, "z", "=Parametres!B30"),
        (8, "S", "=Parametres!B31"),
        (9, "L", "=Parametres!B32"),
        (10, "Zin", "=Parametres!B13"),
    ]:
        wc.cell(r, 1, lab)
        cell = wc.cell(r, 2, ref)
        cell.fill = YELLOW
        cell.border = THIN

    Crest, b_ref, n_ov, z_ref, S_ov, L_ov, Zin_c = (
        "$B$4",
        "$B$5",
        "$B$6",
        "$B$7",
        "$B$8",
        "$B$9",
        "$B$10",
    )
    ss_wse = "Stage_Storage!$A$11:$A$18"
    ss_v = "Stage_Storage!$E$11:$E$18"
    hw_rng2 = f"Courbe_QH_1200!$A${first_q}:$A${last_q}"
    q_rng2 = f"Courbe_QH_1200!$E${first_q}:$E${last_q}"

    def v_pond(wse: str) -> str:
        m = f"MATCH({wse},{ss_wse},1)"
        return (
            f'IF({wse}<=INDEX({ss_wse},1),INDEX({ss_v},1),'
            f'IF({wse}>=INDEX({ss_wse},ROWS({ss_wse})),INDEX({ss_v},ROWS({ss_v})),'
            f'INDEX({ss_v},{m})+({wse}-INDEX({ss_wse},{m}))/'
            f'(INDEX({ss_wse},{m}+1)-INDEX({ss_wse},{m}))*'
            f'(INDEX({ss_v},{m}+1)-INDEX({ss_v},{m}))))'
        )

    def q1200_hw(hw: str) -> str:
        m = f"MATCH({hw},{hw_rng2},1)"
        return (
            f'IF({hw}<=0,0,'
            f'IF({hw}>=INDEX({hw_rng2},ROWS({hw_rng2})),INDEX({q_rng2},ROWS({q_rng2})),'
            f'INDEX({q_rng2},{m})+({hw}-INDEX({hw_rng2},{m}))/'
            f'(INDEX({hw_rng2},{m}+1)-INDEX({hw_rng2},{m}))*'
            f'(INDEX({q_rng2},{m}+1)-INDEX({q_rng2},{m}))))'
        )

    for j, h in enumerate(
        [
            "WSE",
            "HW",
            "y_ov",
            "A_ditch",
            "V_ditch",
            "V_pond",
            "V_total",
            "Q_1200",
            "Q_overflow",
            "Qout",
        ],
        1,
    ):
        wc.cell(12, j, h)
    style_header(wc, 12, 10)

    wse0, wse1, step = Z_POND, 39.50, 0.10
    n_comp = int(round((wse1 - wse0) / step)) + 1
    c0 = 13
    for i in range(n_comp):
        r = c0 + i
        wse_val = round(wse0 + i * step, 2)
        wc.cell(r, 1, wse_val).number_format = "0.00"
        wse = f"A{r}"
        wc.cell(r, 2, f"={wse}-{Zin_c}").number_format = "0.00"
        wc.cell(r, 3, f"=MAX(0,{wse}-{Crest})").number_format = "0.00"
        y = f"C{r}"
        wc.cell(r, 4, f"=IF({y}<=0,0,({b_ref}+{z_ref}*{y})*{y})").number_format = "0.000"
        A = f"D{r}"
        wc.cell(r, 5, f"={A}*{L_ov}").number_format = "0.0"
        wc.cell(r, 6, f"={v_pond(wse)}").number_format = "0.0"
        wc.cell(r, 7, f"=E{r}+F{r}").number_format = "0.0"
        wc.cell(r, 7).fill = GREEN
        hw = f"B{r}"
        wc.cell(r, 8, f"={q1200_hw(hw)}").number_format = "0.000"
        wc.cell(
            r,
            9,
            f"=IF({y}<=0,0,IF({n_ov}<=0,0,(1/{n_ov})*{A}*"
            f"IF(({b_ref}+2*{y}*SQRT(1+{z_ref}^2))<=0,0,"
            f"(({A}/({b_ref}+2*{y}*SQRT(1+{z_ref}^2)))^(2/3)))*SQRT({S_ov})))",
        ).number_format = "0.000"
        wc.cell(r, 10, f"=H{r}+I{r}").number_format = "0.000"
        wc.cell(r, 10).fill = GREEN
        for c in range(1, 11):
            wc.cell(r, c).border = THIN
    c_last = c0 + n_comp - 1

    ch_c = LineChart()
    ch_c.title = "Qout compose vs WSE"
    ch_c.y_axis.title = "Q (m3/s)"
    ch_c.x_axis.title = "WSE (m)"
    ch_c.add_data(Reference(wc, min_col=10, min_row=12, max_row=c_last), titles_from_data=True)
    ch_c.add_data(Reference(wc, min_col=8, min_row=12, max_row=c_last), titles_from_data=True)
    ch_c.add_data(Reference(wc, min_col=9, min_row=12, max_row=c_last), titles_from_data=True)
    ch_c.set_categories(Reference(wc, min_col=1, min_row=c0, max_row=c_last))
    wc.add_chart(ch_c, "L4")

    # ========== Calcul_C ==========
    wc2 = wb.create_sheet("Calcul_C")
    wc2["A1"] = "Methode C — routage V_total + Qout compose (sans Ø900)"
    wc2["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wc2["A2"] = "WSE depuis V_total (Compose_1200); Qout = Q_1200 + Q_overflow."
    wc2.merge_cells("A2:G2")
    wc2["A4"] = "Q_plein ref"
    wc2["B4"] = "=Parametres!B22"
    wc2["B4"].fill = YELLOW
    wc2["A5"] = "Crest"
    wc2["B5"] = "=Parametres!B27"
    wc2["B5"].fill = YELLOW

    vtot = f"Compose_1200!$G${c0}:$G${c_last}"
    wser = f"Compose_1200!$A${c0}:$A${c_last}"
    qoutr = f"Compose_1200!$J${c0}:$J${c_last}"

    def wse_from_vtot(v: str) -> str:
        m = f"MATCH({v},{vtot},1)"
        return (
            f'IF({v}<=INDEX({vtot},1),INDEX({wser},1),'
            f'IF({v}>=INDEX({vtot},ROWS({vtot})),INDEX({wser},ROWS({wser})),'
            f'INDEX({wser},{m})+({v}-INDEX({vtot},{m}))/'
            f'(INDEX({vtot},{m}+1)-INDEX({vtot},{m}))*'
            f'(INDEX({wser},{m}+1)-INDEX({wser},{m}))))'
        )

    def q_from_wse(w: str) -> str:
        m = f"MATCH({w},{wser},1)"
        return (
            f'IF({w}<=INDEX({wser},1),INDEX({qoutr},1),'
            f'IF({w}>=INDEX({wser},ROWS({wser})),INDEX({qoutr},ROWS({qoutr})),'
            f'INDEX({qoutr},{m})+({w}-INDEX({wser},{m}))/'
            f'(INDEX({wser},{m}+1)-INDEX({wser},{m}))*'
            f'(INDEX({qoutr},{m}+1)-INDEX({qoutr},{m}))))'
        )

    r0c = 10
    wc2["A7"] = "Vmax_C"
    wc2["B7"] = f"=MAX(F{r0c}:F{r0c+n-1})"
    wc2["B7"].fill = GREEN
    wc2["B7"].number_format = "0.0"
    wc2["A8"] = "WSEmax_C"
    wc2["B8"] = f"=MAX(C{r0c}:C{r0c+n-1})"
    wc2["B8"].fill = GREEN
    wc2["B8"].number_format = "0.00"
    wc2["A9"] = "Overflow?"
    wc2["B9"] = '=IF(B8>$B$5,"oui","non")'

    for j, h in enumerate(["t", "Qin", "WSE", "Qout", "dt", "V", "Overflow?"], 1):
        wc2.cell(9, j, h)
    style_header(wc2, 9, 7)

    for i in range(n):
        r = r0c + i
        wc2.cell(r, 1, f"=Hydrogramme!A{7+i}")
        wc2.cell(r, 2, f"=Hydrogramme!C{7+i}")
        if i == 0:
            wc2.cell(r, 3, f"=Parametres!B19")
            wc2.cell(r, 4, f"=MIN(B{r},$B$4)")
            wc2.cell(r, 5, 0)
            wc2.cell(r, 6, 0)
            wc2.cell(r, 7, "non")
        else:
            p = r - 1
            wc2.cell(r, 3, f"={wse_from_vtot(f'F{p}')}")
            wc2.cell(r, 4, f"=IF(F{p}<=0.01,MIN(0.5*(B{p}+B{r}),$B$4),{q_from_wse(f'C{r}')})")
            wc2.cell(r, 5, f"=(A{r}-A{p})*60")
            wc2.cell(r, 6, f"=MAX(0,F{p}+(0.5*(B{p}+B{r})-D{r})*E{r})")
            wc2.cell(r, 7, f'=IF(C{r}>$B$5,"oui","non")')
        for c in range(1, 8):
            wc2.cell(r, c).border = THIN
            if c <= 4:
                wc2.cell(r, c).number_format = "0.000"
            elif c <= 6:
                wc2.cell(r, c).number_format = "0.0"
        wc2.cell(r, 6).fill = GREEN

    ch_cc = LineChart()
    ch_cc.title = "Methode C — WSE(t) et V(t)"
    ch_cc.add_data(Reference(wc2, min_col=3, min_row=9, max_row=r0c + n - 1), titles_from_data=True)
    ch_cc.add_data(Reference(wc2, min_col=6, min_row=9, max_row=r0c + n - 1), titles_from_data=True)
    ch_cc.set_categories(Reference(wc2, min_col=1, min_row=r0c, max_row=r0c + n - 1))
    wc2.add_chart(ch_cc, "I3")

    # ========== Methode ==========
    wm = wb.create_sheet("Methode")
    wm["A1"] = "Methode — retention SANS Ø900"
    wm["A1"].font = Font(bold=True, size=13)
    lines = [
        "",
        "1. Le Ø900 est elimine: plus de controle etroit; le bassin peut etre agrandi (Stage_Storage).",
        "2. Entree: hydrogramme (pointe editable Hydrogramme!B4), typiquement via Ø1500.",
        "3. Sortie: Ø1200 = nouvel ouvrage de controle.",
        "   A) Qout = Q_plein Manning (formule Parametres!B18).",
        "   B) Qout = f(H) FHWA sur Courbe_QH_1200.",
        "   C) Qout = Q_1200 + overflow trapèze au-dessus du crest (berme/fosse).",
        "4. Effet attendu vs ancien Ø900: Qout plus grand → Vmax plus petit, pointe aval plus forte.",
        "5. Editez les jaunes; les verts et graphiques se recalculent.",
        "6. Fichier frere (ancien): Volume_Retention_Ponceau_900.xlsx (avec Ø900).",
    ]
    for i, line in enumerate(lines, start=2):
        wm.cell(i, 1, line)
    wm.column_dimensions["A"].width = 110

    # ========== README snippet in Fichiers ==========
    wf = wb.create_sheet("Readme")
    wf["A1"] = "Fichier: Volume_Retention_Sans_900.xlsx"
    wf["A1"].font = Font(bold=True)
    for i, line in enumerate(
        [
            "Onglets: Parametres | Hydrogramme | Calcul_A | Courbe_QH_1200 | Calcul_B |",
            "         Stage_Storage | Compose_1200 | Calcul_C | Methode | Readme",
            "Jaune = entree; vert = resultat; bleu = formule intermediaire.",
            "Regenerer: python3 build_retention_no_900_excel.py",
        ],
        start=3,
    ):
        wf.cell(i, 1, line)
    wf.column_dimensions["A"].width = 90

    wb.save(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path}")
