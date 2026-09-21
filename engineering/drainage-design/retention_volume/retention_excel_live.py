#!/usr/bin/env python3
"""Shared live-Excel builders for retention Files 2–5.

Yellow = inputs · green = results · blue = intermediate formulas.
Routing and rating curves are Excel formulas (not Python-computed values).
"""

from __future__ import annotations

from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

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
N_HYDRO = len(HYDRO_SHAPE)

N_MANNING = 0.013
D_PIPE = 1.20
L_PIPE = 31.30
Z_US = 33.60
Z_DS = 33.10
Z_POND = 34.88
CREST = 37.28
OV_B, OV_N, OV_Z, OV_S, OV_L = 2.0, 0.035, 2.0, 0.0085, 50.1

STAGES = [
    (Z_POND, 0, "Fond bassin"),
    (35.50, 120, "Placeholder — remplacer"),
    (36.01, 419, "Placeholder — remplacer"),
    (36.50, 480, "Placeholder — remplacer"),
    (37.00, 720, "Placeholder — remplacer"),
    (37.28, 2198, ""),
    (37.40, 1516, "Placeholder — remplacer"),
    (40.00, 3746, "Placeholder haut — remplacer"),
]

FILL_YELLOW = PatternFill("solid", fgColor="FFF59D")
FILL_GREEN = PatternFill("solid", fgColor="C8E6C9")
FILL_BLUE = PatternFill("solid", fgColor="BBDEFB")
FILL_ORANGE = PatternFill("solid", fgColor="FFE0B2")
HDR_FILL = PatternFill("solid", fgColor="0F5C5C")
HDR_FONT = Font(bold=True, color="FFFFFF")
THIN = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)


def hdr(ws: Worksheet, row: int, ncols: int) -> None:
    for c in range(1, ncols + 1):
        cell = ws.cell(row, c)
        cell.font = HDR_FONT
        cell.fill = HDR_FILL
        cell.border = THIN


def set_yellow(ws: Worksheet, row: int, col: int, value, fmt: str | None = None):
    cell = ws.cell(row, col, value)
    cell.fill = FILL_YELLOW
    cell.border = THIN
    if fmt:
        cell.number_format = fmt
    return cell


def set_green(ws: Worksheet, row: int, col: int, value, fmt: str | None = None):
    cell = ws.cell(row, col, value)
    cell.fill = FILL_GREEN
    cell.border = THIN
    if fmt:
        cell.number_format = fmt
    return cell


def set_blue(ws: Worksheet, row: int, col: int, value, fmt: str | None = None):
    cell = ws.cell(row, col, value)
    cell.fill = FILL_BLUE
    cell.border = THIN
    if fmt:
        cell.number_format = fmt
    return cell


def add_pipe_params(ws: Worksheet) -> None:
    ws["A8"] = "Ø1200 (jaune)"
    ws["A8"].font = Font(bold=True)
    for r, lab, val, fmt in [
        (9, "n Manning (-)", N_MANNING, "0.000"),
        (10, "D (m)", D_PIPE, "0.00"),
        (11, "L (m)", L_PIPE, "0.00"),
        (12, "Zin (m)", Z_US, "0.00"),
        (13, "Zout (m)", Z_DS, "0.00"),
    ]:
        ws.cell(r, 1, lab)
        set_yellow(ws, r, 2, val, fmt)
    ws["A14"] = "S0 = (Zin-Zout)/L"
    set_blue(ws, 14, 2, "=(B12-B13)/B11", "0.00000")
    ws["A15"] = "A plein (m2)"
    set_blue(ws, 15, 2, "=PI()*B10^2/4", "0.000")
    ws["A16"] = "R plein = D/4 (m)"
    set_blue(ws, 16, 2, "=B10/4", "0.000")
    ws["A17"] = "Q_plein Manning (m3/s)"
    set_green(ws, 17, 2, "=(1/B9)*B15*(B16^(2/3))*SQRT(B14)", "0.000")
    ws["A18"] = "Fond bassin WSE min (m)"
    set_yellow(ws, 18, 2, Z_POND, "0.00")


def add_overflow_params(ws: Worksheet, crest: float = CREST) -> None:
    ws["A20"] = "Overflow fosse trapezoidale (jaune)"
    ws["A20"].font = Font(bold=True)
    for r, lab, val, fmt in [
        (21, "Crest (m)", crest, "0.00"),
        (22, "b fond (m)", OV_B, "0.00"),
        (23, "n fosse (-)", OV_N, "0.000"),
        (24, "z (H:V)", OV_Z, "0.0"),
        (25, "S fosse (-)", OV_S, "0.0000"),
        (26, "L fosse (m)", OV_L, "0.0"),
    ]:
        ws.cell(r, 1, lab)
        set_yellow(ws, r, 2, val, fmt)
    ws["A28"] = "Facteur securite (-)"
    set_yellow(ws, 28, 2, 1.20, "0.00")


def add_hydrogramme(wb: Workbook) -> Worksheet:
    wh = wb.create_sheet("Hydrogramme")
    wh["A1"] = "Hydrogramme d'entree — formules live"
    wh["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wh["A2"] = "Qin = ratio × Qpointe (jaune B4). Changer B4 → Qin et routages se mettent a jour."
    wh["A4"] = "Qpointe (m3/s)"
    set_yellow(wh, 4, 2, QPEAK_REF, "0.000")
    for j, h in enumerate(["t (min)", "ratio", "Qin (m3/s)"], 1):
        wh.cell(6, j, h)
    hdr(wh, 6, 3)
    for i, (t, ratio) in enumerate(HYDRO_SHAPE):
        r = 7 + i
        wh.cell(r, 1, t).number_format = "0.0"
        wh.cell(r, 2, round(ratio, 6)).number_format = "0.000"
        cell = wh.cell(r, 3, f"=B{r}*$B$4")
        cell.number_format = "0.000"
        for c in range(1, 4):
            wh.cell(r, c).border = THIN
        if abs(t - 22.5) < 1e-9:
            cell.fill = FILL_ORANGE
    last_h = 6 + N_HYDRO
    ch = LineChart()
    ch.title = "Qin(t)"
    ch.y_axis.title = "Qin (m3/s)"
    ch.x_axis.title = "t (min)"
    ch.add_data(Reference(wh, min_col=3, min_row=6, max_row=last_h), titles_from_data=True)
    ch.set_categories(Reference(wh, min_col=1, min_row=7, max_row=last_h))
    wh.add_chart(ch, "E4")
    return wh


def add_stage_storage(wb: Workbook) -> Worksheet:
    wss = wb.create_sheet("Stage_Storage")
    wss["A1"] = "Stage–storage amont Ø1200 — editer surfaces jaunes"
    wss["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wss["A2"] = "V_pas = 0.5*(A_bas+A_haut)*dWSE. Colonnes C–E = formules live."
    wss.merge_cells("A2:F3")
    wss["A2"].alignment = Alignment(wrap_text=True)
    for j, h in enumerate(
        ["WSE (m)", "Surface A (m2) EDIT", "dWSE (m)", "V_pas (m3)", "V_cumul (m3)", "Role"], 1
    ):
        wss.cell(10, j, h)
    hdr(wss, 10, 6)
    for i, (wse, area, role) in enumerate(STAGES):
        r = 11 + i
        wss.cell(r, 1, wse).number_format = "0.00"
        set_yellow(wss, r, 2, area, "0")
        if i == 0:
            wss.cell(r, 3, 0)
            wss.cell(r, 4, 0)
            wss.cell(r, 5, 0)
        else:
            prev = r - 1
            wss.cell(r, 3, f"=A{r}-A{prev}").number_format = "0.00"
            wss.cell(r, 4, f"=0.5*(B{prev}+B{r})*C{r}").number_format = "0.0"
            set_green(wss, r, 5, f"=E{prev}+D{r}", "0.0")
        wss.cell(r, 6, role)
        for c in range(1, 7):
            wss.cell(r, c).border = THIN
        if abs(wse - 37.28) < 1e-9:
            for c in range(1, 7):
                if c != 2:
                    wss.cell(r, c).fill = FILL_ORANGE
    for col, w in zip("ABCDEF", [12, 18, 12, 12, 14, 36]):
        wss.column_dimensions[col].width = w
    return wss


def add_courbe_qh(wb: Workbook) -> tuple[Worksheet, int, int]:
    """FHWA Q=f(H). Returns (sheet, first_row, last_row). Needs Parametres!B9–B14."""
    wq = wb.create_sheet("Courbe_QH_1200")
    wq["A1"] = "Courbe Q=f(H) Ø1200 — FHWA inlet + outlet (LIVE)"
    wq["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wq["A2"] = "Lie a Parametres. Q_gouvernant = MIN(Qinlet, Qoutlet)."
    wq.merge_cells("A2:F2")

    for r, lab, ref in [
        (4, "n", "=Parametres!B9"),
        (5, "D (m)", "=Parametres!B10"),
        (6, "L (m)", "=Parametres!B11"),
        (7, "Zin (m)", "=Parametres!B12"),
        (8, "Zout (m)", "=Parametres!B13"),
        (9, "S0", "=Parametres!B14"),
    ]:
        wq.cell(r, 1, lab)
        set_blue(wq, r, 2, ref)
    wq["A10"] = "TW au-dessus Zout (m)"
    set_yellow(wq, 10, 2, 0.0, "0.00")
    wq["A11"] = "Entree"
    set_yellow(wq, 11, 2, "square_edge")

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
        set_green(wq, r, 5, f"=MIN(C{r},D{r})", "0.000")
        for c in range(1, 6):
            wq.cell(r, c).border = THIN
    last_q = first_q + n_hw - 1

    ch = LineChart()
    ch.title = "Q gouvernant vs HW (Ø1200)"
    ch.y_axis.title = "Q (m3/s)"
    ch.x_axis.title = "HW (m)"
    ch.add_data(Reference(wq, min_col=5, min_row=19, max_row=last_q), titles_from_data=True)
    ch.set_categories(Reference(wq, min_col=1, min_row=first_q, max_row=last_q))
    wq.add_chart(ch, "L4")
    return wq, first_q, last_q


def add_compose(
    wb: Workbook,
    title: str,
    *,
    crest_formula: str = "=Parametres!B21",
    pipe_factor_formula: str = "1",
    with_overflow: bool = True,
    first_q: int = 20,
    last_q: int = 80,
) -> tuple[Worksheet, int, int]:
    wc = wb.create_sheet(title)
    mode = "composite" if with_overflow else "pipe seul"
    wc["A1"] = f"{title} — Q_1200 + Q_overflow; V_pond + V_ditch ({mode})"
    wc["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wc["A2"] = "Colonnes = formules Excel. Crest / facteur pipe en jaune."
    wc.merge_cells("A2:K2")

    for r, lab, ref in [
        (4, "Crest", crest_formula),
        (5, "b", "=Parametres!B22"),
        (6, "n", "=Parametres!B23"),
        (7, "z", "=Parametres!B24"),
        (8, "S", "=Parametres!B25"),
        (9, "L", "=Parametres!B26"),
        (10, "Zin", "=Parametres!B12"),
        (11, "Facteur_pipe", pipe_factor_formula),
    ]:
        wc.cell(r, 1, lab)
        cell = wc.cell(r, 2, ref)
        cell.fill = FILL_YELLOW
        cell.border = THIN

    Crest, b_ref, n_ov, z_ref, S_ov, L_ov, Zin_c, fac = (
        "$B$4",
        "$B$5",
        "$B$6",
        "$B$7",
        "$B$8",
        "$B$9",
        "$B$10",
        "$B$11",
    )
    ss_wse = "Stage_Storage!$A$11:$A$18"
    ss_v = "Stage_Storage!$E$11:$E$18"
    hw_rng = f"Courbe_QH_1200!$A${first_q}:$A${last_q}"
    q_rng = f"Courbe_QH_1200!$E${first_q}:$E${last_q}"

    def v_pond(wse: str) -> str:
        m = f"MATCH({wse},{ss_wse},1)"
        return (
            f"IF({wse}<=INDEX({ss_wse},1),INDEX({ss_v},1),"
            f"IF({wse}>=INDEX({ss_wse},ROWS({ss_wse})),INDEX({ss_v},ROWS({ss_v})),"
            f"INDEX({ss_v},{m})+({wse}-INDEX({ss_wse},{m}))/"
            f"(INDEX({ss_wse},{m}+1)-INDEX({ss_wse},{m}))*"
            f"(INDEX({ss_v},{m}+1)-INDEX({ss_v},{m}))))"
        )

    def q1200_hw(hw: str) -> str:
        m = f"MATCH({hw},{hw_rng},1)"
        base = (
            f"IF({hw}<=0,0,"
            f"IF({hw}>=INDEX({hw_rng},ROWS({hw_rng})),INDEX({q_rng},ROWS({q_rng})),"
            f"INDEX({q_rng},{m})+({hw}-INDEX({hw_rng},{m}))/"
            f"(INDEX({hw_rng},{m}+1)-INDEX({hw_rng},{m}))*"
            f"(INDEX({q_rng},{m}+1)-INDEX({q_rng},{m}))))"
        )
        return f"({fac})*({base})"

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
        if with_overflow:
            wc.cell(r, 3, f"=MAX(0,{wse}-{Crest})").number_format = "0.00"
            y = f"C{r}"
            wc.cell(r, 4, f"=IF({y}<=0,0,({b_ref}+{z_ref}*{y})*{y})").number_format = "0.000"
            A = f"D{r}"
            wc.cell(r, 5, f"={A}*{L_ov}").number_format = "0.0"
            wc.cell(r, 6, f"={v_pond(wse)}").number_format = "0.0"
            set_green(wc, r, 7, f"=E{r}+F{r}", "0.0")
            hw = f"B{r}"
            wc.cell(r, 8, f"={q1200_hw(hw)}").number_format = "0.000"
            wc.cell(
                r,
                9,
                f"=IF({y}<=0,0,IF({n_ov}<=0,0,(1/{n_ov})*{A}*"
                f"IF(({b_ref}+2*{y}*SQRT(1+{z_ref}^2))<=0,0,"
                f"(({A}/({b_ref}+2*{y}*SQRT(1+{z_ref}^2)))^(2/3)))*SQRT({S_ov})))",
            ).number_format = "0.000"
            set_green(wc, r, 10, f"=H{r}+I{r}", "0.000")
        else:
            wc.cell(r, 3, 0).number_format = "0.00"
            wc.cell(r, 4, 0).number_format = "0.000"
            wc.cell(r, 5, 0).number_format = "0.0"
            wc.cell(r, 6, f"={v_pond(wse)}").number_format = "0.0"
            set_green(wc, r, 7, f"=F{r}", "0.0")
            hw = f"B{r}"
            wc.cell(r, 8, f"={q1200_hw(hw)}").number_format = "0.000"
            wc.cell(r, 9, 0).number_format = "0.000"
            set_green(wc, r, 10, f"=H{r}", "0.000")
        for c in range(1, 11):
            wc.cell(r, c).border = THIN
    c_last = c0 + n_comp - 1
    return wc, c0, c_last


def add_calcul(
    wb: Workbook,
    title: str,
    *,
    compose_name: str,
    c0: int,
    c_last: int,
    crest_ref: str = "=Parametres!B21",
    qplein_ref: str = "=Parametres!B17",
    wse0_ref: str = "=Parametres!B18",
) -> Worksheet:
    wc2 = wb.create_sheet(title)
    wc2["A1"] = f"{title} — routage level-pool (formules Excel)"
    wc2["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wc2["A2"] = (
        f"WSE depuis V_total ({compose_name}); "
        "Qout depuis rating Compose; ΔV = (Qin_moy − Qout)×Δt."
    )
    wc2.merge_cells("A2:H2")
    wc2["A4"] = "Q_plein ref"
    cell = wc2.cell(4, 2, qplein_ref)
    cell.fill = FILL_YELLOW
    cell.border = THIN
    cell.number_format = "0.000"
    wc2["A5"] = "Crest"
    cell = wc2.cell(5, 2, crest_ref)
    cell.fill = FILL_YELLOW
    cell.border = THIN
    cell.number_format = "0.00"

    vtot = f"{compose_name}!$G${c0}:$G${c_last}"
    wser = f"{compose_name}!$A${c0}:$A${c_last}"
    qoutr = f"{compose_name}!$J${c0}:$J${c_last}"
    q1200r = f"{compose_name}!$H${c0}:$H${c_last}"
    qovr = f"{compose_name}!$I${c0}:$I${c_last}"

    def wse_from_vtot(v: str) -> str:
        m = f"MATCH({v},{vtot},1)"
        return (
            f"IF({v}<=INDEX({vtot},1),INDEX({wser},1),"
            f"IF({v}>=INDEX({vtot},ROWS({vtot})),INDEX({wser},ROWS({wser})),"
            f"INDEX({wser},{m})+({v}-INDEX({vtot},{m}))/"
            f"(INDEX({vtot},{m}+1)-INDEX({vtot},{m}))*"
            f"(INDEX({wser},{m}+1)-INDEX({wser},{m}))))"
        )

    def interp(w: str, y_rng: str) -> str:
        m = f"MATCH({w},{wser},1)"
        return (
            f"IF({w}<=INDEX({wser},1),INDEX({y_rng},1),"
            f"IF({w}>=INDEX({wser},ROWS({wser})),INDEX({y_rng},ROWS({y_rng})),"
            f"INDEX({y_rng},{m})+({w}-INDEX({wser},{m}))/"
            f"(INDEX({wser},{m}+1)-INDEX({wser},{m}))*"
            f"(INDEX({y_rng},{m}+1)-INDEX({y_rng},{m}))))"
        )

    n = N_HYDRO
    r0c = 15
    wc2["A7"] = "V_hold = Vmax (m3)"
    set_green(wc2, 7, 2, f"=MAX(F{r0c}:F{r0c+n-1})", "0.0")
    wc2["A8"] = "WSEmax (m)"
    set_green(wc2, 8, 2, f"=MAX(C{r0c}:C{r0c+n-1})", "0.00")
    wc2["A9"] = "Q_down max (m3/s)"
    set_green(wc2, 9, 2, f"=MAX(D{r0c}:D{r0c+n-1})", "0.000")
    wc2["A10"] = "Q_1200 at Q_down max"
    set_green(
        wc2,
        10,
        2,
        f"=IFERROR(INDEX(G{r0c}:G{r0c+n-1},MATCH(B9,D{r0c}:D{r0c+n-1},0)),0)",
        "0.000",
    )
    wc2["A11"] = "Q_overflow at Q_down max"
    set_green(
        wc2,
        11,
        2,
        f"=IFERROR(INDEX(H{r0c}:H{r0c+n-1},MATCH(B9,D{r0c}:D{r0c+n-1},0)),0)",
        "0.000",
    )
    wc2["A12"] = "Overflow?"
    wc2["B12"] = '=IF(B8>$B$5,"oui","non")'
    wc2["B12"].fill = FILL_ORANGE
    wc2["A13"] = "V_overflow (m3)"
    set_green(wc2, 13, 2, f"=SUMPRODUCT(H{r0c}:H{r0c+n-1},E{r0c}:E{r0c+n-1})", "0.0")

    for j, h in enumerate(
        ["t", "Qin", "WSE", "Qout", "dt", "V", "Q_1200", "Q_overflow", "Overflow?"], 1
    ):
        wc2.cell(14, j, h)
    hdr(wc2, 14, 9)

    for i in range(n):
        r = r0c + i
        wc2.cell(r, 1, f"=Hydrogramme!A{7+i}")
        wc2.cell(r, 2, f"=Hydrogramme!C{7+i}")
        if i == 0:
            wc2.cell(r, 3, wse0_ref)
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
            set_green(wc2, r, 6, f"=MAX(0,F{p}+(0.5*(B{p}+B{r})-D{r})*E{r})", "0.0")
            wc2.cell(r, 7, f"={interp(f'C{r}', q1200r)}")
            wc2.cell(r, 8, f"={interp(f'C{r}', qovr)}")
            wc2.cell(r, 9, f'=IF(C{r}>$B$5,"oui","non")')
        for c in range(1, 10):
            wc2.cell(r, c).border = THIN
            if c <= 4 or c in (7, 8):
                wc2.cell(r, c).number_format = "0.000"
            elif c in (5, 6):
                wc2.cell(r, c).number_format = "0.0"

    last = r0c + n - 1
    ch = LineChart()
    ch.title = f"{title} — WSE et Qout"
    ch.add_data(Reference(wc2, min_col=3, min_row=14, max_row=last), titles_from_data=True)
    ch.add_data(Reference(wc2, min_col=4, min_row=14, max_row=last), titles_from_data=True)
    ch.set_categories(Reference(wc2, min_col=1, min_row=r0c, max_row=last))
    wc2.add_chart(ch, "K3")

    for col, w in zip("ABCDEFGHI", [8, 10, 10, 10, 8, 12, 10, 12, 12]):
        wc2.column_dimensions[col].width = w
    return wc2


def write_methode(wb: Workbook, title: str, lines: list[str]) -> None:
    wm = wb.create_sheet("Methode")
    wm["A1"] = title
    wm["A1"].font = Font(bold=True, size=13, color="0F5C5C")
    for i, line in enumerate(lines, start=3):
        wm.cell(i, 1, line)
    wm.column_dimensions["A"].width = 100
