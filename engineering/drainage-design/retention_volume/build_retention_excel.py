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

import math
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HERE = Path(__file__).resolve().parent
OUT = HERE / "Volume_Retention_Ponceau_900.xlsx"

# Measured hydrograph (min, m³/s) — crossings Qin=Qcap inserted at build time
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

# Ø900 geometry + Manning (full pipe) — user: n=0.013, Q = capacité pleine section
N_MANNING = 0.013
D_900_M = 0.9
L_900 = 50.65
Z_US_900 = 34.88
Z_DS_900 = 34.45
S0_900 = (Z_US_900 - Z_DS_900) / L_900


def q_full_manning(D: float, S0: float, n: float) -> float:
    A = math.pi * D**2 / 4.0
    R = D / 4.0
    return (1.0 / n) * A * (R ** (2.0 / 3.0)) * (S0**0.5)


Q_FULL_900 = q_full_manning(D_900_M, S0_900, N_MANNING)  # ≈ 1.668 m³/s
# Prior office value (~1.77) was same method, slight rounding / S0 difference
QCAP_900_PRIOR = 1.77
QCAP_900 = round(Q_FULL_900, 3)  # default used in routing
QCAP_1200 = 4.93
QPEAK_REF = 9.60  # original peak used to define dimensionless shape
QPEAK_IN = QPEAK_REF

# Dimensionless shape q*(t) = Q(t)/QPEAK_REF from the project hydrograph
HYDRO_SHAPE = [(t, q / QPEAK_REF) for t, q in HYDRO_RAW]
# Workbook / routing rows follow the raw times (shape scaled by editable Qpointe)
HYDRO = list(HYDRO_RAW)

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

    # --- Manning full-pipe capacity check ---
    ws["A12"] = "Capacité Ø900 — Manning pleine section (n = 0,013)"
    ws["A12"].font = Font(bold=True)
    ws["A13"] = "n Manning (-)"
    ws["B13"] = N_MANNING
    ws["B13"].fill = YELLOW
    ws["B13"].border = THIN
    ws["B13"].number_format = "0.000"
    ws["C13"] = "Fourni (béton typique ~0,012–0,015)"
    ws["A14"] = "D (m)"
    ws["B14"] = D_900_M
    ws["B14"].number_format = "0.00"
    ws["A15"] = "S0 = (Zamont−Zaval)/L"
    ws["B15"] = S0_900
    ws["B15"].number_format = "0.00000"
    ws["C15"] = "=(D6-E6)/F6"  # live formula; ASCII minus only (LibreOffice-safe)
    ws["A16"] = "A = πD²/4 (m²)"
    ws["B16"] = math.pi * D_900_M**2 / 4
    ws["B16"].number_format = "0.000"
    ws["A17"] = "R = D/4 (m)"
    ws["B17"] = D_900_M / 4
    ws["B17"].number_format = "0.000"
    ws["A18"] = "Q_plein = (1/n)·A·R^(2/3)·√S0"
    ws["B18"] = Q_FULL_900
    ws["B18"].fill = GREEN
    ws["B18"].border = THIN
    ws["B18"].number_format = "0.000"
    ws["C18"] = "m³/s — capacité pleine section (hypothèse actuelle)"
    ws["A19"] = "Q utilisé avant (m³/s)"
    ws["B19"] = QCAP_900_PRIOR
    ws["B19"].number_format = "0.00"
    ws["C19"] = "Ancienne valeur bureau (~6% plus haute; même méthode)"

    ws["A21"] = "Entrées de calcul rétention (jaune)"
    ws["A21"].font = Font(bold=True)
    ws["A22"] = "Qout_cap_900 (m³/s)"
    ws["B22"] = QCAP_900
    ws["B22"].fill = YELLOW
    ws["B22"].border = THIN
    ws["B22"].number_format = "0.000"
    ws["C22"] = "Par défaut = Q_plein Manning. Mettre 1.77 pour retrouver l'ancien calcul."
    ws["A23"] = "Facteur_securite (-)"
    ws["B23"] = 1.20
    ws["B23"].fill = YELLOW
    ws["B23"].border = THIN
    ws["B23"].number_format = "0.00"
    ws["C23"] = "Marge sur Vmax (ex. 1.20 = +20%)"
    ws["A24"] = "Aire_bassin_m2"
    ws["B24"] = 2500
    ws["B24"].fill = YELLOW
    ws["B24"].border = THIN
    ws["B24"].number_format = "0"
    ws["C24"] = "Aire plan d'eau approx. pour H = V/A (Méthode B)"

    ws["A26"] = "Résultats (formules — feuille Calcul_A)"
    ws["A26"].font = Font(bold=True)
    ws["A27"] = "Vmax (m³)"
    ws["B27"] = "=Calcul_A!B3"
    ws["B27"].fill = GREEN
    ws["B27"].number_format = "0"
    ws["A28"] = "V_dimensionnement = Vmax × facteur (m³)"
    ws["B28"] = "=B27*B23"
    ws["B28"].fill = GREEN
    ws["B28"].number_format = "0"
    ws["A29"] = "Hmax approx (m) = Vmax / Aire"
    ws["B29"] = "=IF(B24>0,B27/B24,0)"
    ws["B29"].fill = BLUE
    ws["B29"].number_format = "0.00"
    ws["C29"] = "Estimation grossière si l'aire de bassin est constante"

    ws["A30"] = "WSEmax depuis levé (m) — feuille Stage_Storage"
    # Interpolate Vmax (B27) on Stage_Storage V_cumul (E11:E18) → WSE (A11:A18)
    ws["B30"] = (
        '=IF(B27<=Stage_Storage!E11,Stage_Storage!A11,'
        'IF(B27>=Stage_Storage!E18,"Hors table (>=39.5 m — étendre levé)",'
        'INDEX(Stage_Storage!$A$11:$A$18,MATCH(B27,Stage_Storage!$E$11:$E$18,1))'
        '+(B27-INDEX(Stage_Storage!$E$11:$E$18,MATCH(B27,Stage_Storage!$E$11:$E$18,1)))'
        '/(INDEX(Stage_Storage!$E$11:$E$18,MATCH(B27,Stage_Storage!$E$11:$E$18,1)+1)'
        '-INDEX(Stage_Storage!$E$11:$E$18,MATCH(B27,Stage_Storage!$E$11:$E$18,1)))'
        '*(INDEX(Stage_Storage!$A$11:$A$18,MATCH(B27,Stage_Storage!$E$11:$E$18,1)+1)'
        '-INDEX(Stage_Storage!$A$11:$A$18,MATCH(B27,Stage_Storage!$E$11:$E$18,1)))))'
    )
    ws["B30"].fill = GREEN
    ws["B30"].number_format = "0.00"
    ws["C30"] = "Niveau d'eau max lu sur courbe volume–cote du levé (recommandé)"
    ws["A31"] = "HW max = WSEmax − radier Ø900 (m)"
    ws["B31"] = '=IF(ISNUMBER(B30),B30-34.88,"")'
    ws["B31"].fill = GREEN
    ws["B31"].number_format = "0.00"
    ws["C31"] = "Comparer à 2.40 m (limite patron = +1.5 m au-dessus du crown)"

    ws["A33"] = "Inlet control vs outlet control — qu'est-ce que ça veut dire?"
    ws["A33"].font = Font(bold=True)
    ic_oc = [
        "• Inlet control (contrôle à l'entrée): le débit est limité par l'entrée du ponceau (forme d'entrée, HW/D).",
        "  Le tuyau aval « n'aspire » pas assez pour influencer — Q dépend surtout de la charge amont H, pas de L ni de n.",
        "• Outlet control (contrôle à la sortie / frottement): le débit dépend de la longueur, de n, de la pente et de la charge",
        "  (énergie amont → aval). Manning pleine section est une hypothèse de type outlet/frottement à section pleine.",
        f"• Ici L/D = {L_900/D_900_M:.0f} (tuyau assez long) → le contrôle par frottement (outlet) est souvent plausible,",
        "  mais sans analyse FHWA/HY-8 on ne peut pas l'affirmer. Pour dimensionner la rétention, Q_plein constant est",
        "  en général prudent (si la charge monte, le débit réel peut être un peu plus élevé → Vmax un peu plus bas).",
        "• On n'a pas besoin de trancher IC/OC pour utiliser ce classeur: garder Qout = Q_plein (ou 1.77) suffit pour une 1re estimation.",
    ]
    for i, line in enumerate(ic_oc, start=34):
        ws.cell(i, 1, line)
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=8)

    ws["A43"] = "Notes"
    ws["A43"].font = Font(bold=True)
    notes = [
        "• Méthode A: Qout fixe = Q_plein Manning Ø900 (n=0,013). Pas un jugement IC/OC complet.",
        "• Le stockage commence quand Qin dépasse Qout; Vmax = max du volume stocké (pas (Qp−Qout)×durée).",
        "• Méthode B: Qout = f(H) depuis feuille Courbe_QH_900 (FHWA inlet+outlet).",
        "• Voir feuille Fichiers_lies pour les anciens Excel HY-8 / ponceau+fossé.",
        "• Vérifier que le radier amont Ø900 (34.88) est bien le fond de la zone de rétention étudiée.",
        "• Niveau max (WSEmax): feuille Stage_Storage + case Parametres!B30 (Vmax → cote du levé).",
    ]
    for i, line in enumerate(notes, start=44):
        ws.cell(i, 1, line)
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=8)

    for col, w in zip("ABCDEFGH", [36, 14, 55, 16, 16, 14, 12, 26]):
        ws.column_dimensions[col].width = w

    # ---------- Hydrogramme (shape × editable Qpointe) ----------
    wh = wb.create_sheet("Hydrogramme")
    wh["A1"] = "Hydrogramme d'entrée (point Ø1500 / entrée rétention) — FORMULES LIVE"
    wh["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wh["A2"] = (
        "Qin(t) = ratio(t) × Qpointe. Changez Qpointe (jaune B4) : toute la colonne Qin et Calcul_A/B se mettent à jour. "
        "Les ratios viennent de votre hydrogramme d'origine (pointe 9,6). "
        "À t=0, ratio≈0,081 → Qin=0,778 si Qpointe=9,6 (débit de départ du projet, pas zéro)."
    )
    wh.merge_cells("A2:F3")
    wh["A2"].alignment = Alignment(wrap_text=True, vertical="top")

    wh["A4"] = "Qpointe (m³/s) ← ÉDITER"
    wh["B4"] = QPEAK_REF
    wh["B4"].fill = YELLOW
    wh["B4"].border = THIN
    wh["B4"].number_format = "0.000"
    wh["C4"] = "Ex. 9.6 = pointe projet / capacité Ø1500"
    wh["A5"] = "t pointe (min)"
    wh["B5"] = 22.5
    wh["B5"].fill = YELLOW
    wh["B5"].number_format = "0.0"
    wh["C5"] = "Forme temporelle inchangée si vous changez seulement Qpointe"

    headers = ["t (min)", "ratio Q/Qp_ref", "Qin (m³/s)", "Remarque"]
    for j, h in enumerate(headers, start=1):
        wh.cell(7, j, h)
    style_header(wh, 7, 4)

    for i, (t, ratio) in enumerate(HYDRO_SHAPE):
        r = 8 + i
        wh.cell(r, 1, t).border = THIN
        wh.cell(r, 1).number_format = "0.0"
        wh.cell(r, 2, round(ratio, 6)).border = THIN
        wh.cell(r, 2).number_format = "0.000"
        wh.cell(r, 2).fill = BLUE
        wh.cell(r, 3, f"=B{r}*$B$4").border = THIN
        wh.cell(r, 3).number_format = "0.000"
        note = ""
        if abs(t - 22.5) < 1e-9:
            note = "Pointe (ratio = 1)"
            wh.cell(r, 3).fill = ORANGE
        elif i == 0:
            note = "Départ: ≈0.081 × Qpointe (0.778 si Qp=9.6)"
        wh.cell(r, 4, note).border = THIN
    last_h = 7 + len(HYDRO_SHAPE)
    sum_row = last_h + 2
    wh.cell(sum_row, 1, "Qin max (contrôle)")
    wh.cell(sum_row, 2, f"=MAX(C8:C{last_h})")
    wh.cell(sum_row, 2).fill = GREEN
    wh.cell(sum_row, 2).number_format = "0.000"
    wh.cell(sum_row, 3, "doit égaler Qpointe")
    wh.cell(sum_row + 1, 1, "Qcap Ø900 (réf.)")
    wh.cell(sum_row + 1, 2, "=Parametres!B22")
    wh.cell(sum_row + 1, 2).number_format = "0.000"

    chart = LineChart()
    chart.title = "Hydrogramme Qin (scalé par Qpointe)"
    chart.style = 10
    chart.y_axis.title = "Q (m³/s)"
    chart.x_axis.title = "t (min)"
    chart.add_data(Reference(wh, min_col=3, min_row=7, max_row=last_h), titles_from_data=True)
    chart.set_categories(Reference(wh, min_col=1, min_row=8, max_row=last_h))
    chart.shape = 4
    wh.add_chart(chart, "F7")
    for col, w in zip("ABCD", [12, 16, 14, 48]):
        wh.column_dimensions[col].width = w

    # ---------- Calcul_A : constant Qout ----------
    wa = wb.create_sheet("Calcul_A")
    wa["A1"] = "Méthode A — Qout constant = capacité Ø900"
    wa["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wa["A2"] = "Qout (m³/s)"
    wa["B2"] = "=Parametres!B22"
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
        wh_row = 8 + i
        wa.cell(r, 1, f"=Hydrogramme!A{wh_row}").border = THIN
        wa.cell(r, 1).number_format = "0.0"
        wa.cell(r, 2, f"=Hydrogramme!C{wh_row}").border = THIN
        wa.cell(r, 2).number_format = "0.000"
        wa.cell(r, 3, "=$B$2").border = THIN
        wa.cell(r, 3).number_format = "0.00"
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
            wa.cell(r, 7, f"=F{r}-(H{r}-H{prev})").border = THIN
            wa.cell(r, 7).number_format = "0.0"
            wa.cell(r, 8, f"=MAX(0,H{prev}+0.5*(D{prev}+D{r})*E{r})").border = THIN
            wa.cell(r, 8).number_format = "0.0"
        wa.cell(r, 8).fill = GREEN
        wa.cell(r, 9, f'=IF(H{r}>0.5,"oui","non")').border = THIN

    wa["A5"] = "t début stockage approx (min)"
    wa["B5"] = "quand Qin dépasse Qout (dépend de Qpointe et Qcap)"
    wa["A6"] = "t fin accumulation nette (min)"
    wa["B6"] = "quand Qin redescend sous Qout"

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

    # ---------- Courbe Q=f(H) FHWA HDS-5 (Ø900) — FORMULES LIVE ----------
    wq = wb.create_sheet("Courbe_QH_900")
    wq["A1"] = "Courbe de capacité Ø900 — Q = f(H) (FHWA HDS-5 inlet + outlet) — FORMULES LIVE"
    wq["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wq["A2"] = (
        "Changez les cellules JAUNES (n, D, L, radiers, entrée, TW) : toute la table se recalcule. "
        "Q_gouvernant = MIN(Qinlet, Qoutlet) = debit retenu pour le design. Sur ce tuyau long, Q_gouvernant suit Qoutlet (courbe verte). Qinlet (rouge) est seulement la capacite d'entree — souvent plus haute."
    )
    wq.merge_cells("A2:G3")
    wq["A2"].alignment = Alignment(wrap_text=True, vertical="top")

    # --- Editable geometry / hydraulics (yellow) ---
    wq["A5"] = "Paramètres Ø900 (jaune = éditable)"
    wq["A5"].font = Font(bold=True)
    params_q = [
        (6, "n Manning (-)", N_MANNING, "0.000", "béton typ. 0.012–0.015"),
        (7, "D (m)", D_900_M, "0.00", ""),
        (8, "L (m)", L_900, "0.00", ""),
        (9, "Radier amont Zin (m)", Z_US_900, "0.00", ""),
        (10, "Radier aval Zout (m)", Z_DS_900, "0.00", ""),
        (11, "S0 = (Zin-Zout)/L", "=(B9-B10)/B8", "0.00000", "ASCII minus; LibreOffice FR: OK"),
        (12, "TW (m au-dessus Zout)", 0.0, "0.00", "0 = exutoire libre"),
        (13, "Entrée (texte exact)", "square_edge", "@", "square_edge | beveled | groove_headwall"),
    ]
    for row, label, val, fmt, note in params_q:
        wq.cell(row, 1, label)
        cell = wq.cell(row, 2, val)
        cell.fill = YELLOW
        cell.border = THIN
        if fmt != "@":
            cell.number_format = fmt
        wq.cell(row, 3, note)

    # Q_plein live
    wq["A15"] = "Q_plein Manning (réf.)"
    wq["B15"] = "=(1/B6)*(PI()*B7^2/4)*((B7/4)^(2/3))*SQRT(B11)"
    wq["B15"].fill = GREEN
    wq["B15"].number_format = "0.000"
    wq["C15"] = "m³/s — se met à jour avec n, D, S0"

    # HDS-5 entrance coefficient table + VLOOKUP into K–O
    wq["E5"] = "Coeffs HDS-5 (table)"
    wq["E5"].font = Font(bold=True)
    coeff_hdr = ["entrée", "K", "M", "c", "Y", "Ke"]
    for j, h in enumerate(coeff_hdr, start=5):
        wq.cell(6, j, h)
        wq.cell(6, j).fill = HEADER_FILL
        wq.cell(6, j).font = HEADER
    coeffs = [
        ("square_edge", 0.0098, 2.0, 0.0398, 0.67, 0.5),
        ("beveled", 0.0018, 2.5, 0.0300, 0.74, 0.2),
        ("groove_headwall", 0.0078, 2.0, 0.0292, 0.74, 0.2),
    ]
    for i, rowv in enumerate(coeffs):
        for j, v in enumerate(rowv):
            wq.cell(7 + i, 5 + j, v).border = THIN

    wq["A17"] = "K (lu)"
    wq["B17"] = '=IFERROR(VLOOKUP(B13,$E$7:$J$9,2,FALSE),0.0098)'
    wq["A18"] = "M (lu)"
    wq["B18"] = '=IFERROR(VLOOKUP(B13,$E$7:$J$9,3,FALSE),2)'
    wq["A19"] = "c (lu)"
    wq["B19"] = '=IFERROR(VLOOKUP(B13,$E$7:$J$9,4,FALSE),0.0398)'
    wq["A20"] = "Y (lu)"
    wq["B20"] = '=IFERROR(VLOOKUP(B13,$E$7:$J$9,5,FALSE),0.67)'
    wq["A21"] = "Ke (lu)"
    wq["B21"] = '=IFERROR(VLOOKUP(B13,$E$7:$J$9,6,FALSE),0.5)'
    for r in range(17, 22):
        wq.cell(r, 2).fill = BLUE
        wq.cell(r, 2).number_format = "0.0000"

    # Named-style absolute refs for row formulas
    D = "$B$7"
    L = "$B$8"
    Zin = "$B$9"
    S0 = "$B$11"
    TW = "$B$12"
    n_ref = "$B$6"
    K = "$B$17"
    M = "$B$18"
    c = "$B$19"
    Y = "$B$20"
    Ke = "$B$21"
    KU = "1.811"
    G = "9.81"

    def f_qinlet(hw: str) -> str:
        """HDS-5 Form-2 inverse; avoid blend dip (use unsubmerged until 1.2D, then max)."""
        A = f"(PI()*({D}/2)^2)"
        qun = (
            f"{KU}*{A}*SQRT({D})"
            f"*IF({K}*{D}<=0,0,({hw}/({K}*{D}))^(1/{M}))"
        )
        # unsubmerged Q evaluated at HW=1.2D (switch point) — floor so curve never drops
        qun_sw = (
            f"{KU}*{A}*SQRT({D})"
            f"*IF({K}*{D}<=0,0,((1.2*{D})/({K}*{D}))^(1/{M}))"
        )
        qsub = (
            f"{KU}*{A}*SQRT({D})"
            f"*SQRT(MAX(0,({hw}/{D}-{Y})/{c}))"
        )
        return (
            f"IF({hw}<=0,0,"
            f"IF({hw}<=1.2*{D},{qun},"
            f"MAX({qun_sw},{qsub})))"
        )

    def f_qoutlet(hw: str) -> str:
        ratio = f"MIN(0.999,MAX(1E-6,{hw}/{D}))"
        theta = f"2*ACOS(1-2*({ratio}))"
        aseg = f"(({D}/2)^2/2)*(({theta})-SIN({theta}))"
        pwet = f"({D}/2)*({theta})"
        rh_p = f"IF(({pwet})<=0,0,({aseg})/({pwet}))"
        q_part = (
            f"IF({n_ref}<=0,0,(1/{n_ref})*({aseg})"
            f"*IF(({rh_p})<=0,0,({rh_p})^(2/3))*SQRT({S0}))"
        )
        a_full = f"(PI()*({D}/2)^2)"
        rh_f = f"{D}/4"
        hloss = f"{hw}-{TW}+{S0}*{L}"
        denom = f"(1+{Ke})/(2*{G})+({n_ref}^2)*{L}/(({rh_f})^(4/3))"
        q_full = f"IF(({hloss})<=0,0,{a_full}*SQRT(({hloss})/({denom})))"
        return f"IF({hw}<{D},{q_part},{q_full})"

    hdr_q = ["HW (m)", "WSE (m)", "Qinlet", "Qoutlet", "Q gouvernant", "Contrôle"]
    for j, h in enumerate(hdr_q, start=1):
        wq.cell(23, j, h)
    style_header(wq, 23, 6)

    first_q = 24
    n_hw = 61  # 0.00 → 3.00 step 0.05
    for i in range(n_hw):
        r = first_q + i
        hw_val = round(i * 0.05, 2)
        wq.cell(r, 1, hw_val).number_format = "0.00"
        wq.cell(r, 1).border = THIN
        hw = f"A{r}"
        wq.cell(r, 2, f"={Zin}+{hw}").number_format = "0.00"
        wq.cell(r, 2).border = THIN
        wq.cell(r, 3, f"={f_qinlet(hw)}").number_format = "0.000"
        wq.cell(r, 3).border = THIN
        wq.cell(r, 4, f"={f_qoutlet(hw)}").number_format = "0.000"
        wq.cell(r, 4).border = THIN
        wq.cell(r, 5, f"=MIN(C{r},D{r})").number_format = "0.000"
        wq.cell(r, 5).border = THIN
        wq.cell(r, 5).fill = GREEN
        wq.cell(r, 6, f'=IF(A{r}<=0,"—",IF(C{r}<=D{r},"inlet","outlet"))').border = THIN
    last_q = first_q + n_hw - 1

    # Highlight boss stage HW = 2.40 (1.5 above crown) if present: row 24+48 = 72
    boss_row = first_q + int(round(2.40 / 0.05))
    if first_q <= boss_row <= last_q:
        for c in range(1, 7):
            if c != 5:
                wq.cell(boss_row, c).fill = ORANGE
        wq.cell(boss_row, 5).fill = ORANGE

    ch_q = LineChart()
    ch_q.title = "Q gouvernant vs HW (Ø900) — live"
    ch_q.y_axis.title = "Q (m³/s)"
    ch_q.x_axis.title = "HW (m)"
    ch_q.add_data(Reference(wq, min_col=5, min_row=23, max_row=last_q), titles_from_data=True)
    ch_q.add_data(Reference(wq, min_col=3, min_row=23, max_row=last_q), titles_from_data=True)
    ch_q.add_data(Reference(wq, min_col=4, min_row=23, max_row=last_q), titles_from_data=True)
    ch_q.set_categories(Reference(wq, min_col=1, min_row=first_q, max_row=last_q))
    wq.add_chart(ch_q, "L5")

    for col, w in zip("ABCDEF", [28, 14, 42, 12, 12, 12]):
        wq.column_dimensions[col].width = w
    wq.column_dimensions["E"].width = 14
    wq.column_dimensions["J"].width = 8

    first_q, last_q = 24, 84  # live Courbe_QH_900 table rows

    # ---------- Calcul_B : routage avec courbe FHWA ----------
    wb2 = wb.create_sheet("Calcul_B")
    wb2["A1"] = "Méthode B — routage avec Qout = f(H) depuis Courbe_QH_900 (FHWA)"
    wb2["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wb2["A2"] = (
        "H = V / Aire_bassin. Qout interpolé sur Courbe_QH_900!E (Q gouvernant). "
        "Si V≈0, Qout = MIN(Qin, Q_plein). ΔV = (Qin_moy - Qout)*Δt. La courbe Courbe_QH_900 est en formules live (changer n/L/entrée/TW)."
    )
    wb2.merge_cells("A2:G3")
    wb2["A2"].alignment = Alignment(wrap_text=True)

    wb2["A5"] = "Aire (m²)"
    wb2["B5"] = "=Parametres!B24"
    wb2["B5"].fill = YELLOW
    wb2["A6"] = "Q_plein réf. (m³/s)"
    wb2["B6"] = "=Parametres!B22"
    wb2["B6"].fill = YELLOW
    r0 = 12
    wb2["A7"] = "Vmax_B (m³)"
    wb2["B7"] = f"=MAX(G{r0}:G{r0+n-1})"
    wb2["B7"].fill = GREEN
    wb2["B7"].number_format = "0.0"
    wb2["A8"] = "Hmax_B (m)"
    wb2["B8"] = "=IF(B5>0,B7/B5,0)"
    wb2["B8"].fill = BLUE
    wb2["B8"].number_format = "0.00"

    # Named ranges for interpolation (sheet-local absolute refs)
    hw_rng = f"Courbe_QH_900!$A${first_q}:$A${last_q}"
    q_rng = f"Courbe_QH_900!$E${first_q}:$E${last_q}"

    def q_from_h_formula(h_cell: str) -> str:
        # Linear interp between MATCH(...,1) and next row; clamp at ends
        return (
            f'IF({h_cell}<=0,0,'
            f'IF({h_cell}>=INDEX({hw_rng},ROWS({hw_rng})),INDEX({q_rng},ROWS({q_rng})),'
            f'LET('
            f'i,MATCH({h_cell},{hw_rng},1),'
            f'h1,INDEX({hw_rng},i),h2,INDEX({hw_rng},i+1),'
            f'q1,INDEX({q_rng},i),q2,INDEX({q_rng},i+1),'
            f'q1+({h_cell}-h1)/(h2-h1)*(q2-q1))))'
        )

    # LibreOffice-friendly version without LET (nested INDEX/MATCH)
    def q_from_h_classic(h_cell: str) -> str:
        m = f"MATCH({h_cell},{hw_rng},1)"
        return (
            f'IF({h_cell}<=0,0,'
            f'IF({h_cell}>=INDEX({hw_rng},ROWS({hw_rng})),INDEX({q_rng},ROWS({q_rng})),'
            f'INDEX({q_rng},{m})+'
            f'({h_cell}-INDEX({hw_rng},{m}))/'
            f'(INDEX({hw_rng},{m}+1)-INDEX({hw_rng},{m}))*'
            f'(INDEX({q_rng},{m}+1)-INDEX({q_rng},{m}))))'
        )

    hdr_b = ["t (min)", "Qin", "H (m)", "Q_courbe", "Qout", "Δt (s)", "V (m³)"]
    for j, h in enumerate(hdr_b, start=1):
        wb2.cell(11, j, h)
    style_header(wb2, 11, 7)

    for i in range(n):
        r = r0 + i
        wb2.cell(r, 1, f"=Hydrogramme!A{8+i}")
        wb2.cell(r, 2, f"=Hydrogramme!C{8+i}")
        if i == 0:
            wb2.cell(r, 3, 0)
            wb2.cell(r, 4, 0)
            wb2.cell(r, 5, f"=MIN(B{r},$B$6)")
            wb2.cell(r, 6, 0)
            wb2.cell(r, 7, 0)
        else:
            p = r - 1
            wb2.cell(r, 3, f"=IF($B$5>0,G{p}/$B$5,0)")
            wb2.cell(r, 4, f"={q_from_h_classic(f'C{r}')}")
            wb2.cell(r, 5, f"=IF(G{p}<=0.01,MIN(0.5*(B{p}+B{r}),$B$6),D{r})")
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

    # ---------- Stage_Storage (levé → V(WSE) → WSEmax) ----------
    wss = wb.create_sheet("Stage_Storage")
    wss["A1"] = "Stage–storage du levé — V = f(WSE) → lire le niveau max"
    wss["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wss["A2"] = (
        "PROCÉDURE (dans CE fichier): "
        "1) Routage → Vmax sur Parametres (Calcul_A ou B). "
        "2) Cette feuille calcule V cumulé vs NSE/WSE à partir des surfaces du levé (jaune). "
        "3) Parametres!B30 interpolates Vmax → WSEmax. "
        "Remplacez les surfaces jaunes par vos polygones; 543 m² @ 37.28 et 1932 m² @ 39.5 sont vos mesures."
    )
    wss.merge_cells("A2:G4")
    wss["A2"].alignment = Alignment(wrap_text=True, vertical="top")

    wss["A6"] = "Formule d'un pas"
    wss["A6"].font = Font(bold=True)
    wss["A7"] = "V_pas (m³) = (A_basse + A_haute) / 2 × (WSE_haute − WSE_basse)"
    wss["A7"].fill = GREEN
    wss.merge_cells("A7:F7")
    wss["A8"] = "V_cumulatif = somme des V_pas depuis le radier"
    wss.merge_cells("A8:F8")

    hdr = [
        "WSE / NSE (m)",
        "Surface A (m²) ← ÉDITER",
        "ΔWSE (m)",
        "V_pas (m³)",
        "V_cumulatif (m³)",
        "Rôle",
    ]
    for j, h in enumerate(hdr, start=1):
        wss.cell(10, j, h)
    style_header(wss, 10, 6)

    stages = [
        (34.88, 0, "Radier Ø900 — départ"),
        (35.50, 80, "Placeholder — remplacer par levé"),
        (36.00, 180, "Placeholder — remplacer par levé"),
        (36.50, 320, "Placeholder — remplacer par levé"),
        (37.00, 480, "Placeholder — remplacer par levé"),
        (37.28, 543, "LIMITE PATRON (+1.5 m crown) — votre levé"),
        (37.50, 700, "Placeholder — remplacer par levé"),
        (39.50, 1932, "Votre levé 1932 m² — niveau optionnel plus haut"),
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

    wss["A21"] = "Vmax (depuis Calcul_A)"
    wss["B21"] = "=Parametres!B27"
    wss["B21"].fill = GREEN
    wss["B21"].number_format = "0"
    wss["A22"] = "WSEmax correspondant (m)"
    wss["B22"] = "=Parametres!B30"
    wss["B22"].fill = GREEN
    wss["A23"] = "V disponible à 37.28 m (m³)"
    wss["B23"] = "=E16"
    wss["B23"].fill = BLUE
    wss["B23"].number_format = "0"
    wss["C23"] = "Si Vmax > cette valeur → le niveau dépasse la limite patron"

    wss["A25"] = "Comment lire le résultat"
    wss["A25"].font = Font(bold=True)
    wss["A26"] = (
        "Exemple: si Vmax = 5609 m³ et V(37.28)≈558 m³, alors WSEmax est au-dessus de 37.28 m "
        "(la table ira vers 39.5 m ou 'Hors table'). "
        "Affinez en entrant les vraies surfaces aux cotes intermédiaires (jaune)."
    )
    wss.merge_cells("A26:F28")
    wss["A26"].alignment = Alignment(wrap_text=True)

    ch = LineChart()
    ch.title = "V cumulé vs WSE (levé)"
    ch.y_axis.title = "V (m³)"
    ch.x_axis.title = "WSE (m)"
    ch.add_data(Reference(wss, min_col=5, min_row=10, max_row=18), titles_from_data=True)
    ch.set_categories(Reference(wss, min_col=1, min_row=11, max_row=18))
    wss.add_chart(ch, "H6")

    for col, w in zip("ABCDEF", [14, 22, 12, 12, 16, 55]):
        wss.column_dimensions[col].width = w

    # ---------- Fichiers liés ----------
    wf = wb.create_sheet("Fichiers_lies")
    wf["A1"] = "Où sont les fichiers HY-8 / capacité ?"
    wf["A1"].font = Font(bold=True, size=13, color="0F5C5C")
    files_txt = [
        "",
        "Ce classeur (rétention Ø900) :",
        "  engineering/drainage-design/retention_volume/Volume_Retention_Ponceau_900.xlsx",
        "",
        "Courbe Q=f(H) FHWA pour CE Ø900 : feuille Courbe_QH_900 (ci-dessus).",
        "",
        "Ancien Excel « type HY-8 / inlet-outlet » (autre projet / Ste-Thérèse) :",
        "  engineering/drainage-design/Ponceau_Capacite_Inlet_Outlet.xlsx",
        "  Branche git: cursor/culvert-excel-capacity-model-d87f",
        "",
        "Modèle composé ponceau Ø1050 + fossé (FHWA + remblai) — PAS le Ø900 de rétention :",
        "  engineering/drainage-design/ponceau_fosse_model/Ponceau_Fosse_Modele_Hydraulique.xlsx",
        "  Branche git: cursor/ponceau-fosse-hydraulic-model-d87f",
        "",
        "HEC-RAS : pas de projet .ras/.hdf pour ce Ø900. Un DEM Ste-Thérèse est dans",
        "  engineering/hec-ras-data/ (données topo seulement).",
        "",
        "Donc: on n'avait pas perdu un HY-8 pour ce bassin Ø900 — on avait des outils",
        "similaires pour d'autres sites. La courbe de CE classeur remplace ça pour le Ø900.",
    ]
    for i, line in enumerate(files_txt, start=2):
        wf.cell(i, 1, line)
    wf.column_dimensions["A"].width = 100

    # ---------- Methode ----------
    wm = wb.create_sheet("Methode")
    wm["A1"] = "Méthode — volume de rétention"
    wm["A1"].font = Font(bold=True, size=13)
    lines = [
        "",
        "1. Hydrogramme Qin(t) à l'entrée de la zone de rétention.",
        "2. Débit sortant contrôlé par le Ø900 (en série avant le Ø1200).",
        "3. Capacité Ø900 — deux niveaux:",
        "   A) Q_plein Manning (n=0.013) ≈ 1.668 m³/s → Méthode A (constant).",
        "   B) Courbe Q=f(H) FHWA HDS-5 (inlet + outlet) → feuille Courbe_QH_900 + Calcul_B.",
        "4. Méthode A: Qout = constante = Q_plein (jaune Parametres). Bon pour 1re estimation.",
        "5. Méthode B: Qout lu sur la courbe selon H=V/Aire (charge amont).",
        "6. Sur ce Ø900 (L/D≈56), le calcul FHWA indique surtout un contrôle outlet.",
        "7. Le Ø1200 est aval: n'augmente pas la sortie de la rétention.",
        "",
        "8. Niveau d'eau max: Stage_Storage (surfaces levé) + Parametres!B30 = WSEmax.",
        "",
        "Fichiers liés / anciens Excel: voir feuille Fichiers_lies.",
    ]
    for i, line in enumerate(lines, start=2):
        wm.cell(i, 1, line)
    wm.column_dimensions["A"].width = 110

    # Link results from Calcul_B on Parametres (below Notes block)
    ws["A50"] = "Vmax_B courbe FHWA (m³)"
    ws["B50"] = "=Calcul_B!B7"
    ws["B50"].fill = GREEN
    ws["B50"].number_format = "0"
    ws["C50"] = "Routage avec Q=f(H) — dépend de Aire_bassin (B24)"
    ws["A51"] = "WSEmax (rappel)"
    ws["B51"] = "=B30"
    ws["B51"].fill = GREEN
    ws["C51"] = "Même valeur que B30 — niveau max depuis levé Stage_Storage"

    wb.save(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path}")
