#!/usr/bin/env python3
"""
FILE 1 — Composite retention model (Idea 1 only)

  Qin (Ø1500 / hydrograph)
    → pond Stage_Storage upstream of Ø1200
    → Qout = Q_1200(WSE) + Q_overflow_trapezoid(WSE)   [overflow if WSE ≥ crest]
    → report WSEmax, Vmax, Q_1200 peak, Q_overflow peak, Q_down peak

Separate file from Sans_900 / pipe-only workbooks.
Live Excel formulas; yellow = inputs; green = results.
"""

from __future__ import annotations

import math
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

HERE = Path(__file__).resolve().parent
OUT = HERE / "Retention_1200_File1_Composite.xlsx"

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
Z_US_1200 = 33.60
Z_DS_1200 = 33.10
Z_POND = 34.88
CREST = 37.28
OV_B, OV_N, OV_Z, OV_S, OV_L = 2.0, 0.035, 2.0, 0.0085, 50.1

YELLOW = PatternFill("solid", fgColor="FFF59D")
GREEN = PatternFill("solid", fgColor="C8E6C9")
BLUE = PatternFill("solid", fgColor="BBDEFB")
ORANGE = PatternFill("solid", fgColor="FFE0B2")
HDR_FILL = PatternFill("solid", fgColor="0F5C5C")
HDR_FONT = Font(bold=True, color="FFFFFF")
THIN = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)


def hdr(ws, row: int, ncols: int) -> None:
    for c in range(1, ncols + 1):
        cell = ws.cell(row, c)
        cell.font = HDR_FONT
        cell.fill = HDR_FILL
        cell.border = THIN


def build() -> Path:
    wb = Workbook()
    n = len(HYDRO_SHAPE)

    # ---------- Parametres ----------
    ws = wb.active
    ws.title = "Parametres"
    ws["A1"] = "FILE 1 — Composite: Ø1200 + fosse trapezoidale (overflow)"
    ws["A1"].font = Font(bold=True, size=14, color="0F5C5C")
    ws.merge_cells("A1:F1")
    ws["A2"] = (
        "But: WSE amont du Ø1200 si overflow actif, et pointe aval = Q_1200 + Q_overflow. "
        "Jaune = entrees. Autres fichiers (comparaison, series temporelles, sensibilite) = separes."
    )
    ws.merge_cells("A2:F3")
    ws["A2"].alignment = Alignment(wrap_text=True)

    ws["A5"] = "Schema"
    ws["A5"].font = Font(bold=True)
    ws["A6"] = "Qin → bassin (Stage_Storage) → Q_1200(WSE) + Q_fossé(WSE si WSE≥crest) → aval"

    # Pipe
    ws["A8"] = "Ø1200 (jaune)"
    ws["A8"].font = Font(bold=True)
    for r, lab, val, fmt in [
        (9, "n Manning (-)", N_MANNING, "0.000"),
        (10, "D (m)", D_1200, "0.00"),
        (11, "L (m)", L_1200, "0.00"),
        (12, "Zin (m)", Z_US_1200, "0.00"),
        (13, "Zout (m)", Z_DS_1200, "0.00"),
    ]:
        ws.cell(r, 1, lab)
        c = ws.cell(r, 2, val)
        c.fill = YELLOW
        c.border = THIN
        c.number_format = fmt
    ws["A14"] = "S0 = (Zin-Zout)/L"
    ws["B14"] = "=(B12-B13)/B11"
    ws["B14"].fill = BLUE
    ws["B14"].number_format = "0.00000"
    ws["A15"] = "A plein (m2)"
    ws["B15"] = "=PI()*B10^2/4"
    ws["B15"].fill = BLUE
    ws["B15"].number_format = "0.000"
    ws["A16"] = "R plein = D/4 (m)"
    ws["B16"] = "=B10/4"
    ws["B16"].fill = BLUE
    ws["B16"].number_format = "0.000"
    ws["A17"] = "Q_plein Manning (m3/s)"
    ws["B17"] = "=(1/B9)*B15*(B16^(2/3))*SQRT(B14)"
    ws["B17"].fill = GREEN
    ws["B17"].border = THIN
    ws["B17"].number_format = "0.000"
    ws["A18"] = "Fond bassin WSE min (m)"
    ws["B18"] = Z_POND
    ws["B18"].fill = YELLOW
    ws["B18"].border = THIN
    ws["B18"].number_format = "0.00"

    # Overflow trapezoid
    ws["A20"] = "Overflow fosse trapezoidale (jaune)"
    ws["A20"].font = Font(bold=True)
    for r, lab, val, fmt in [
        (21, "Crest (m)", CREST, "0.00"),
        (22, "b fond (m)", OV_B, "0.00"),
        (23, "n fosse (-)", OV_N, "0.000"),
        (24, "z (H:V)", OV_Z, "0.0"),
        (25, "S fosse (-)", OV_S, "0.0000"),
        (26, "L fosse (m)", OV_L, "0.0"),
    ]:
        ws.cell(r, 1, lab)
        c = ws.cell(r, 2, val)
        c.fill = YELLOW
        c.border = THIN
        c.number_format = fmt
    ws["C21"] = "Q_overflow = 0 si WSE < crest"
    ws["C25"] = "Pente fosse (ex. 0.0085)"

    ws["A28"] = "Facteur securite (-)"
    ws["B28"] = 1.20
    ws["B28"].fill = YELLOW
    ws["B28"].border = THIN
    ws["B28"].number_format = "0.00"

    # Results from Calcul
    ws["A30"] = "RESULTATS FILE 1 (Calcul_Composite)"
    ws["A30"].font = Font(bold=True, size=12, color="0F5C5C")
    ws["A31"] = "Vmax (m3) = max(V_pond + V_ditch)"
    ws["B31"] = "=Calcul_Composite!B7"
    ws["B31"].fill = GREEN
    ws["B31"].number_format = "0.0"
    ws["A32"] = "V_dimensionnement = Vmax × facteur"
    ws["B32"] = "=B31*B28"
    ws["B32"].fill = GREEN
    ws["B32"].number_format = "0.0"
    ws["A33"] = "WSEmax (m)"
    ws["B33"] = "=Calcul_Composite!B8"
    ws["B33"].fill = GREEN
    ws["B33"].number_format = "0.00"
    ws["C33"] = "Niveau max amont Ø1200"
    ws["A34"] = "Overflow atteint?"
    ws["B34"] = '=IF(B33>B21,"OUI — WSE > crest","NON — pipe seul")'
    ws["B34"].fill = ORANGE
    ws["A35"] = "Q_1200 a la pointe de Qout (m3/s)"
    ws["B35"] = "=Calcul_Composite!B10"
    ws["B35"].fill = GREEN
    ws["B35"].number_format = "0.000"
    ws["A36"] = "Q_overflow a la pointe de Qout (m3/s)"
    ws["B36"] = "=Calcul_Composite!B11"
    ws["B36"].fill = GREEN
    ws["B36"].number_format = "0.000"
    ws["A37"] = "Q_down max = Q_1200 + Q_overflow (m3/s)"
    ws["B37"] = "=Calcul_Composite!B9"
    ws["B37"].fill = GREEN
    ws["B37"].border = THIN
    ws["B37"].number_format = "0.000"
    ws["C37"] = "Pointe vue a l'aval"
    ws["A38"] = "HW max = WSEmax − Zin (m)"
    ws["B38"] = '=IF(ISNUMBER(B33),B33-B12,"")'
    ws["B38"].fill = GREEN
    ws["B38"].number_format = "0.00"

    ws["A40"] = "Message cle"
    ws["A40"].font = Font(bold=True)
    ws["A41"] = (
        "Si overflow OUI: l'aval recoit la somme pipe + fosse. "
        "WSEmax est le niveau dans le bassin amont du Ø1200 (eau retenue a l'entree)."
    )
    ws.merge_cells("A41:F42")
    ws["A41"].alignment = Alignment(wrap_text=True)

    for col, w in zip("ABCDEF", [42, 14, 40, 12, 12, 12]):
        ws.column_dimensions[col].width = w

    # ---------- Hydrogramme ----------
    wh = wb.create_sheet("Hydrogramme")
    wh["A1"] = "Hydrogramme d'entree — FILE 1"
    wh["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wh["A2"] = "Qin = ratio × Qpointe (jaune B4)."
    wh["A4"] = "Qpointe (m3/s)"
    wh["B4"] = QPEAK_REF
    wh["B4"].fill = YELLOW
    wh["B4"].border = THIN
    wh["B4"].number_format = "0.000"
    for j, h in enumerate(["t (min)", "ratio", "Qin (m3/s)"], 1):
        wh.cell(6, j, h)
    hdr(wh, 6, 3)
    for i, (t, ratio) in enumerate(HYDRO_SHAPE):
        r = 7 + i
        wh.cell(r, 1, t).number_format = "0.0"
        wh.cell(r, 2, round(ratio, 6)).number_format = "0.000"
        wh.cell(r, 3, f"=B{r}*$B$4").number_format = "0.000"
        for c in range(1, 4):
            wh.cell(r, c).border = THIN
        if abs(t - 22.5) < 1e-9:
            wh.cell(r, 3).fill = ORANGE
    last_h = 6 + n
    ch_h = LineChart()
    ch_h.title = "Qin(t)"
    ch_h.y_axis.title = "Qin (m3/s)"
    ch_h.x_axis.title = "t (min)"
    ch_h.add_data(Reference(wh, min_col=3, min_row=6, max_row=last_h), titles_from_data=True)
    ch_h.set_categories(Reference(wh, min_col=1, min_row=7, max_row=last_h))
    wh.add_chart(ch_h, "E4")

    # ---------- Stage_Storage ----------
    wss = wb.create_sheet("Stage_Storage")
    wss["A1"] = "Stage–storage amont Ø1200 — editer surfaces jaunes"
    wss["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wss["A2"] = (
        "V_pas = 0.5*(A_bas+A_haut)*dWSE. Aires synchronisees avec votre leve local. "
        "Role a 37.28 m laisse vide."
    )
    wss.merge_cells("A2:F3")
    wss["A2"].alignment = Alignment(wrap_text=True)
    for j, h in enumerate(
        ["WSE (m)", "Surface A (m2) EDIT", "dWSE (m)", "V_pas (m3)", "V_cumul (m3)", "Role"], 1
    ):
        wss.cell(10, j, h)
    hdr(wss, 10, 6)

    stages = [
        (Z_POND, 0, "Fond bassin"),
        (35.50, 120, "Placeholder — remplacer"),
        (36.01, 419, "Placeholder — remplacer"),
        (36.50, 480, "Placeholder — remplacer"),
        (37.00, 720, "Placeholder — remplacer"),
        (37.28, 2198, ""),  # empty Role — user request
        (37.40, 1516, "Placeholder — remplacer"),
        (40.00, 3746, "Placeholder haut — remplacer"),
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
        wss.cell(r, 6, "" if role is None else role)
        for c in range(1, 7):
            wss.cell(r, c).border = THIN
        if abs(wse - 37.28) < 1e-9:
            for c in range(1, 7):
                if c != 2:
                    wss.cell(r, c).fill = ORANGE

    wss["A21"] = "Vmax / WSEmax (FILE 1)"
    wss["B21"] = "=Parametres!B31"
    wss["C21"] = "=Parametres!B33"
    wss["A22"] = "V @ 37.28 m"
    wss["B22"] = "=E16"
    wss["B22"].fill = BLUE

    ch_s = LineChart()
    ch_s.title = "V cumul vs WSE"
    ch_s.y_axis.title = "V (m3)"
    ch_s.x_axis.title = "WSE (m)"
    ch_s.add_data(Reference(wss, min_col=5, min_row=10, max_row=18), titles_from_data=True)
    ch_s.set_categories(Reference(wss, min_col=1, min_row=11, max_row=18))
    wss.add_chart(ch_s, "H6")
    for col, w in zip("ABCDEF", [12, 18, 12, 12, 14, 36]):
        wss.column_dimensions[col].width = w

    # ---------- Courbe_QH_1200 (FHWA simplified) ----------
    wq = wb.create_sheet("Courbe_QH_1200")
    wq["A1"] = "Courbe Q=f(H) Ø1200 — FHWA inlet + outlet (LIVE)"
    wq["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wq["A2"] = "Lie a Parametres. Q_gouvernant = MIN(Qinlet, Qoutlet). Facteur 1.811 = conversion SI FHWA."
    wq.merge_cells("A2:F2")

    wq["A4"] = "n"
    wq["B4"] = "=Parametres!B9"
    wq["A5"] = "D (m)"
    wq["B5"] = "=Parametres!B10"
    wq["A6"] = "L (m)"
    wq["B6"] = "=Parametres!B11"
    wq["A7"] = "Zin (m)"
    wq["B7"] = "=Parametres!B12"
    wq["A8"] = "Zout (m)"
    wq["B8"] = "=Parametres!B13"
    wq["A9"] = "S0"
    wq["B9"] = "=Parametres!B14"
    wq["A10"] = "TW au-dessus Zout (m)"
    wq["B10"] = 0.0
    wq["B10"].fill = YELLOW
    wq["B10"].border = THIN
    wq["A11"] = "Entree"
    wq["B11"] = "square_edge"
    wq["B11"].fill = YELLOW
    wq["B11"].border = THIN

    for j, h in enumerate(["entree", "K", "M", "c", "Y", "Ke"], start=5):
        wq.cell(4, j, h)
        wq.cell(4, j).font = HDR_FONT
        wq.cell(4, j).fill = HDR_FILL
    for i, rowv in enumerate(
        [
            ("square_edge", 0.0098, 2.0, 0.0398, 0.67, 0.5),
            ("beveled", 0.0018, 2.5, 0.0300, 0.74, 0.2),
            ("groove_headwall", 0.0078, 2.0, 0.0292, 0.74, 0.2),
        ]
    ):
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
    hdr(wq, 19, 5)

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
    ch_q.set_categories(Reference(wq, min_col=1, min_row=first_q, max_row=last_q))
    wq.add_chart(ch_q, "L4")

    # ---------- Compose ----------
    wc = wb.create_sheet("Compose")
    wc["A1"] = "FILE 1 — Compose: Q_1200 + Q_overflow; V_pond + V_ditch"
    wc["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wc["A2"] = "Overflow Manning trapèze au-dessus du crest. Parametres lies (jaune)."
    wc.merge_cells("A2:K2")

    for r, lab, ref in [
        (4, "Crest", "=Parametres!B21"),
        (5, "b", "=Parametres!B22"),
        (6, "n", "=Parametres!B23"),
        (7, "z", "=Parametres!B24"),
        (8, "S", "=Parametres!B25"),
        (9, "L", "=Parametres!B26"),
        (10, "Zin", "=Parametres!B12"),
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
    hw_rng = f"Courbe_QH_1200!$A${first_q}:$A${last_q}"
    q_rng = f"Courbe_QH_1200!$E${first_q}:$E${last_q}"

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
        m = f"MATCH({hw},{hw_rng},1)"
        return (
            f'IF({hw}<=0,0,'
            f'IF({hw}>=INDEX({hw_rng},ROWS({hw_rng})),INDEX({q_rng},ROWS({q_rng})),'
            f'INDEX({q_rng},{m})+({hw}-INDEX({hw_rng},{m}))/'
            f'(INDEX({hw_rng},{m}+1)-INDEX({hw_rng},{m}))*'
            f'(INDEX({q_rng},{m}+1)-INDEX({q_rng},{m}))))'
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
    hdr(wc, 12, 10)

    wse0, wse1, step = Z_POND, 40.00, 0.10
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
    ch_c.title = "Qout = Q_1200 + Q_overflow vs WSE"
    ch_c.y_axis.title = "Q (m3/s)"
    ch_c.x_axis.title = "WSE (m)"
    ch_c.add_data(Reference(wc, min_col=10, min_row=12, max_row=c_last), titles_from_data=True)
    ch_c.add_data(Reference(wc, min_col=8, min_row=12, max_row=c_last), titles_from_data=True)
    ch_c.add_data(Reference(wc, min_col=9, min_row=12, max_row=c_last), titles_from_data=True)
    ch_c.set_categories(Reference(wc, min_col=1, min_row=c0, max_row=c_last))
    wc.add_chart(ch_c, "L4")

    # ---------- Calcul_Composite ----------
    wc2 = wb.create_sheet("Calcul_Composite")
    wc2["A1"] = "FILE 1 — Routage composite (eau retenue amont Ø1200)"
    wc2["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wc2["A2"] = (
        "A chaque pas: WSE depuis V_total (Compose); "
        "Qout = Q_1200 + Q_overflow; ΔV = (Qin_moy − Qout)×Δt."
    )
    wc2.merge_cells("A2:H2")
    wc2["A4"] = "Q_plein ref"
    wc2["B4"] = "=Parametres!B17"
    wc2["B4"].fill = YELLOW
    wc2["A5"] = "Crest"
    wc2["B5"] = "=Parametres!B21"
    wc2["B5"].fill = YELLOW

    vtot = f"Compose!$G${c0}:$G${c_last}"
    wser = f"Compose!$A${c0}:$A${c_last}"
    qoutr = f"Compose!$J${c0}:$J${c_last}"
    q1200r = f"Compose!$H${c0}:$H${c_last}"
    qovr = f"Compose!$I${c0}:$I${c_last}"

    def wse_from_vtot(v: str) -> str:
        m = f"MATCH({v},{vtot},1)"
        return (
            f'IF({v}<=INDEX({vtot},1),INDEX({wser},1),'
            f'IF({v}>=INDEX({vtot},ROWS({vtot})),INDEX({wser},ROWS({wser})),'
            f'INDEX({wser},{m})+({v}-INDEX({vtot},{m}))/'
            f'(INDEX({vtot},{m}+1)-INDEX({vtot},{m}))*'
            f'(INDEX({wser},{m}+1)-INDEX({wser},{m}))))'
        )

    def interp(w: str, y_rng: str) -> str:
        m = f"MATCH({w},{wser},1)"
        return (
            f'IF({w}<=INDEX({wser},1),INDEX({y_rng},1),'
            f'IF({w}>=INDEX({wser},ROWS({wser})),INDEX({y_rng},ROWS({y_rng})),'
            f'INDEX({y_rng},{m})+({w}-INDEX({wser},{m}))/'
            f'(INDEX({wser},{m}+1)-INDEX({wser},{m}))*'
            f'(INDEX({y_rng},{m}+1)-INDEX({y_rng},{m}))))'
        )

    r0c = 14
    wc2["A7"] = "Vmax (m3)"
    wc2["B7"] = f"=MAX(F{r0c}:F{r0c+n-1})"
    wc2["B7"].fill = GREEN
    wc2["B7"].number_format = "0.0"
    wc2["A8"] = "WSEmax (m)"
    wc2["B8"] = f"=MAX(C{r0c}:C{r0c+n-1})"
    wc2["B8"].fill = GREEN
    wc2["B8"].number_format = "0.00"
    wc2["A9"] = "Q_down max (m3/s)"
    wc2["B9"] = f"=MAX(D{r0c}:D{r0c+n-1})"
    wc2["B9"].fill = GREEN
    wc2["B9"].number_format = "0.000"
    # At timestep of max Qout, report split — approximate via MATCH on Qout column
    wc2["A10"] = "Q_1200 at Q_down max (m3/s)"
    wc2["B10"] = (
        f'=IFERROR(INDEX(G{r0c}:G{r0c+n-1},MATCH(B9,D{r0c}:D{r0c+n-1},0)),0)'
    )
    wc2["B10"].fill = GREEN
    wc2["B10"].number_format = "0.000"
    wc2["A11"] = "Q_overflow at Q_down max (m3/s)"
    wc2["B11"] = (
        f'=IFERROR(INDEX(H{r0c}:H{r0c+n-1},MATCH(B9,D{r0c}:D{r0c+n-1},0)),0)'
    )
    wc2["B11"].fill = GREEN
    wc2["B11"].number_format = "0.000"
    wc2["A12"] = "Overflow?"
    wc2["B12"] = '=IF(B8>$B$5,"oui","non")'

    for j, h in enumerate(
        ["t", "Qin", "WSE", "Qout", "dt", "V", "Q_1200", "Q_overflow", "Overflow?"], 1
    ):
        wc2.cell(13, j, h)
    hdr(wc2, 13, 9)

    for i in range(n):
        r = r0c + i
        wc2.cell(r, 1, f"=Hydrogramme!A{7+i}")
        wc2.cell(r, 2, f"=Hydrogramme!C{7+i}")
        if i == 0:
            wc2.cell(r, 3, "=Parametres!B18")
            wc2.cell(r, 4, f"=MIN(B{r},$B$4)")
            wc2.cell(r, 5, 0)
            wc2.cell(r, 6, 0)
            wc2.cell(r, 7, 0)
            wc2.cell(r, 8, 0)
            wc2.cell(r, 9, "non")
        else:
            p = r - 1
            wc2.cell(r, 3, f"={wse_from_vtot(f'F{p}')}")
            wc2.cell(
                r,
                4,
                f"=IF(F{p}<=0.01,MIN(0.5*(B{p}+B{r}),$B$4),{interp(f'C{r}', qoutr)})",
            )
            wc2.cell(r, 5, f"=(A{r}-A{p})*60")
            wc2.cell(r, 6, f"=MAX(0,F{p}+(0.5*(B{p}+B{r})-D{r})*E{r})")
            wc2.cell(r, 7, f"={interp(f'C{r}', q1200r)}")
            wc2.cell(r, 8, f"={interp(f'C{r}', qovr)}")
            wc2.cell(r, 9, f'=IF(C{r}>$B$5,"oui","non")')
        for c in range(1, 10):
            wc2.cell(r, c).border = THIN
            if c <= 4 or c in (7, 8):
                wc2.cell(r, c).number_format = "0.000"
            elif c in (5, 6):
                wc2.cell(r, c).number_format = "0.0"
        wc2.cell(r, 6).fill = GREEN

    ch_cc = LineChart()
    ch_cc.title = "FILE 1 — WSE(t) et Qout(t)"
    ch_cc.add_data(Reference(wc2, min_col=3, min_row=13, max_row=r0c + n - 1), titles_from_data=True)
    ch_cc.add_data(Reference(wc2, min_col=4, min_row=13, max_row=r0c + n - 1), titles_from_data=True)
    ch_cc.set_categories(Reference(wc2, min_col=1, min_row=r0c, max_row=r0c + n - 1))
    wc2.add_chart(ch_cc, "K3")

    ch_split = LineChart()
    ch_split.title = "Split aval: Q_1200 vs Q_overflow"
    ch_split.add_data(Reference(wc2, min_col=7, min_row=13, max_row=r0c + n - 1), titles_from_data=True)
    ch_split.add_data(Reference(wc2, min_col=8, min_row=13, max_row=r0c + n - 1), titles_from_data=True)
    ch_split.add_data(Reference(wc2, min_col=4, min_row=13, max_row=r0c + n - 1), titles_from_data=True)
    ch_split.set_categories(Reference(wc2, min_col=1, min_row=r0c, max_row=r0c + n - 1))
    wc2.add_chart(ch_split, "K18")

    for col, w in zip("ABCDEFGHI", [8, 10, 10, 10, 8, 12, 10, 12, 12]):
        wc2.column_dimensions[col].width = w

    # ---------- Methode ----------
    wm = wb.create_sheet("Methode")
    wm["A1"] = "FILE 1 — Methode (Idee 1 seule)"
    wm["A1"].font = Font(bold=True, size=13)
    for i, line in enumerate(
        [
            "",
            "Objectif: modeliser la retention amont du Ø1200 AVEC overflow fosse trapèze.",
            "",
            "Qout(WSE) = Q_1200(WSE) + Q_overflow(WSE)",
            "  • Q_1200 depuis Courbe_QH_1200 (FHWA)",
            "  • Q_overflow = 0 si WSE < crest; sinon Manning trapèze (b, n, z, S, L)",
            "",
            "V(WSE) = V_pond(Stage_Storage) + V_ditch (A_trapèze × L)",
            "",
            "Resultats cles (Parametres):",
            "  • WSEmax = niveau max retenu a l'entree du Ø1200",
            "  • Q_down max = pointe aval = pipe + overflow",
            "  • Split Q_1200 / Q_overflow a cette pointe",
            "",
            "Fichiers suivants (separes, pas encore dans ce classeur):",
            "  File 2 = comparaison pipe-only vs composite",
            "  File 3 = series temporelles detaillees (Idee 4)",
            "  File 4 = sensibilite crest (Idee 5)",
            "",
            "Regenerer: python3 build_retention_file1_composite.py",
        ],
        start=2,
    ):
        wm.cell(i, 1, line)
    wm.column_dimensions["A"].width = 100

    wb.save(OUT)
    return OUT


if __name__ == "__main__":
    p = build()
    print(f"Wrote {p}")
