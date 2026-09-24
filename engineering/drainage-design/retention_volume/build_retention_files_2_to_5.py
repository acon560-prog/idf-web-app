#!/usr/bin/env python3
"""
Build Files 2–5 as separate Excel workbooks with LIVE formulas.

  File 2 — Compare pipe-only vs composite
  File 3 — Stress cases on pipe capacity
  File 4 — Time-series focus
  File 5 — Crest sensitivity

Yellow = inputs · green = results. Change yellow cells → Excel recalculates.
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Font

import retention_excel_live as xl

HERE = Path(__file__).resolve().parent


def _base_parametres(wb: Workbook, title: str, blurb: str):
    ws = wb.active
    ws.title = "Parametres"
    ws["A1"] = title
    ws["A1"].font = Font(bold=True, size=14, color="0F5C5C")
    ws.merge_cells("A1:F1")
    ws["A2"] = blurb
    ws.merge_cells("A2:F3")
    ws["A2"].alignment = Alignment(wrap_text=True)
    xl.add_pipe_params(ws)
    xl.add_overflow_params(ws)
    for col, w in zip("ABCDEF", [42, 14, 40, 12, 12, 12]):
        ws.column_dimensions[col].width = w
    return ws


def _infra(wb: Workbook):
    xl.add_hydrogramme(wb)
    xl.add_stage_storage(wb)
    _, first_q, last_q = xl.add_courbe_qh(wb)
    return first_q, last_q


def build_file2() -> Path:
    path = HERE / "Retention_1200_File2_Compare.xlsx"
    wb = Workbook()
    ws = _base_parametres(
        wb,
        "FILE 2 — Comparaison: pipe seul vs composite (formules Excel)",
        "Meme orage et meme bassin. Cas A = Ø1200 seul. Cas C = Ø1200 + overflow. "
        "Jaune = entrees. Tous les resultats sont des formules live.",
    )
    first_q, last_q = _infra(wb)

    # Pipe-only compose + calcul
    _, c0a, cla = xl.add_compose(
        wb,
        "Compose_PipeSeul",
        crest_formula="=Parametres!B21",
        pipe_factor_formula="1",
        with_overflow=False,
        first_q=first_q,
        last_q=last_q,
    )
    xl.add_calcul(
        wb,
        "Calcul_PipeSeul",
        compose_name="Compose_PipeSeul",
        c0=c0a,
        c_last=cla,
    )

    # Composite compose + calcul
    _, c0c, clc = xl.add_compose(
        wb,
        "Compose_Composite",
        crest_formula="=Parametres!B21",
        pipe_factor_formula="1",
        with_overflow=True,
        first_q=first_q,
        last_q=last_q,
    )
    xl.add_calcul(
        wb,
        "Calcul_Composite",
        compose_name="Compose_Composite",
        c0=c0c,
        c_last=clc,
    )

    # Trial: pipe capped at Q_plein (no pressurized boost above Manning full)
    _, c0p, clp = xl.add_compose(
        wb,
        "Compose_QpleinCap",
        crest_formula="=Parametres!B21",
        pipe_factor_formula="1",
        with_overflow=False,
        first_q=first_q,
        last_q=last_q,
        q_cap_formula="=Parametres!B17",
    )
    xl.add_calcul(
        wb,
        "Calcul_QpleinCap",
        compose_name="Compose_QpleinCap",
        c0=c0p,
        c_last=clp,
    )

    # Summary comparison with live links
    ws["A30"] = "RESULTATS — comparaison (liens formules)"
    ws["A30"].font = Font(bold=True, size=12, color="0F5C5C")
    xl.hdr(ws, 31, 5)
    for j, h in enumerate(
        [
            "Indicateur",
            "Cas A — pipe FHWA",
            "Cas C — composite",
            "Essai — Q ≤ Q_plein",
            "Ecart Essai−A",
        ],
        1,
    ):
        ws.cell(31, j, h)
    rows = [
        (
            32,
            "V_hold (m3)",
            "=Calcul_PipeSeul!B7",
            "=Calcul_Composite!B7",
            "=Calcul_QpleinCap!B7",
        ),
        (
            33,
            "V_dim = V_hold × facteur",
            "=B32*B28",
            "=C32*B28",
            "=D32*B28",
        ),
        (
            34,
            "WSEmax (m)",
            "=Calcul_PipeSeul!B8",
            "=Calcul_Composite!B8",
            "=Calcul_QpleinCap!B8",
        ),
        (
            35,
            "Q_down max (m3/s)",
            "=Calcul_PipeSeul!B9",
            "=Calcul_Composite!B9",
            "=Calcul_QpleinCap!B9",
        ),
        (
            36,
            "Q_1200 a la pointe",
            "=Calcul_PipeSeul!B10",
            "=Calcul_Composite!B10",
            "=Calcul_QpleinCap!B10",
        ),
        (
            37,
            "Q_overflow a la pointe",
            "=Calcul_PipeSeul!B11",
            "=Calcul_Composite!B11",
            "=Calcul_QpleinCap!B11",
        ),
        (
            38,
            "V_overflow (m3)",
            "=Calcul_PipeSeul!B13",
            "=Calcul_Composite!B13",
            "=Calcul_QpleinCap!B13",
        ),
        (
            39,
            "Overflow? (WSEmax>crest)",
            "=Calcul_PipeSeul!B12",
            "=Calcul_Composite!B12",
            "=Calcul_QpleinCap!B12",
        ),
    ]
    for r, lab, a, c, d in rows:
        ws.cell(r, 1, lab)
        fmt = "0.000" if ("Q_" in lab or "WSE" in lab) else "0.0"
        if "Overflow" in lab:
            xl.set_green(ws, r, 2, a)
            xl.set_green(ws, r, 3, c)
            xl.set_green(ws, r, 4, d)
            ws.cell(r, 5, "")
        else:
            xl.set_green(ws, r, 2, a, fmt)
            xl.set_green(ws, r, 3, c, fmt)
            xl.set_green(ws, r, 4, d, fmt)
            xl.set_blue(ws, r, 5, f"=D{r}-B{r}", fmt)

    ws["A41"] = "Essai Q ≤ Q_plein"
    ws["A41"].font = Font(bold=True)
    ws["A42"] = (
        "Colonne D: Q_1200 plafonne a Parametres!B17 (Q_plein Manning ≈ 4.93 m3/s). "
        "Pas d'effet de charge au-dessus du plein. Comparer WSEmax (D34) au Crest (B21). "
        "Si D34 ≥ B21 → avec ce plafond, le niveau depasse le crest (overflow structure)."
    )
    ws.merge_cells("A42:F43")
    ws["A42"].alignment = Alignment(wrap_text=True)

    ws["A45"] = "Lecture"
    ws["A45"].font = Font(bold=True)
    ws["A46"] = (
        "Cas A = FHWA libre (Q peut > Q_plein). Essai = Q borne a Q_plein. "
        "Editez jaune (Qpointe Hydrogramme!B4, Crest B21, Q_plein B17) — Excel recalcule."
    )
    ws.merge_cells("A46:F47")
    ws["A46"].alignment = Alignment(wrap_text=True)

    xl.write_methode(
        wb,
        "FILE 2 — Methode (formules Excel)",
        [
            "Idee 2: comparer sorties pour le meme bassin / orage.",
            "  A) Qout = Q_1200 FHWA (Compose_PipeSeul)",
            "  C) Qout = Q_1200 + Q_overflow (Compose_Composite)",
            "  Essai) Qout = MIN(Q_FHWA, Q_plein) — pas de boost presse (Compose_QpleinCap)",
            "",
            "Toutes les cellules de resultat sont des formules (=Calcul_…!B7 etc.).",
            "V_hold = volume max stocke. V_overflow = Σ Q_overflow × dt.",
            "",
            "Editez jaune puis laissez Excel recalculer (pas besoin de relancer Python).",
            "Regenerer: python3 build_retention_files_2_to_5.py",
        ],
    )
    wb.save(path)
    return path


def build_file3() -> Path:
    path = HERE / "Retention_1200_File3_Stress.xlsx"
    wb = Workbook()
    ws = _base_parametres(
        wb,
        "FILE 3 — Stress sur capacite Ø1200 (formules Excel)",
        "Que se passe-t-il si le pipe est degrade ou bloque? "
        "Facteurs pipe jaunes. Overflow reste disponible sauf cas SANS overflow.",
    )
    # Extra yellow pipe factors on Parametres
    ws["A44"] = "Facteurs pipe (jaune) — utilises par Compose_*"
    ws["A44"].font = Font(bold=True)
    ws["A45"] = "Facteur normal"
    xl.set_yellow(ws, 45, 2, 1.0, "0.00")
    ws["A46"] = "Facteur reduit 50%"
    xl.set_yellow(ws, 46, 2, 0.5, "0.00")
    ws["A47"] = "Facteur bloque"
    xl.set_yellow(ws, 47, 2, 0.0, "0.00")

    first_q, last_q = _infra(wb)

    cases = [
        ("Compose_100pct", "Calcul_100pct", "=Parametres!B45", True),
        ("Compose_50pct", "Calcul_50pct", "=Parametres!B46", True),
        ("Compose_0pct", "Calcul_0pct", "=Parametres!B47", True),
        ("Compose_100_NoOv", "Calcul_100_NoOv", "=Parametres!B45", False),
    ]
    calc_names = []
    for compose_name, calc_name, fac, ov in cases:
        _, c0, cl = xl.add_compose(
            wb,
            compose_name,
            crest_formula="=Parametres!B21",
            pipe_factor_formula=fac,
            with_overflow=ov,
            first_q=first_q,
            last_q=last_q,
        )
        xl.add_calcul(wb, calc_name, compose_name=compose_name, c0=c0, c_last=cl)
        calc_names.append((calc_name, fac, ov))

    ws["A49"] = "RESULTATS stress (formules)"
    ws["A49"].font = Font(bold=True, size=12, color="0F5C5C")
    for j, h in enumerate(
        ["Cas", "Facteur", "Overflow?", "V_hold", "WSEmax", "Q_down max", "V_overflow"], 1
    ):
        ws.cell(50, j, h)
    xl.hdr(ws, 50, 7)

    labels = [
        "Normal pipe 100%",
        "Pipe reduit 50%",
        "Pipe bloque 0%",
        "Pipe 100% SANS overflow",
    ]
    for i, ((calc, fac, ov), lab) in enumerate(zip(calc_names, labels)):
        r = 51 + i
        ws.cell(r, 1, lab)
        ws.cell(r, 2, fac)
        ws.cell(r, 2).number_format = "0.00"
        ws.cell(r, 3, "oui" if ov else "non")
        xl.set_green(ws, r, 4, f"={calc}!B7", "0.0")
        xl.set_green(ws, r, 5, f"={calc}!B8", "0.00")
        xl.set_green(ws, r, 6, f"={calc}!B9", "0.000")
        xl.set_green(ws, r, 7, f"={calc}!B13", "0.0")

    ws["A56"] = "Message"
    ws["A56"].font = Font(bold=True)
    ws["A57"] = (
        "Pipe bloque: V_hold / WSEmax montent; l'eau part surtout par la fosse. "
        "Changez B45–B47 (jaune) — Excel recalcule."
    )
    ws.merge_cells("A57:G58")

    ch = BarChart()
    ch.type = "col"
    ch.title = "V_hold par cas"
    ch.add_data(Reference(ws, min_col=4, min_row=50, max_row=54), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=51, max_row=54))
    ws.add_chart(ch, "A60")

    xl.write_methode(
        wb,
        "FILE 3 — Methode (formules Excel)",
        [
            "Idee 3: stress-test du Ø1200 via Facteur_pipe sur Compose.",
            "  Facteur 1.0 = normal; 0.5 = encrasse; 0.0 = bloque.",
            "Q_1200 Compose = Facteur_pipe × Q_FHWA(HW).",
            "Resultats Parametres B51:B54 = liens formules vers chaque Calcul_*.",
        ],
    )
    wb.save(path)
    return path


def build_file4() -> Path:
    path = HERE / "Retention_1200_File4_TimeSeries.xlsx"
    wb = Workbook()
    ws = _base_parametres(
        wb,
        "FILE 4 — Series temporelles (formules Excel)",
        "Qin, Q_1200, Q_overflow, Q_down et WSE dans le temps — toutes formules live. "
        "Montre quand l'overflow demarre.",
    )
    first_q, last_q = _infra(wb)
    _, c0, cl = xl.add_compose(
        wb,
        "Compose",
        crest_formula="=Parametres!B21",
        pipe_factor_formula="1",
        with_overflow=True,
        first_q=first_q,
        last_q=last_q,
    )
    xl.add_calcul(wb, "Calcul_Composite", compose_name="Compose", c0=c0, c_last=cl)

    # Dashboard links + cumulative overflow formula column note
    ws["A30"] = "RESULTATS (liens formules → Calcul_Composite)"
    ws["A30"].font = Font(bold=True, size=12, color="0F5C5C")
    for r, lab, ref, fmt in [
        (31, "V_hold (m3)", "=Calcul_Composite!B7", "0.0"),
        (32, "V_overflow (m3)", "=Calcul_Composite!B13", "0.0"),
        (33, "WSEmax (m)", "=Calcul_Composite!B8", "0.00"),
        (34, "Q_down max (m3/s)", "=Calcul_Composite!B9", "0.000"),
        (35, "Q_1200 a la pointe", "=Calcul_Composite!B10", "0.000"),
        (36, "Q_overflow a la pointe", "=Calcul_Composite!B11", "0.000"),
    ]:
        ws.cell(r, 1, lab)
        xl.set_green(ws, r, 2, ref, fmt)

    ws["A38"] = (
        "Detail pas-a-pas: feuille Calcul_Composite (t, Qin, WSE, Qout, Q_1200, Q_overflow). "
        "Graphiques WSE/Qout inclus. Editez Hydrogramme!B4 ou Crest B21."
    )
    ws.merge_cells("A38:F39")
    ws["A38"].alignment = Alignment(wrap_text=True)

    # Extra chart sheet linking series — formulas already on Calcul; add V_ov_cumul
    calc = wb["Calcul_Composite"]
    n = xl.N_HYDRO
    r0 = 15
    calc.cell(14, 10, "V_ov_cumul")
    calc.cell(14, 10).font = xl.HDR_FONT
    calc.cell(14, 10).fill = xl.HDR_FILL
    for i in range(n):
        r = r0 + i
        if i == 0:
            calc.cell(r, 10, f"=H{r}*E{r}")
        else:
            calc.cell(r, 10, f"=J{r-1}+H{r}*E{r}")
        calc.cell(r, 10).number_format = "0.0"
        calc.cell(r, 10).border = xl.THIN
        calc.cell(r, 10).fill = xl.FILL_GREEN

    last = r0 + n - 1
    ch1 = LineChart()
    ch1.title = "Debits vs temps"
    ch1.y_axis.title = "Q (m3/s)"
    for col in (2, 4, 7, 8):
        ch1.add_data(Reference(calc, min_col=col, min_row=14, max_row=last), titles_from_data=True)
    ch1.set_categories(Reference(calc, min_col=1, min_row=r0, max_row=last))
    calc.add_chart(ch1, "K18")

    xl.write_methode(
        wb,
        "FILE 4 — Methode (formules Excel)",
        [
            "Idee 4: comportement DANS LE TEMPS (formules live).",
            "Q_overflow quitte 0 quand le crest est depasse.",
            "Q_down = Q_1200 + Q_overflow a chaque pas.",
            "V_ov_cumul (col J) aboutit a V_overflow = Calcul_Composite!B13.",
        ],
    )
    wb.save(path)
    return path


def build_file5() -> Path:
    path = HERE / "Retention_1200_File5_CrestSensitivity.xlsx"
    wb = Workbook()
    ws = _base_parametres(
        wb,
        "FILE 5 — Sensibilite au crest (formules Excel)",
        "Meme orage et meme bassin; seul le crest change (jaune par scenario). "
        "Crest plus bas → overflow plus tot → souvent WSEmax plus bas, Q_down plus haut.",
    )
    first_q, last_q = _infra(wb)

    crests = [36.80, 37.00, 37.28, 37.50, 37.80, 38.20]
    ws["A44"] = "Crests scenario (jaune) — chaque Compose_Ci lit sa cellule"
    ws["A44"].font = Font(bold=True)
    calc_names = []
    for i, crest in enumerate(crests):
        r = 45 + i
        ws.cell(r, 1, f"Crest scenario {i+1} (m)")
        xl.set_yellow(ws, r, 2, crest, "0.00")
        compose_name = f"Compose_C{i+1}"
        calc_name = f"Calcul_C{i+1}"
        # Short sheet names (Excel 31-char limit is fine)
        _, c0, cl = xl.add_compose(
            wb,
            compose_name,
            crest_formula=f"=Parametres!B{r}",
            pipe_factor_formula="1",
            with_overflow=True,
            first_q=first_q,
            last_q=last_q,
        )
        xl.add_calcul(
            wb,
            calc_name,
            compose_name=compose_name,
            c0=c0,
            c_last=cl,
            crest_ref=f"=Parametres!B{r}",
        )
        calc_names.append((r, calc_name))

    ws["A52"] = "RESULTATS sensibilite (formules)"
    ws["A52"].font = Font(bold=True, size=12, color="0F5C5C")
    for j, h in enumerate(
        ["Crest (m)", "V_hold", "WSEmax", "Q_down max", "Q_ov a pointe", "V_overflow", "Overflow?"],
        1,
    ):
        ws.cell(53, j, h)
    xl.hdr(ws, 53, 7)

    for i, (crest_row, calc) in enumerate(calc_names):
        r = 54 + i
        xl.set_yellow(ws, r, 1, f"=B{crest_row}", "0.00")
        xl.set_green(ws, r, 2, f"={calc}!B7", "0.0")
        xl.set_green(ws, r, 3, f"={calc}!B8", "0.00")
        xl.set_green(ws, r, 4, f"={calc}!B9", "0.000")
        xl.set_green(ws, r, 5, f"={calc}!B11", "0.000")
        xl.set_green(ws, r, 6, f"={calc}!B13", "0.0")
        ws.cell(r, 7, f'={calc}!B12')
        ws.cell(r, 7).border = xl.THIN

    last_r = 53 + len(crests)
    ch1 = LineChart()
    ch1.title = "WSEmax vs Crest"
    ch1.add_data(Reference(ws, min_col=3, min_row=53, max_row=last_r), titles_from_data=True)
    ch1.set_categories(Reference(ws, min_col=1, min_row=54, max_row=last_r))
    ws.add_chart(ch1, "A62")

    ch2 = LineChart()
    ch2.title = "V_hold et Q_down max vs Crest"
    ch2.add_data(Reference(ws, min_col=2, min_row=53, max_row=last_r), titles_from_data=True)
    ch2.add_data(Reference(ws, min_col=4, min_row=53, max_row=last_r), titles_from_data=True)
    ch2.set_categories(Reference(ws, min_col=1, min_row=54, max_row=last_r))
    ws.add_chart(ch2, "I62")

    ws["A78"] = "Lecture"
    ws["A78"].font = Font(bold=True)
    ws["A79"] = (
        "Editez B45–B50 (crests jaunes) — chaque Compose/Calcul et le tableau se mettent a jour. "
        "Crest bas: plus d'overflow, souvent moins de V_hold, pointe aval plus forte."
    )
    ws.merge_cells("A79:G80")

    xl.write_methode(
        wb,
        "FILE 5 — Methode (formules Excel)",
        [
            "Idee 5: sensibilite — un parametre (crest), formules live.",
            "Chaque scenario a Compose_Ci + Calcul_Ci lies a Parametres!B45+i.",
            "Utile pour choisir une cote de debordement avec le client.",
            "Pas besoin de relancer Python apres edition des crests jaunes.",
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
