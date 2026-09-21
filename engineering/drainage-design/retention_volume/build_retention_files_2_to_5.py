#!/usr/bin/env python3
"""
Build Files 2–5 as separate Excel workbooks.

  File 2 — Compare pipe-only vs composite (Idea 2)
  File 3 — Stress cases on pipe capacity (Idea 3)
  File 4 — Time-series focus (Idea 4)
  File 5 — Crest sensitivity (Idea 5)
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

import retention_common as rc

HERE = Path(__file__).resolve().parent

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


def header_row(ws, row: int, titles: list[str]) -> None:
    for c, t in enumerate(titles, 1):
        cell = ws.cell(row, c, t)
        cell.font = HDR_FONT
        cell.fill = HDR_FILL
        cell.border = THIN


def yellow_input(ws, row: int, label: str, value, fmt: str = "0.000") -> None:
    ws.cell(row, 1, label)
    cell = ws.cell(row, 2, value)
    cell.fill = YELLOW
    cell.border = THIN
    if isinstance(value, (int, float)):
        cell.number_format = fmt


def write_method(ws, title: str, lines: list[str]) -> None:
    ws["A1"] = title
    ws["A1"].font = Font(bold=True, size=13, color="0F5C5C")
    for i, line in enumerate(lines, start=3):
        ws.cell(i, 1, line)
    ws.column_dimensions["A"].width = 100


def write_hydro_table(ws, steps: list[rc.Step], start_row: int = 10) -> int:
    header_row(
        ws,
        start_row,
        [
            "t (min)",
            "Qin",
            "WSE",
            "Q_1200",
            "Q_overflow",
            "Q_down",
            "V (m3)",
            "dt (s)",
            "dV_ov (m3)",
        ],
    )
    for i, s in enumerate(steps):
        r = start_row + 1 + i
        vals = [
            s.t_min,
            s.Qin,
            s.WSE,
            s.Q_pipe,
            s.Q_ov,
            s.Q_out,
            s.V,
            s.dt_s,
            s.Q_ov * s.dt_s,
        ]
        fmts = ["0.0", "0.000", "0.00", "0.000", "0.000", "0.000", "0.0", "0", "0.0"]
        for c, (v, f) in enumerate(zip(vals, fmts), 1):
            cell = ws.cell(r, c, v)
            cell.number_format = f
            cell.border = THIN
        ws.cell(r, 7).fill = GREEN
    return start_row + len(steps)


def build_file2() -> Path:
    path = HERE / "Retention_1200_File2_Compare.xlsx"
    qpeak, crest = rc.QPEAK_REF, rc.CREST
    pipe = rc.route(qpeak=qpeak, crest=crest, with_overflow=False)
    comp = rc.route(qpeak=qpeak, crest=crest, with_overflow=True)
    sp, sc = rc.summarize(pipe, crest), rc.summarize(comp, crest)

    wb = Workbook()
    ws = wb.active
    ws.title = "Comparaison"
    ws["A1"] = "FILE 2 — Comparaison: pipe seul vs pipe + fosse (Idee 2)"
    ws["A1"].font = Font(bold=True, size=14, color="0F5C5C")
    ws.merge_cells("A1:E1")
    ws["A2"] = (
        "Meme orage et meme bassin. Cas A = Ø1200 seul. "
        "Cas C = Ø1200 + overflow trapèze si WSE ≥ crest."
    )
    ws.merge_cells("A2:E3")
    ws["A2"].alignment = Alignment(wrap_text=True)

    yellow_input(ws, 5, "Qpointe (m3/s)", qpeak, "0.000")
    yellow_input(ws, 6, "Crest (m)", crest, "0.00")
    yellow_input(ws, 7, "Facteur securite (-)", 1.20, "0.00")
    ws["C5"] = "Apres changement: python3 build_retention_files_2_to_5.py"
    ws["C5"].fill = ORANGE

    header_row(ws, 9, ["Indicateur", "Cas A — pipe seul", "Cas C — composite", "Ecart C−A"])
    rows = [
        ("V_hold (m3)", sp["V_hold"], sc["V_hold"], "0.0"),
        ("V_dim = V_hold × facteur", sp["V_hold"] * 1.2, sc["V_hold"] * 1.2, "0.0"),
        ("WSEmax (m)", sp["WSEmax"], sc["WSEmax"], "0.00"),
        ("Q_down max (m3/s)", sp["Q_down_max"], sc["Q_down_max"], "0.000"),
        ("Q_1200 a la pointe", sp["Q_pipe_at_peak"], sc["Q_pipe_at_peak"], "0.000"),
        ("Q_overflow a la pointe", sp["Q_ov_at_peak"], sc["Q_ov_at_peak"], "0.000"),
        ("V_overflow (m3)", sp["V_overflow"], sc["V_overflow"], "0.0"),
    ]
    for i, (lab, a, c, fmt) in enumerate(rows):
        r = 10 + i
        ws.cell(r, 1, lab)
        for col, val, fill in ((2, a, BLUE), (3, c, GREEN), (4, c - a, None)):
            cell = ws.cell(r, col, val)
            cell.number_format = fmt
            cell.border = THIN
            if fill:
                cell.fill = fill

    ws["A18"] = "Lecture"
    ws["A18"].font = Font(bold=True)
    ws["A19"] = (
        "Si C a WSEmax plus bas et Q_down plus haut: overflow protege l'amont "
        "mais augmente la pointe aval. V_hold = volume a retenir a l'entree Ø1200."
    )
    ws.merge_cells("A19:E20")
    ws["A19"].alignment = Alignment(wrap_text=True)

    for col, w in zip("ABCDE", [34, 18, 18, 12, 12]):
        ws.column_dimensions[col].width = w

    wa = wb.create_sheet("Detail_PipeSeul")
    wa["A1"] = "Cas A — pipe seul"
    wa["A1"].font = Font(bold=True, color="0F5C5C")
    write_hydro_table(wa, pipe)
    wc = wb.create_sheet("Detail_Composite")
    wc["A1"] = "Cas C — composite"
    wc["A1"].font = Font(bold=True, color="0F5C5C")
    last = write_hydro_table(wc, comp)
    ch = LineChart()
    ch.title = "Cas C — WSE et Q_down"
    ch.add_data(Reference(wc, min_col=3, min_row=10, max_row=last), titles_from_data=True)
    ch.add_data(Reference(wc, min_col=6, min_row=10, max_row=last), titles_from_data=True)
    ch.set_categories(Reference(wc, min_col=1, min_row=11, max_row=last))
    wc.add_chart(ch, "K3")

    wm = wb.create_sheet("Methode")
    write_method(
        wm,
        "FILE 2 — Methode",
        [
            "Idee 2: comparer deux sorties pour le meme bassin / orage.",
            "  A) Qout = Q_1200 seulement",
            "  C) Qout = Q_1200 + Q_overflow (si WSE ≥ crest)",
            "",
            "V_hold = volume max stocke a l'entree du Ø1200.",
            "V_overflow = volume cumule parti par la fosse.",
            "",
            "Editez Qpointe/Crest (jaune) puis: python3 build_retention_files_2_to_5.py",
        ],
    )
    wb.save(path)
    return path


def build_file3() -> Path:
    path = HERE / "Retention_1200_File3_Stress.xlsx"
    qpeak, crest = rc.QPEAK_REF, rc.CREST
    cases = [
        ("Normal pipe 100%", 1.0, True),
        ("Pipe reduit 50%", 0.5, True),
        ("Pipe bloque 0%", 0.0, True),
        ("Pipe 100% SANS overflow", 1.0, False),
    ]

    wb = Workbook()
    ws = wb.active
    ws.title = "Stress"
    ws["A1"] = "FILE 3 — Stress sur capacite Ø1200 (Idee 3)"
    ws["A1"].font = Font(bold=True, size=14, color="0F5C5C")
    ws["A2"] = (
        "Que se passe-t-il si le pipe est degrade ou bloque? "
        "L'overflow reste disponible sauf au cas 'SANS overflow'."
    )
    ws.merge_cells("A2:G3")
    ws["A2"].alignment = Alignment(wrap_text=True)

    yellow_input(ws, 5, "Qpointe (m3/s)", qpeak)
    yellow_input(ws, 6, "Crest (m)", crest, "0.00")

    header_row(
        ws,
        8,
        [
            "Cas",
            "Facteur pipe",
            "Overflow?",
            "V_hold (m3)",
            "WSEmax (m)",
            "Q_down max",
            "V_overflow (m3)",
        ],
    )
    for i, (name, fac, ov) in enumerate(cases):
        steps = rc.route(qpeak=qpeak, crest=crest, pipe_factor=fac, with_overflow=ov)
        sm = rc.summarize(steps, crest)
        r = 9 + i
        ws.cell(r, 1, name)
        ws.cell(r, 2, fac).number_format = "0.00"
        ws.cell(r, 3, "oui" if ov else "non")
        for col, key, fmt in (
            (4, "V_hold", "0.0"),
            (5, "WSEmax", "0.00"),
            (6, "Q_down_max", "0.000"),
            (7, "V_overflow", "0.0"),
        ):
            cell = ws.cell(r, col, sm[key])
            cell.number_format = fmt
            cell.fill = GREEN
            cell.border = THIN
        for c in range(1, 4):
            ws.cell(r, c).border = THIN
        sh = wb.create_sheet(name.replace(" ", "_")[:28])
        sh["A1"] = name
        write_hydro_table(sh, steps)

    ws["A14"] = "Message"
    ws["A14"].font = Font(bold=True)
    ws["A15"] = (
        "Pipe bloque: V_hold / WSEmax montent; l'eau part surtout par la fosse si crest depasse. "
        "Montre le role de secours de l'overflow."
    )
    ws.merge_cells("A15:G16")

    ch = BarChart()
    ch.type = "col"
    ch.title = "V_hold par cas"
    ch.add_data(Reference(ws, min_col=4, min_row=8, max_row=12), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=9, max_row=12))
    ws.add_chart(ch, "A18")

    for col, w in zip("ABCDEFG", [26, 12, 12, 14, 12, 12, 14]):
        ws.column_dimensions[col].width = w

    wm = wb.create_sheet("Methode")
    write_method(
        wm,
        "FILE 3 — Methode",
        [
            "Idee 3: stress-test du Ø1200.",
            "  Facteur 1.0 = normal; 0.5 = encrasse; 0.0 = bloque.",
            "Comparer V_hold et WSEmax entre cas.",
        ],
    )
    wb.save(path)
    return path


def build_file4() -> Path:
    path = HERE / "Retention_1200_File4_TimeSeries.xlsx"
    qpeak, crest = rc.QPEAK_REF, rc.CREST
    steps = rc.route(qpeak=qpeak, crest=crest, with_overflow=True)
    sm = rc.summarize(steps, crest)

    wb = Workbook()
    ws = wb.active
    ws.title = "Series_temporelles"
    ws["A1"] = "FILE 4 — Series temporelles (Idee 4)"
    ws["A1"].font = Font(bold=True, size=14, color="0F5C5C")
    ws["A2"] = (
        "Qin, Q_1200, Q_overflow, Q_down et WSE dans le temps. "
        "Montre quand l'overflow demarre et que l'aval recoit pipe + fosse."
    )
    ws.merge_cells("A2:J3")
    ws["A2"].alignment = Alignment(wrap_text=True)

    yellow_input(ws, 5, "Qpointe (m3/s)", qpeak)
    yellow_input(ws, 6, "Crest (m)", crest, "0.00")

    for r, lab, key, fmt in (
        (8, "V_hold (m3)", "V_hold", "0.0"),
        (9, "V_overflow (m3)", "V_overflow", "0.0"),
        (10, "WSEmax (m)", "WSEmax", "0.00"),
        (11, "Q_down max (m3/s)", "Q_down_max", "0.000"),
    ):
        ws.cell(r, 1, lab)
        cell = ws.cell(r, 2, sm[key])
        cell.fill = GREEN
        cell.number_format = fmt

    last = write_hydro_table(ws, steps, start_row=13)
    ws.cell(13, 10, "V_ov_cumul")
    ws.cell(13, 10).font = HDR_FONT
    ws.cell(13, 10).fill = HDR_FILL
    for i in range(len(steps)):
        r = 14 + i
        ws.cell(r, 10, f"=I{r}" if i == 0 else f"=J{r-1}+I{r}")
        ws.cell(r, 10).number_format = "0.0"
        ws.cell(r, 10).border = THIN

    ch1 = LineChart()
    ch1.title = "Debits vs temps"
    ch1.y_axis.title = "Q (m3/s)"
    for col in (2, 4, 5, 6):
        ch1.add_data(Reference(ws, min_col=col, min_row=13, max_row=last), titles_from_data=True)
    ch1.set_categories(Reference(ws, min_col=1, min_row=14, max_row=last))
    ws.add_chart(ch1, "L3")

    ch2 = LineChart()
    ch2.title = "WSE et V vs temps"
    ch2.add_data(Reference(ws, min_col=3, min_row=13, max_row=last), titles_from_data=True)
    ch2.add_data(Reference(ws, min_col=7, min_row=13, max_row=last), titles_from_data=True)
    ch2.set_categories(Reference(ws, min_col=1, min_row=14, max_row=last))
    ws.add_chart(ch2, "L18")

    for col, w in zip("ABCDEFGHIJ", [10] * 10):
        ws.column_dimensions[col].width = w

    wm = wb.create_sheet("Methode")
    write_method(
        wm,
        "FILE 4 — Methode",
        [
            "Idee 4: comportement DANS LE TEMPS.",
            "Q_overflow quitte 0 quand le crest est depasse.",
            "Q_down = Q_1200 + Q_overflow a chaque pas.",
            "V_ov_cumul aboutit a V_overflow.",
        ],
    )
    wb.save(path)
    return path


def build_file5() -> Path:
    path = HERE / "Retention_1200_File5_CrestSensitivity.xlsx"
    qpeak = rc.QPEAK_REF
    crests = [36.80, 37.00, 37.28, 37.50, 37.80, 38.20]

    wb = Workbook()
    ws = wb.active
    ws.title = "Sensibilite_crest"
    ws["A1"] = "FILE 5 — Sensibilite au crest (Idee 5)"
    ws["A1"].font = Font(bold=True, size=14, color="0F5C5C")
    ws["A2"] = (
        "Meme orage et meme bassin; seul le crest change. "
        "Crest plus bas → overflow plus tot → souvent WSEmax plus bas, Q_down plus haut."
    )
    ws.merge_cells("A2:G3")
    ws["A2"].alignment = Alignment(wrap_text=True)

    yellow_input(ws, 5, "Qpointe (m3/s)", qpeak)
    ws["C5"] = "Crests jaunes en col. A — apres edition: relancer le script"

    header_row(
        ws,
        8,
        [
            "Crest (m)",
            "V_hold (m3)",
            "WSEmax (m)",
            "Q_down max",
            "Q_ov a pointe",
            "V_overflow (m3)",
            "Overflow?",
        ],
    )
    for i, crest in enumerate(crests):
        steps = rc.route(qpeak=qpeak, crest=crest, with_overflow=True)
        sm = rc.summarize(steps, crest)
        r = 9 + i
        c0 = ws.cell(r, 1, crest)
        c0.fill = YELLOW
        c0.number_format = "0.00"
        c0.border = THIN
        for col, key, fmt in (
            (2, "V_hold", "0.0"),
            (3, "WSEmax", "0.00"),
            (4, "Q_down_max", "0.000"),
            (5, "Q_ov_at_peak", "0.000"),
            (6, "V_overflow", "0.0"),
        ):
            cell = ws.cell(r, col, sm[key])
            cell.number_format = fmt
            cell.fill = GREEN
            cell.border = THIN
        ws.cell(r, 7, "oui" if sm["overflow"] else "non").border = THIN

    last_r = 8 + len(crests)
    ch1 = LineChart()
    ch1.title = "WSEmax vs Crest"
    ch1.add_data(Reference(ws, min_col=3, min_row=8, max_row=last_r), titles_from_data=True)
    ch1.set_categories(Reference(ws, min_col=1, min_row=9, max_row=last_r))
    ws.add_chart(ch1, "A18")

    ch2 = LineChart()
    ch2.title = "V_hold et Q_down max vs Crest"
    ch2.add_data(Reference(ws, min_col=2, min_row=8, max_row=last_r), titles_from_data=True)
    ch2.add_data(Reference(ws, min_col=4, min_row=8, max_row=last_r), titles_from_data=True)
    ch2.set_categories(Reference(ws, min_col=1, min_row=9, max_row=last_r))
    ws.add_chart(ch2, "I18")

    ws["A34"] = "Lecture"
    ws["A34"].font = Font(bold=True)
    ws["A35"] = (
        "Crest bas: plus d'overflow, souvent moins de V_hold, pointe aval plus forte. "
        "Crest haut: proche du cas pipe seul."
    )
    ws.merge_cells("A35:G36")

    for col, w in zip("ABCDEFG", [12, 14, 12, 12, 12, 14, 12]):
        ws.column_dimensions[col].width = w

    wm = wb.create_sheet("Methode")
    write_method(
        wm,
        "FILE 5 — Methode",
        [
            "Idee 5: sensibilite — un parametre (crest).",
            "Utile pour choisir une cote de debordement avec le client.",
            "Apres edition des crests: python3 build_retention_files_2_to_5.py",
        ],
    )
    wb.save(path)
    return path


def main() -> None:
    for fn in (build_file2, build_file3, build_file4, build_file5):
        p = fn()
        print(f"Wrote {p}")


if __name__ == "__main__":
    main()
