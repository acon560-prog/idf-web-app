#!/usr/bin/env python3
"""
Build Excel (TWO ZONES): Zone 1 Ø1500→Ø900 + Zone 2 Ø900→Ø1200.

Preserves the original single-pond workbook separately:
  Volume_Retention_Ponceau_900.xlsx  (build_retention_excel.py)

This script writes a NEW file with split stage-storage and Aval routing.

System (series):
  Ø1500 (in) → storage zone → Ø900 (control) → Ø1200 (downstream) → outlet

Method A: constant outlet capacity Qout = Qcap_900 (default 1.77 m³/s)
  V(t) = integral max(Qin - Qout, 0) dt   [trapezoidal]
  Vmax = max cumulative storage (storage cannot go negative)

Method B (optional): Qout = f(H) rating for Ø900, with simple level-pool
  using an assumed constant pond area (editable).

Method C (composite): Qout = Q_900(WSE) + Q_overflow(WSE)
  Overflow = trapezoidal open channel above culvert crown (crest).
  Storage V = V_pond(WSE) [survey] + V_ditch(WSE) [trapezoid × L].
"""

from __future__ import annotations

import math
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HERE = Path(__file__).resolve().parent
OUT = HERE / "Volume_Retention_Deux_Zones_1500_900_1200.xlsx"

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

# Method C — overflow ditch above Ø900 crown (user inputs)
CROWN_900 = Z_US_900 + D_900_M  # 35.78 m = crest
OVERFLOW_B = 2.0  # m bottom width at crown
OVERFLOW_N = 0.035
OVERFLOW_Z = 2.0  # H:V side slope (z=2 → 2H:1V)
OVERFLOW_S = 0.0085  # ≈ pipe bed slope (user correction; was 0.085 by mistake)
OVERFLOW_L = 50.1  # m length for V_ditch and channel reach

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


# Zone 1 = Ø1500 → Ø900 (amont). Zone 2 = Ø900 → Ø1200 (aval).
# WSE + Surface are yellow editable — correct from AutoCAD as needed.
STAGES_AMONT = [
    (34.88, 0, "Fond Zone 1 / radier amont Ø900"),
    (35.50, 56, "Levé Zone 1 — éditer si AutoCAD diffère"),
    (36.01, 210, "Levé Zone 1"),
    (36.50, 380, "Levé Zone 1"),
    (37.00, 400, "Levé Zone 1"),
    (37.28, 500, "LIMITE PATRON Zone 1 (+1.5 m crown)"),
    (37.40, 860, "Levé Zone 1"),
    (40.00, 2100, "Sommet table Zone 1"),
]
STAGES_AVAL = [
    (34.88, 0, "Fond Zone 2 (même grille WSE — éditer)"),
    (35.50, 60, "Levé Zone 2 — éditer si AutoCAD diffère"),
    (36.01, 219, "Levé Zone 2"),
    (36.50, 150, "Levé Zone 2 (A↓ — vérifier plan)"),
    (37.00, 340, "Levé Zone 2"),
    (37.28, 1700, "Levé Zone 2 @ limite patron"),
    (37.40, 1460, "Levé Zone 2 (A↓ — vérifier plan)"),
    (40.00, 1632, "Sommet table Zone 2"),
]


def add_stage_storage_sheet(
    wb: Workbook,
    title: str,
    heading: str,
    blurb: str,
    stages: list[tuple[float, float, str]],
    chart_title: str,
) -> None:
    """Editable WSE + Surface (yellow); ΔWSE / V_pas / V_cumul are live formulas."""
    wss = wb.create_sheet(title)
    wss["A1"] = heading
    wss["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wss["A2"] = blurb
    wss.merge_cells("A2:G4")
    wss["A2"].alignment = Alignment(wrap_text=True, vertical="top")

    wss["A6"] = "Formule d'un pas (aires moyennes)"
    wss["A6"].font = Font(bold=True)
    wss["A7"] = "V_pas (m³) = (A_basse + A_haute) / 2 × (WSE_haute − WSE_basse)"
    wss["A7"].fill = GREEN
    wss.merge_cells("A7:F7")
    wss["A8"] = "V_cumulatif = somme des V_pas depuis le fond de zone. Jaune = éditer (AutoCAD)."
    wss.merge_cells("A8:F8")

    hdr = [
        "WSE / NSE (m) ← ÉDITER",
        "Surface A (m²) ← ÉDITER",
        "ΔWSE (m)",
        "V_pas (m³)",
        "V_cumulatif (m³)",
        "Rôle",
    ]
    for j, h in enumerate(hdr, start=1):
        wss.cell(10, j, h)
    style_header(wss, 10, 6)

    for i, (wse, area, role) in enumerate(stages):
        r = 11 + i
        wss.cell(r, 1, wse).number_format = "0.00"
        wss.cell(r, 1).fill = YELLOW
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
                if c not in (1, 2):
                    wss.cell(r, c).fill = ORANGE

    last = 10 + len(stages)
    wss["A21"] = "V @ 37.28 m (m³)"
    wss["B21"] = "=E16"
    wss["B21"].fill = BLUE
    wss["B21"].number_format = "0.0"
    wss["C21"] = "Ligne orange — limite patron typique"
    wss["A22"] = "V @ sommet table (m³)"
    wss["B22"] = f"=E{last}"
    wss["B22"].fill = BLUE
    wss["B22"].number_format = "0.0"

    ch = LineChart()
    ch.title = chart_title
    ch.y_axis.title = "V (m³)"
    ch.x_axis.title = "WSE (m)"
    ch.add_data(Reference(wss, min_col=5, min_row=10, max_row=last), titles_from_data=True)
    ch.set_categories(Reference(wss, min_col=1, min_row=11, max_row=last))
    wss.add_chart(ch, "H6")

    for col, w in zip("ABCDEF", [20, 22, 12, 12, 16, 48]):
        wss.column_dimensions[col].width = w


def build() -> Path:
    wb = Workbook()

    # ---------- Parametres ----------
    ws = wb.active
    ws.title = "Parametres"
    ws["A1"] = "Volume de rétention — DEUX ZONES (Ø1500→Ø900 + Ø900→Ø1200)"
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

    # --- Vitesses de référence (V = Q / A_plein) ---
    ws["A82"] = "Vitesses de référence — V = Q / A_plein (pleine section)"
    ws["A82"].font = Font(bold=True, size=12, color="0F5C5C")
    ws["A83"] = (
        "A_plein = π D²/4. V_eq = Q/A_plein. Si le tuyau est partiellement rempli, "
        "la vitesse réelle Q/A(h) est plus élevée pour le même Q — voir Courbe_QH_900 col. V. "
        "Critères typiques fossé/tuyau: souvent 0.6–3 ou 4 m/s selon municipalité (à confirmer)."
    )
    ws.merge_cells("A83:H84")
    ws["A83"].alignment = Alignment(wrap_text=True)
    for j, h in enumerate(
        ["Ouvrage", "D (m)", "A_plein (m²)", "Q ref (m³/s)", "V_eq (m/s)", "Source Q"],
        start=1,
    ):
        ws.cell(85, j, h)
    style_header(ws, 85, 6)
    # Ø1500 @ Qpointe
    ws["A86"] = "Ø1500 (entrée)"
    ws["B86"] = 1.50
    ws["C86"] = "=PI()*B86^2/4"
    ws["D86"] = "=Hydrogramme!B4"
    ws["E86"] = "=IF(C86<=0,0,D86/C86)"
    ws["F86"] = "Qpointe hydrogramme"
    # Ø900 @ Q_plein Parametres
    ws["A87"] = "Ø900 (contrôle)"
    ws["B87"] = 0.90
    ws["C87"] = "=PI()*B87^2/4"
    ws["D87"] = "=B18"
    ws["E87"] = "=IF(C87<=0,0,D87/C87)"
    ws["F87"] = "Q_plein Manning (B18)"
    # Ø1200 @ Q_plein
    ws["A88"] = "Ø1200 (aval)"
    ws["B88"] = 1.20
    ws["C88"] = "=PI()*B88^2/4"
    ws["D88"] = 4.93
    ws["E88"] = "=IF(C88<=0,0,D88/C88)"
    ws["F88"] = "Q_plein Ø1200 (édit. si besoin)"
    ws["D88"].fill = YELLOW
    for r in (86, 87, 88):
        for c in range(1, 7):
            ws.cell(r, c).border = THIN
        ws.cell(r, 2).number_format = "0.00"
        ws.cell(r, 3).number_format = "0.000"
        ws.cell(r, 4).number_format = "0.000"
        ws.cell(r, 5).number_format = "0.00"
        ws.cell(r, 5).fill = GREEN
    ws["A89"] = "V_Ø900 @ Qout Calcul_A (m/s)"
    ws["B89"] = "=IF(C87<=0,"",Calcul_A!C8/C87)"  # wait Calcul_A Qout is B2 constant - use that
    ws["B89"] = "=IF(C87<=0,0,Calcul_A!B2/C87)"
    ws["B89"].fill = GREEN
    ws["B89"].number_format = "0.00"
    ws["C89"] = "Qout constant Méthode A / A_plein Ø900"
    ws["A91"] = (
        "ATTENTION: des V >> 5–6 m/s ne sont PAS physiques. "
        "Souvent Q_overflow+Q_pipe divisé par A_tuyau, ou Q/A_fossé trop petit. "
        "Vitesses tuyau réalistes typ. ~1–4 m/s; lire Compose_900 (V_Ø900) et Courbe_QH_900."
    )
    ws.merge_cells("A91:H92")
    ws["A91"].alignment = Alignment(wrap_text=True)
    ws["A90"] = "V_Ø1200 @ Qout Calcul_Aval_A (m/s)"
    ws["B90"] = "=IF(C88<=0,0,Calcul_Aval_A!B5/C88)"
    ws["B90"].fill = GREEN
    ws["B90"].number_format = "0.00"
    ws["C90"] = "Qout Aval / A_plein Ø1200"

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
    ws["B14"].fill = YELLOW
    ws["B14"].border = THIN
    ws["B14"].number_format = "0.00"
    ws["A15"] = "S0 = (Zamont-Zaval)/L"
    ws["B15"] = "=(D6-E6)/F6"
    ws["B15"].fill = BLUE
    ws["B15"].number_format = "0.00000"
    ws["C15"] = "Formule live depuis tableau géométrie Ø900"
    ws["A16"] = "A = πD²/4 (m²)"
    ws["B16"] = "=PI()*B14^2/4"
    ws["B16"].fill = BLUE
    ws["B16"].number_format = "0.000"
    ws["A17"] = "R = D/4 (m)"
    ws["B17"] = "=B14/4"
    ws["B17"].fill = BLUE
    ws["B17"].number_format = "0.000"
    ws["A18"] = "Q_plein = (1/n)·A·R^(2/3)·√S0"
    ws["B18"] = "=(1/B13)*B16*(B17^(2/3))*SQRT(B15)"
    ws["B18"].fill = GREEN
    ws["B18"].border = THIN
    ws["B18"].number_format = "0.000"
    ws["C18"] = "m³/s — formule live (changez n ou géométrie → Q se met à jour)"
    ws["A19"] = "Q utilisé avant (m³/s)"
    ws["B19"] = QCAP_900_PRIOR
    ws["B19"].number_format = "0.00"
    ws["C19"] = "Ancienne valeur bureau (~6% plus haute; même méthode)"

    ws["A21"] = "Entrées de calcul rétention (jaune)"
    ws["A21"].font = Font(bold=True)
    ws["A22"] = "Qout_cap_900 (m³/s)"
    ws["B22"] = "=B18"
    ws["B22"].fill = YELLOW
    ws["B22"].border = THIN
    ws["B22"].number_format = "0.000"
    ws["C22"] = "Par défaut = Q_plein (B18). Écraser par 1.77 si besoin (ancien calcul)."
    ws["A23"] = "Facteur_securite (-)"
    ws["B23"] = 1.20
    ws["B23"].fill = YELLOW
    ws["B23"].border = THIN
    ws["B23"].number_format = "0.00"
    ws["C23"] = "Marge sur Vmax (ex. 1.20 = +20%)"
    ws["A24"] = "Aire_constante_B (m²) — PAS le levé"
    ws["B24"] = 2500
    ws["B24"].fill = YELLOW
    ws["B24"].border = THIN
    ws["B24"].number_format = "0"
    ws["C24"] = (
        "Raccourci Méthode B seulement: H≈V/B24 pour lire Q=f(H). "
        "Ce n'est PAS un 2e bassin. Levé Zone 1 = feuille SS_Amont; Zone 2 = SS_Aval."
    )

    ws["A25"] = "Inclure V_ditch trapèze? (1=oui, 0=levé seul)"
    ws["B25"] = 0
    ws["B25"].fill = YELLOW
    ws["B25"].border = THIN
    ws["B25"].number_format = "0"
    ws["C25"] = (
        "0 = recommandé si SS_Amont contient déjà le fossé (V=levé seul; Q_overflow garde b,z,L,n,S). "
        "1 = ajoute V_ditch = A_trapèze × L (ancien mode — risque de double volume)."
    )

    ws["A26"] = "Débordement Méthode C — fossé trapèze au-dessus du crown (jaune)"
    ws["A26"].font = Font(bold=True)
    ws["A27"] = "Crest = crown Ø900 (m)"
    ws["B27"] = CROWN_900
    ws["B27"].fill = YELLOW
    ws["B27"].border = THIN
    ws["B27"].number_format = "0.00"
    ws["C27"] = "34.88+0.90 — overflow starts when WSE >= crest"
    ws["A28"] = "b fond fossé (m)"
    ws["B28"] = OVERFLOW_B
    ws["B28"].fill = YELLOW
    ws["B28"].border = THIN
    ws["B28"].number_format = "0.00"
    ws["A29"] = "n fossé Manning (-)"
    ws["B29"] = OVERFLOW_N
    ws["B29"].fill = YELLOW
    ws["B29"].border = THIN
    ws["B29"].number_format = "0.000"
    ws["A30"] = "z pente talus (H:V)"
    ws["B30"] = OVERFLOW_Z
    ws["B30"].fill = YELLOW
    ws["B30"].border = THIN
    ws["B30"].number_format = "0.0"
    ws["C30"] = "z=2 → 2H:1V"
    ws["A31"] = "S pente fossé (-)"
    ws["B31"] = OVERFLOW_S
    ws["B31"].fill = YELLOW
    ws["B31"].border = THIN
    ws["B31"].number_format = "0.0000"
    ws["C31"] = "≈0.0085 (corrigé; pente type lit Ø900 — pas 0.085)"
    ws["A32"] = "L fossé (m)"
    ws["B32"] = OVERFLOW_L
    ws["B32"].fill = YELLOW
    ws["B32"].border = THIN
    ws["B32"].number_format = "0.0"
    ws["C32"] = "L pour Manning Q_overflow (et V_ditch seulement si B25=1)"
    # Two separate Method C ideas — do not mix Q and V on the same row
    ws["A33"] = "Qout_C (débit sortie)"
    ws["B33"] = "Q_900(WSE) + Q_overflow(WSE)"
    ws["C33"] = "Débit = pipe + fossé (Compose_900). Ceci n'est PAS un volume."
    ws["A34"] = "Stockage_C (volume)"
    ws["B34"] = '=IF(B25=1,"V_pond(levé)+V_ditch","V_pond(levé) seul")'
    ws["C34"] = "Piloté par B25 — pas de double comptage si le fossé est déjà dans SS_Amont"

    def wse_from_v(cell_ref: str, sheet: str = "SS_Amont") -> str:
        """Interpolate V → WSE on zone stage-storage V_cumul (E11:E18) → WSE (A11:A18)."""
        return (
            f'=IF({cell_ref}<={sheet}!E11,{sheet}!A11,'
            f'IF({cell_ref}>={sheet}!E18,"Hors table (>=40.0 m — étendre levé)",'
            f'INDEX({sheet}!$A$11:$A$18,MATCH({cell_ref},{sheet}!$E$11:$E$18,1))'
            f'+({cell_ref}-INDEX({sheet}!$E$11:$E$18,MATCH({cell_ref},{sheet}!$E$11:$E$18,1)))'
            f'/(INDEX({sheet}!$E$11:$E$18,MATCH({cell_ref},{sheet}!$E$11:$E$18,1)+1)'
            f'-INDEX({sheet}!$E$11:$E$18,MATCH({cell_ref},{sheet}!$E$11:$E$18,1)))'
            f'*(INDEX({sheet}!$A$11:$A$18,MATCH({cell_ref},{sheet}!$E$11:$E$18,1)+1)'
            f'-INDEX({sheet}!$A$11:$A$18,MATCH({cell_ref},{sheet}!$E$11:$E$18,1)))))'
        )

    ws["A35"] = "Résultats Méthode A — Qout constant (feuille Calcul_A)"
    ws["A35"].font = Font(bold=True)
    ws["A36"] = "Vmax_A (m³)"
    ws["B36"] = "=Calcul_A!B3"
    ws["B36"].fill = GREEN
    ws["B36"].number_format = "0"
    ws["C36"] = "Volume max stocké avec Qout fixe (Parametres B22)"
    ws["A37"] = "V_dimensionnement_A = Vmax_A × facteur (m³)"
    ws["B37"] = "=B36*B23"
    ws["B37"].fill = GREEN
    ws["B37"].number_format = "0"
    ws["A38"] = "Hmax approx_A (m) = Vmax_A / Aire"
    ws["B38"] = "=IF(B24>0,B36/B24,0)"
    ws["B38"].fill = BLUE
    ws["B38"].number_format = "0.00"
    ws["C38"] = "Estimation grossière si l'aire de bassin est constante (pas le levé)"

    ws["A39"] = "WSEmax_A depuis levé Zone 1 (m) — SS_Amont"
    ws["B39"] = wse_from_v("B36", "SS_Amont")
    ws["B39"].fill = GREEN
    ws["B39"].number_format = "0.00"
    ws["C39"] = (
        "Cote d'eau max pour Vmax_A: lecture sur SS_Amont (Ø1500→Ø900), pas Zone 2"
    )
    ws["A40"] = "HW max_A = WSEmax_A − radier Ø900 (m)"
    ws["B40"] = '=IF(ISNUMBER(B39),B39-34.88,"")'
    ws["B40"].fill = GREEN
    ws["B40"].number_format = "0.00"
    ws["C40"] = "Comparer à 2.40 m (limite patron = +1.5 m au-dessus du crown)"

    ws["A42"] = "Résultats Méthode B — Qout = f(H) FHWA pipe seul (feuille Calcul_B)"
    ws["A42"].font = Font(bold=True)
    ws["A43"] = "Vmax_B (m³)"
    ws["B43"] = "=Calcul_B!B7"
    ws["B43"].fill = GREEN
    ws["B43"].number_format = "0"
    ws["C43"] = "Volume max stocké avec Q lu sur Courbe_QH_900 (dépend de Aire B24)"
    ws["A44"] = "V_dimensionnement_B = Vmax_B × facteur (m³)"
    ws["B44"] = "=B43*B23"
    ws["B44"].fill = GREEN
    ws["B44"].number_format = "0"
    ws["A45"] = "WSEmax_B depuis levé Zone 1 (m) — SS_Amont"
    ws["B45"] = wse_from_v("B43", "SS_Amont")
    ws["B45"].fill = GREEN
    ws["B45"].number_format = "0.00"
    ws["C45"] = "Même lecture volume→cote que B39 (SS_Amont), avec Vmax_B"
    ws["A46"] = "HW max_B = WSEmax_B − radier Ø900 (m)"
    ws["B46"] = '=IF(ISNUMBER(B45),B45-34.88,"")'
    ws["B46"].fill = GREEN
    ws["B46"].number_format = "0.00"
    ws["C46"] = "Comparer à 2.40 m (limite patron)"

    ws["A48"] = "Résultats Méthode C — Ø900 + fossé trapèze (Compose_900 + Calcul_C)"
    ws["A48"].font = Font(bold=True)
    ws["A49"] = 'Vmax_C (m³) = max(V_total)'
    ws["B49"] = "=Calcul_C!B7"
    ws["B49"].fill = GREEN
    ws["B49"].number_format = "0"
    ws["C49"] = '=IF(B25=1,"V_pond+V_ditch (B25=1)","V_pond seul — levé SS_Amont (B25=0)")'
    ws["A50"] = "V_dimensionnement_C = Vmax_C × facteur (m³)"
    ws["B50"] = "=B49*B23"
    ws["B50"].fill = GREEN
    ws["B50"].number_format = "0"
    ws["A51"] = "WSEmax_C (m) — du routage Calcul_C"
    ws["B51"] = "=Calcul_C!B8"
    ws["B51"].fill = GREEN
    ws["B51"].number_format = "0.00"
    ws["C51"] = "Directement du niveau dans Calcul_C (V inclut le fossé)"
    ws["A52"] = "HW max_C = WSEmax_C − radier Ø900 (m)"
    ws["B52"] = '=IF(ISNUMBER(B51),B51-34.88,"")'
    ws["B52"].fill = GREEN
    ws["B52"].number_format = "0.00"
    ws["C52"] = "Comparer à 2.40 m (limite patron); overflow actif si WSE>crest"

    ws["A54"] = "Résultats Zone 2 — Ø900 → Ø1200 (SS_Aval + Calcul_Aval_A)"
    ws["A54"].font = Font(bold=True)
    ws["A55"] = "V @ 37.28 m Zone 2 (m³) — SS_Aval"
    ws["B55"] = "=SS_Aval!B21"
    ws["B55"].fill = BLUE
    ws["B55"].number_format = "0"
    ws["C55"] = "Volume levé Zone 2 à la cote patron"
    ws["A56"] = "Vmax_Aval_A (m³)"
    ws["B56"] = "=Calcul_Aval_A!B6"
    ws["B56"].fill = GREEN
    ws["B56"].number_format = "0"
    ws["C56"] = "Routage Aval: Qin≈Qcap Ø900; Qout=Q_plein Ø1200"
    ws["A57"] = "WSEmax_Aval_A (m) — SS_Aval"
    ws["B57"] = "=Calcul_Aval_A!B7"
    ws["B57"].fill = GREEN
    ws["B57"].number_format = "0.00"
    ws["C57"] = "Lecture volume→cote sur levé Zone 2"

    ws["A59"] = "Comment lire WSEmax (zones + méthodes)"
    ws["A59"].font = Font(bold=True)
    wse_help = [
        "1) Zone 1 (Ø1500→Ø900): A/B → Vmax puis WSEmax sur SS_Amont. Zone 2: SS_Aval + Calcul_Aval_A (B55–B57).",
        "2) C (Zone 1): Qout = Q_900+Q_overflow; V = SS_Amont (+V_ditch si B25=1); WSEmax_C = Calcul_C.",
        "3) Crest = crown = 35.78 m → au-dessus, le fossé trapèze ajoute débit et volume (Zone 1).",
        "4) Ne pas additionner Zone 1+2 dans un seul routage. Éditer WSE/Surface jaunes dans SS_Amont et SS_Aval.",
    ]
    for i, line in enumerate(wse_help, start=60):
        ws.cell(i, 1, line)
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=8)

    ws["A65"] = "Inlet control vs outlet control — qu'est-ce que ça veut dire?"
    ws["A65"].font = Font(bold=True)
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
    for i, line in enumerate(ic_oc, start=66):
        ws.cell(i, 1, line)
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=8)

    ws["A75"] = "Notes"
    ws["A75"].font = Font(bold=True)
    notes = [
        "• Méthode A: Qout fixe = Q_plein Manning Ø900 (n=0,013).",
        "• Méthode B: Qout = f(H) pipe seul (Courbe_QH_900) — résultats B43–B46.",
        "• Méthode C: Qout = Q_900 + Q_overflow; V_ditch via B25 (0=levé seul) — Compose_900 + Calcul_C (B49–B52).",
        "• Zone 2: SS_Aval + Calcul_Aval_A — résultats B55–B57.",
        "• SS_Amont / SS_Aval: WSE et Surface en jaune — corriger depuis AutoCAD; ΔWSE et V_pas se recalculent.",
        "• Vérifier que le radier amont Ø900 (34.88) est bien le fond de Zone 1.",
    ]
    for i, line in enumerate(notes, start=76):
        ws.cell(i, 1, line)
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=8)

    for col, w in zip("ABCDEFGH", [36, 14, 55, 16, 16, 14, 12, 26]):
        ws.column_dimensions[col].width = w

    # ---------- Hydrogramme (shape × editable Qpointe) ----------
    wh = wb.create_sheet("Hydrogramme")
    wh["A1"] = "Hydrogramme d'entrée (point Ø1500 / entrée rétention) — FORMULES LIVE"
    wh["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wh["A2"] = (
        "Qin(t) = ratio(t) × Qpointe. Changez Qpointe (jaune B4) : toute la colonne Qin et Calcul_A/B/C se mettent à jour. "
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
        "V_Ø900 (m/s)",
    ]
    for j, h in enumerate(cols, start=1):
        wa.cell(7, j, h)
    style_header(wa, 7, len(cols))
    A900 = "Parametres!$C$87"  # A_plein Ø900

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
        wa.cell(r, 10, f'=IF({A900}<=0,0,C{r}/{A900})').border = THIN
        wa.cell(r, 10).number_format = "0.00"
        wa.cell(r, 10).fill = GREEN

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

    for col in range(1, 11):
        wa.column_dimensions[get_column_letter(col)].width = 14 if col > 1 else 12
    wa.column_dimensions["D"].width = 20
    wa.column_dimensions["H"].width = 18
    wa.column_dimensions["I"].width = 14
    wa.column_dimensions["J"].width = 14
    wa["A4"] = "V_Ø900 = Qout / A_plein Ø900 (Parametres C87)"

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

    hdr_q = ["HW (m)", "WSE (m)", "Qinlet", "Qoutlet", "Q gouvernant", "Contrôle", "A_ecoul (m²)", "V_gouv (m/s)"]
    for j, h in enumerate(hdr_q, start=1):
        wq.cell(23, j, h)
    style_header(wq, 23, 8)

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
        # Flow area: circular segment if HW < D else A_full; V = Q_gouv / A
        ratio = f"MIN(0.999,MAX(1E-6,A{r}/{D}))"
        theta = f"2*ACOS(1-2*({ratio}))"
        aseg = f"(({D}/2)^2/2)*(({theta})-SIN({theta}))"
        a_full = f"(PI()*({D}/2)^2)"
        wq.cell(
            r,
            7,
            f'=IF(A{r}<=0,0,IF(A{r}<{D},{aseg},{a_full}))',
        ).number_format = "0.000"
        wq.cell(r, 7).border = THIN
        wq.cell(r, 8, f"=IF(G{r}<=0,0,E{r}/G{r})").number_format = "0.00"
        wq.cell(r, 8).border = THIN
        wq.cell(r, 8).fill = GREEN
    last_q = first_q + n_hw - 1

    # Highlight boss stage HW = 2.40 (1.5 above crown) if present: row 24+48 = 72
    boss_row = first_q + int(round(2.40 / 0.05))
    if first_q <= boss_row <= last_q:
        for c in range(1, 9):
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

    for col, w in zip("ABCDEFGH", [12, 12, 12, 12, 14, 12, 12, 12]):
        wq.column_dimensions[col].width = w
    wq.column_dimensions["A"].width = 10
    wq["A22"] = "V_gouv = Q_gouvernant / A_ecoul (segment circulaire si HW<D, sinon A_plein)"
    wq.column_dimensions["J"].width = 8

    first_q, last_q = 24, 84  # live Courbe_QH_900 table rows

    # ---------- Calcul_B : routage avec courbe FHWA ----------
    wb2 = wb.create_sheet("Calcul_B")
    wb2["A1"] = "Méthode B — routage avec Qout = f(H) depuis Courbe_QH_900 (FHWA)"
    wb2["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wb2["A2"] = (
        "H = V / Aire_constante (Parametres!B24) — raccourci, PAS le levé SS_Amont. "
        "Qout interpolé sur Courbe_QH_900!E (Q gouvernant). "
        "Si V≈0, Qout = MIN(Qin, Q_plein). ΔV = (Qin_moy - Qout)*Δt. "
        "Après routage, WSEmax_B réel est lu sur SS_Amont via Vmax_B (Parametres B45)."
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

    hdr_b = ["t (min)", "Qin", "H (m)", "Q_courbe", "Qout", "Δt (s)", "V (m³)", "V_Ø900 (m/s)"]
    for j, h in enumerate(hdr_b, start=1):
        wb2.cell(11, j, h)
    style_header(wb2, 11, 8)
    A900b = "Parametres!$C$87"

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
        wb2.cell(r, 8, f"=IF({A900b}<=0,0,E{r}/{A900b})")
        for c in range(1, 9):
            wb2.cell(r, c).border = THIN
            if c in (2, 3, 4, 5):
                wb2.cell(r, c).number_format = "0.000"
            if c in (6, 7):
                wb2.cell(r, c).number_format = "0.0"
            if c == 8:
                wb2.cell(r, c).number_format = "0.00"
        wb2.cell(r, 7).fill = GREEN
        wb2.cell(r, 8).fill = GREEN

    for col, w in zip("ABCDEFGH", [10, 10, 10, 12, 10, 10, 12, 12]):
        wb2.column_dimensions[col].width = w

    # ---------- Compose_900 : Q_900 + Q_overflow, V_pond + V_ditch ----------
    wc = wb.create_sheet("Compose_900")
    wc["A1"] = "Méthode C — courbe composée Ø900 + fossé trapèze (crest = crown)"
    wc["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wc["A2"] = (
        "Qout = Q_900(WSE) + Q_overflow(WSE). "
        "V_total = V_pond(SS_Amont) + (B25)*V_ditch. "
        "Qout = Q_900 + Q_overflow (trapèze Manning) toujours. "
        "B25=0 → pas de volume trapèze (levé seul). Paramètres = Parametres!B25–B32."
    )
    wc.merge_cells("A2:L3")
    wc["A2"].alignment = Alignment(wrap_text=True, vertical="top")

    wc["A5"] = "Paramètres (liés à Parametres)"
    wc["A5"].font = Font(bold=True)
    c_params = [
        (6, "Crest (m)", "=Parametres!B27", "0.00"),
        (7, "b (m)", "=Parametres!B28", "0.00"),
        (8, "n fossé", "=Parametres!B29", "0.000"),
        (9, "z (-)", "=Parametres!B30", "0.0"),
        (10, "S fossé", "=Parametres!B31", "0.000"),
        (11, "L fossé (m)", "=Parametres!B32", "0.0"),
        (12, "Zin Ø900 (m)", f"={Z_US_900}", "0.00"),
        (13, "Inclure V_ditch (0/1)", "=Parametres!B25", "0"),
    ]
    for row, label, val, fmt in c_params:
        wc.cell(row, 1, label)
        cell = wc.cell(row, 2, val)
        cell.fill = YELLOW
        cell.border = THIN
        cell.number_format = fmt

    Crest = "$B$6"
    b_ref = "$B$7"
    n_ov = "$B$8"
    z_ref = "$B$9"
    S_ov = "$B$10"
    L_ov = "$B$11"
    Zin_c = "$B$12"
    v_ditch_on = "$B$13"  # Parametres!B25

    # SS_Amont WSE→V_pond (Zone 1 only)
    ss_wse = "SS_Amont!$A$11:$A$18"
    ss_v = "SS_Amont!$E$11:$E$18"
    # Courbe_QH HW→Q
    hw_rng = f"Courbe_QH_900!$A${first_q}:$A${last_q}"
    q_rng = f"Courbe_QH_900!$E${first_q}:$E${last_q}"

    def v_pond_from_wse(wse_cell: str) -> str:
        m = f"MATCH({wse_cell},{ss_wse},1)"
        return (
            f'IF({wse_cell}<=INDEX({ss_wse},1),INDEX({ss_v},1),'
            f'IF({wse_cell}>=INDEX({ss_wse},ROWS({ss_wse})),INDEX({ss_v},ROWS({ss_v})),'
            f'INDEX({ss_v},{m})+'
            f'({wse_cell}-INDEX({ss_wse},{m}))/'
            f'(INDEX({ss_wse},{m}+1)-INDEX({ss_wse},{m}))*'
            f'(INDEX({ss_v},{m}+1)-INDEX({ss_v},{m}))))'
        )

    def q900_from_hw(hw_cell: str) -> str:
        m = f"MATCH({hw_cell},{hw_rng},1)"
        return (
            f'IF({hw_cell}<=0,0,'
            f'IF({hw_cell}>=INDEX({hw_rng},ROWS({hw_rng})),INDEX({q_rng},ROWS({q_rng})),'
            f'INDEX({q_rng},{m})+'
            f'({hw_cell}-INDEX({hw_rng},{m}))/'
            f'(INDEX({hw_rng},{m}+1)-INDEX({hw_rng},{m}))*'
            f'(INDEX({q_rng},{m}+1)-INDEX({q_rng},{m}))))'
        )

    hdr_c = [
        "WSE (m)",
        "HW (m)",
        "y_ov (m)",
        "A_ditch (m²)",
        "V_ditch (m³)",
        "V_pond (m³)",
        "V_total (m³)",
        "Q_900",
        "Q_overflow",
        "Qout",
        "Overflow?",
        "V_Ø900 (m/s)",
        "V_overflow (m/s)",
    ]
    for j, h in enumerate(hdr_c, start=1):
        wc.cell(14, j, h)
    style_header(wc, 14, 13)
    A900c = "Parametres!$C$87"

    # WSE from invert to 39.50 step 0.05
    wse0 = Z_US_900
    wse1 = 39.50
    step = 0.05
    n_comp = int(round((wse1 - wse0) / step)) + 1
    c0 = 15
    for i in range(n_comp):
        r = c0 + i
        wse_val = round(wse0 + i * step, 2)
        wc.cell(r, 1, wse_val).number_format = "0.00"
        wc.cell(r, 1).border = THIN
        wse = f"A{r}"
        wc.cell(r, 2, f"={wse}-{Zin_c}").number_format = "0.00"
        # y_ov
        wc.cell(r, 3, f"=MAX(0,{wse}-{Crest})").number_format = "0.00"
        y = f"C{r}"
        # A = (b + z*y)*y
        wc.cell(r, 4, f"=IF({y}<=0,0,({b_ref}+{z_ref}*{y})*{y})").number_format = "0.000"
        A = f"D{r}"
        # V_ditch credited only if switch B25/B13 = 1 (else 0 — levé seul)
        wc.cell(r, 5, f"=IF({v_ditch_on}=1,{A}*{L_ov},0)").number_format = "0.0"
        wc.cell(r, 6, f"={v_pond_from_wse(wse)}").number_format = "0.0"
        wc.cell(r, 7, f"=F{r}+E{r}").number_format = "0.0"
        wc.cell(r, 7).fill = GREEN
        hw = f"B{r}"
        wc.cell(r, 8, f"={q900_from_hw(hw)}").number_format = "0.000"
        # P = b + 2*y*SQRT(1+z^2); R=A/P; Q=(1/n)*A*R^(2/3)*SQRT(S)
        wc.cell(
            r,
            9,
            f"=IF({y}<=0,0,"
            f"IF({n_ov}<=0,0,"
            f"(1/{n_ov})*{A}*"
            f"IF(({b_ref}+2*{y}*SQRT(1+{z_ref}^2))<=0,0,"
            f"(({A}/({b_ref}+2*{y}*SQRT(1+{z_ref}^2)))^(2/3)))*"
            f"SQRT({S_ov})))",
        ).number_format = "0.000"
        wc.cell(r, 10, f"=H{r}+I{r}").number_format = "0.000"
        wc.cell(r, 10).fill = GREEN
        wc.cell(r, 11, f'=IF({y}>0,"oui","non")')
        # Velocities: pipe ~ Q_900/A_plein; overflow = Q_ov/A_ditch
        # V_pipe = Q_900 only / A_plein (NOT Qout total)
        wc.cell(r, 12, f"=IF({A900c}<=0,0,H{r}/{A900c})").number_format = "0.00"
        wc.cell(r, 12).fill = GREEN
        # V_overflow only if depth/area meaningful (avoid /tiny A → absurd m/s)
        wc.cell(
            r,
            13,
            f'=IF(OR({y}<0.05,{A}<0.05),"",I{r}/{A})',
        ).number_format = "0.00"
        wc.cell(r, 13).fill = GREEN
        for c in range(2, 14):
            wc.cell(r, c).border = THIN
        # highlight crest row
        if abs(wse_val - CROWN_900) < 1e-9:
            for c in range(1, 14):
                if c not in (7, 10, 12, 13):
                    wc.cell(r, c).fill = ORANGE
    c_last = c0 + n_comp - 1

    ch_c = LineChart()
    ch_c.title = "Qout composé vs WSE"
    ch_c.y_axis.title = "Q (m³/s)"
    ch_c.x_axis.title = "WSE (m)"
    ch_c.add_data(Reference(wc, min_col=10, min_row=14, max_row=c_last), titles_from_data=True)
    ch_c.add_data(Reference(wc, min_col=8, min_row=14, max_row=c_last), titles_from_data=True)
    ch_c.add_data(Reference(wc, min_col=9, min_row=14, max_row=c_last), titles_from_data=True)
    ch_c.set_categories(Reference(wc, min_col=1, min_row=c0, max_row=c_last))
    wc.add_chart(ch_c, "M5")

    for col, w in zip("ABCDEFGHIJKLM", [10, 10, 10, 12, 12, 12, 12, 10, 12, 10, 10, 12, 14]):
        wc.column_dimensions[col].width = w

    # ---------- Calcul_C : routage V_total + Qout composé ----------
    wc2 = wb.create_sheet("Calcul_C")
    wc2["A1"] = "Méthode C — routage Qout composé; V = V_total (B25 pilote V_ditch)"
    wc2["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wc2["A2"] = (
        "À chaque pas: WSE lu sur Compose_900!V_total → Qout sur Compose_900. "
        "V_total = V_pond + V_ditch seulement si Parametres!B25=1; sinon V=levé SS_Amont. "
        "Q_overflow reste actif (b,z,L,n,S). ΔV = (Qin_moy − Qout)×Δt."
    )
    wc2.merge_cells("A2:H3")
    wc2["A2"].alignment = Alignment(wrap_text=True)

    wc2["A5"] = "Q_plein réf. (m³/s)"
    wc2["B5"] = "=Parametres!B22"
    wc2["B5"].fill = YELLOW
    wc2["A6"] = "Crest (m)"
    wc2["B6"] = "=Parametres!B27"
    wc2["B6"].fill = YELLOW

    vtot_rng = f"Compose_900!$G${c0}:$G${c_last}"
    wse_rng = f"Compose_900!$A${c0}:$A${c_last}"
    qout_rng = f"Compose_900!$J${c0}:$J${c_last}"

    def wse_from_vtot(v_cell: str) -> str:
        m = f"MATCH({v_cell},{vtot_rng},1)"
        return (
            f'IF({v_cell}<=INDEX({vtot_rng},1),INDEX({wse_rng},1),'
            f'IF({v_cell}>=INDEX({vtot_rng},ROWS({vtot_rng})),INDEX({wse_rng},ROWS({wse_rng})),'
            f'INDEX({wse_rng},{m})+'
            f'({v_cell}-INDEX({vtot_rng},{m}))/'
            f'(INDEX({vtot_rng},{m}+1)-INDEX({vtot_rng},{m}))*'
            f'(INDEX({wse_rng},{m}+1)-INDEX({wse_rng},{m}))))'
        )

    def qout_from_wse(wse_cell: str) -> str:
        m = f"MATCH({wse_cell},{wse_rng},1)"
        return (
            f'IF({wse_cell}<=INDEX({wse_rng},1),INDEX({qout_rng},1),'
            f'IF({wse_cell}>=INDEX({wse_rng},ROWS({wse_rng})),INDEX({qout_rng},ROWS({qout_rng})),'
            f'INDEX({qout_rng},{m})+'
            f'({wse_cell}-INDEX({wse_rng},{m}))/'
            f'(INDEX({wse_rng},{m}+1)-INDEX({wse_rng},{m}))*'
            f'(INDEX({qout_rng},{m}+1)-INDEX({qout_rng},{m}))))'
        )

    r0c = 12
    wc2["A7"] = "Vmax_C (m³)"
    wc2["B7"] = f"=MAX(F{r0c}:F{r0c+n-1})"
    wc2["B7"].fill = GREEN
    wc2["B7"].number_format = "0.0"
    wc2["A8"] = "WSEmax_C (m)"
    wc2["B8"] = f"=MAX(C{r0c}:C{r0c+n-1})"
    wc2["B8"].fill = GREEN
    wc2["B8"].number_format = "0.00"
    wc2["A9"] = "Overflow atteint?"
    wc2["B9"] = f'=IF(B8>$B$6,"oui — WSE > crest","non — pipe seul")'

    hdr_cc = ["t (min)", "Qin", "WSE (m)", "Qout", "Δt (s)", "V (m³)", "Overflow?", "V_pipe_seul (m/s)"]
    for j, h in enumerate(hdr_cc, start=1):
        wc2.cell(11, j, h)
    style_header(wc2, 11, 8)
    A900cc = "Parametres!$C$87"

    for i in range(n):
        r = r0c + i
        wc2.cell(r, 1, f"=Hydrogramme!A{8+i}")
        wc2.cell(r, 2, f"=Hydrogramme!C{8+i}")
        if i == 0:
            wc2.cell(r, 3, f"={Z_US_900}")
            wc2.cell(r, 4, f"=MIN(B{r},$B$5)")
            wc2.cell(r, 5, 0)
            wc2.cell(r, 6, 0)
            wc2.cell(r, 7, "non")
        else:
            p = r - 1
            wc2.cell(r, 3, f"={wse_from_vtot(f'F{p}')}")
            wc2.cell(r, 4, f"=IF(F{p}<=0.01,MIN(0.5*(B{p}+B{r}),$B$5),{qout_from_wse(f'C{r}')})")
            wc2.cell(r, 5, f"=(A{r}-A{p})*60")
            wc2.cell(r, 6, f"=MAX(0,F{p}+(0.5*(B{p}+B{r})-D{r})*E{r})")
            wc2.cell(r, 7, f'=IF(C{r}>$B$6,"oui","non")')
        # Only meaningful when NO overflow (otherwise Qout includes fossé — use Compose_900)
        wc2.cell(
            r,
            8,
            f'=IF(OR({A900cc}<=0,C{r}>$B$6),"",D{r}/{A900cc})',
        )
        for c in range(1, 9):
            wc2.cell(r, c).border = THIN
            if c in (2, 3, 4):
                wc2.cell(r, c).number_format = "0.000"
            if c in (5, 6):
                wc2.cell(r, c).number_format = "0.0"
            if c == 8:
                wc2.cell(r, c).number_format = "0.00"
        wc2.cell(r, 6).fill = GREEN
        wc2.cell(r, 8).fill = GREEN

    wc2["A10"] = (
        "V_pipe_seul = Qout/A_plein Ø900 seulement si WSE≤crest (pas d'overflow). "
        "Si Overflow=oui → cellule vide: lire V_Ø900 et V_overflow sur Compose_900 (ne pas diviser Qout total par A_tuyau)."
    )
    for col, w in zip("ABCDEFGH", [10, 10, 10, 10, 10, 14, 12, 14]):
        wc2.column_dimensions[col].width = w

    # ---------- Stage-storage Zone 1 / Zone 2 (WSE + A editables) ----------
    add_stage_storage_sheet(
        wb,
        "SS_Amont",
        "Zone 1 — Stage–storage Ø1500 → Ø900 (amont)",
        (
            "Jaune = WSE et Surface éditables (corriger depuis AutoCAD). "
            "ΔWSE, V_pas, V_cumul = formules live (aires moyennes). "
            "Cette feuille alimente WSEmax_A/B et V_pond Méthode C. "
            "Parametres!B24 (2500 m²) n'est PAS ici — raccourci Méthode B seulement. "
            "Ne pas y mettre les surfaces de Zone 2."
        ),
        STAGES_AMONT,
        "Zone 1 — V cumulé vs WSE",
    )
    # Link Amont results summary onto SS_Amont
    wsa = wb["SS_Amont"]
    wsa["A24"] = "Vmax_A / WSEmax_A (Parametres)"
    wsa["B24"] = "=Parametres!B36"
    wsa["B24"].fill = GREEN
    wsa["B24"].number_format = "0"
    wsa["C24"] = "=Parametres!B39"
    wsa["A25"] = "Vmax_B / WSEmax_B (Parametres)"
    wsa["B25"] = "=Parametres!B43"
    wsa["B25"].fill = GREEN
    wsa["B25"].number_format = "0"
    wsa["C25"] = "=Parametres!B45"
    wsa["A26"] = "Vmax_C / WSEmax_C (Parametres)"
    wsa["B26"] = "=Parametres!B49"
    wsa["B26"].fill = GREEN
    wsa["B26"].number_format = "0"
    wsa["C26"] = "=Parametres!B51"
    wsa["D26"] = '=IF(Parametres!B25=1,"Vmax_C inclut V_ditch","Vmax_C = levé seul (B25=0)")'

    add_stage_storage_sheet(
        wb,
        "SS_Aval",
        "Zone 2 — Stage–storage Ø900 → Ø1200 (aval)",
        (
            "Jaune = WSE et Surface éditables (corriger depuis AutoCAD). "
            "ΔWSE, V_pas, V_cumul = formules live. "
            "Qin de cette zone = débit sortant du Ø900 (voir Calcul_Aval_A). "
            "Sortie contrôlée par Ø1200 (Q_plein ≈ 4.93 m³/s). "
            "Ne pas y mettre les surfaces de Zone 1."
        ),
        STAGES_AVAL,
        "Zone 2 — V cumulé vs WSE",
    )
    wsv = wb["SS_Aval"]
    wsv["A24"] = "Vmax_Aval_A / WSEmax (Parametres)"
    wsv["B24"] = "=Parametres!B56"
    wsv["B24"].fill = GREEN
    wsv["B24"].number_format = "0"
    wsv["C24"] = "=Parametres!B57"

    # Index sheet (keeps familiar name + side-by-side check)
    wix = wb.create_sheet("Stage_Storage")
    wix["A1"] = "Index levé — Zone 1 (SS_Amont) + Zone 2 (SS_Aval)"
    wix["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wix["A2"] = (
        "Éditez les surfaces dans SS_Amont et SS_Aval (pas ici). "
        "Ce tableau compare A1+A2 vs total pour détecter un double comptage. "
        "GIS export = option pour sortir des polygones d'eau depuis AutoCAD/Civil 3D; "
        "vous n'en avez pas besoin si vous tapez les aires à la main depuis le plan."
    )
    wix.merge_cells("A2:H3")
    wix["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    for j, h in enumerate(
        ["WSE (m)", "A_Zone1 (m²)", "A_Zone2 (m²)", "A1+A2 (m²)", "V1 (m³)", "V2 (m³)", "V1+V2 (m³)"],
        start=1,
    ):
        wix.cell(5, j, h)
    style_header(wix, 5, 7)
    for i in range(8):
        r = 6 + i
        src = 11 + i
        wix.cell(r, 1, f"=SS_Amont!A{src}").number_format = "0.00"
        wix.cell(r, 2, f"=SS_Amont!B{src}").number_format = "0"
        wix.cell(r, 3, f"=SS_Aval!B{src}").number_format = "0"
        wix.cell(r, 4, f"=B{r}+C{r}").number_format = "0"
        wix.cell(r, 4).fill = BLUE
        wix.cell(r, 5, f"=SS_Amont!E{src}").number_format = "0.0"
        wix.cell(r, 6, f"=SS_Aval!E{src}").number_format = "0.0"
        wix.cell(r, 7, f"=E{r}+F{r}").number_format = "0.0"
        wix.cell(r, 7).fill = GREEN
        for c in range(1, 8):
            wix.cell(r, c).border = THIN
    for col, w in zip("ABCDEFG", [12, 14, 14, 14, 12, 12, 12]):
        wix.column_dimensions[col].width = w

    # ---------- Calcul_Aval_A : Zone 2, Qout = Q_plein Ø1200 ----------
    wav = wb.create_sheet("Calcul_Aval_A")
    wav["A1"] = "Zone 2 — Méthode A: Qin = sortie Ø900; Qout = Q_plein Ø1200"
    wav["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wav["A2"] = (
        "Qin_aval ≈ débit livré par le Ø900 (Calcul_A colonne C = Qcap Ø900 quand le bassin amont stocke). "
        "Qout_aval = Parametres capacité Ø1200. Stockage sur SS_Aval. "
        "Souvent Vmax_Aval faible si Q_1200 ≫ Q_900."
    )
    wav.merge_cells("A2:I3")
    wav["A2"].alignment = Alignment(wrap_text=True)
    wav["A5"] = "Qout_Aval (m³/s)"
    wav["B5"] = f"={QCAP_1200}"
    wav["B5"].fill = YELLOW
    wav["B5"].number_format = "0.00"
    wav["C5"] = "Par défaut Q_plein Ø1200 — éditable"
    wav["A6"] = "Vmax_Aval_A (m³)"
    n_h = len(HYDRO)
    first_a = 8
    last_a = first_a + n_h - 1
    # Aval routing table starts at row 10
    first_av = 10
    last_av = first_av + n_h - 1
    wav["B6"] = f"=MAX(H{first_av}:H{last_av})"
    wav["B6"].fill = GREEN
    wav["B6"].number_format = "0.0"
    wav["A7"] = "WSEmax_Aval (m)"
    wav["B7"] = wse_from_v("B6", "SS_Aval")
    wav["B7"].fill = GREEN
    wav["B7"].number_format = "0.00"

    cols_av = [
        "t (min)",
        "Qin_aval (m³/s)",
        "Qout_aval (m³/s)",
        "Qin−Qout",
        "Δt (s)",
        "ΔVin (m³)",
        "ΔVout (m³)",
        "V stocké (m³)",
        "Stockage?",
        "V_livré_Ø900 (m/s)",
        "V_Ø1200 (m/s)",
    ]
    for j, h in enumerate(cols_av, start=1):
        wav.cell(9, j, h)
    style_header(wav, 9, len(cols_av))
    A900av = "Parametres!$C$87"
    A1200av = "Parametres!$C$88"

    for i in range(n_h):
        r = first_av + i
        ca = first_a + i  # Calcul_A row
        wav.cell(r, 1, f"=Calcul_A!A{ca}").border = THIN
        wav.cell(r, 1).number_format = "0.0"
        # Delivered to Zone 2 ≈ Ø900 outlet used in Calcul_A (constant Qcap while routing)
        wav.cell(r, 2, f"=Calcul_A!C{ca}").border = THIN
        wav.cell(r, 2).number_format = "0.000"
        wav.cell(r, 3, "=$B$5").border = THIN
        wav.cell(r, 3).number_format = "0.00"
        wav.cell(r, 4, f"=B{r}-C{r}").border = THIN
        wav.cell(r, 4).number_format = "0.000"
        if i == 0:
            for c in (5, 6, 7, 8):
                wav.cell(r, c, 0).border = THIN
        else:
            prev = r - 1
            wav.cell(r, 5, f"=(A{r}-A{prev})*60").border = THIN
            wav.cell(r, 5).number_format = "0.0"
            wav.cell(r, 6, f"=0.5*(B{prev}+B{r})*E{r}").border = THIN
            wav.cell(r, 6).number_format = "0.0"
            wav.cell(r, 7, f"=F{r}-(H{r}-H{prev})").border = THIN
            wav.cell(r, 7).number_format = "0.0"
            wav.cell(r, 8, f"=MAX(0,H{prev}+0.5*(D{prev}+D{r})*E{r})").border = THIN
            wav.cell(r, 8).number_format = "0.0"
        wav.cell(r, 8).fill = GREEN
        wav.cell(r, 9, f'=IF(H{r}>0.5,"oui","non")').border = THIN
        wav.cell(r, 10, f'=IF({A900av}<=0,0,B{r}/{A900av})').border = THIN
        wav.cell(r, 10).number_format = "0.00"
        wav.cell(r, 10).fill = GREEN
        wav.cell(r, 11, f'=IF({A1200av}<=0,0,C{r}/{A1200av})').border = THIN
        wav.cell(r, 11).number_format = "0.00"
        wav.cell(r, 11).fill = GREEN

    for col in range(1, 12):
        wav.column_dimensions[get_column_letter(col)].width = 14 if col > 1 else 12

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
        "3. Capacité Ø900 — trois niveaux:",
        "   A) Q_plein Manning (n=0.013) ≈ 1.668 m³/s → Méthode A (constant).",
        "   B) Courbe Q=f(H) FHWA HDS-5 (inlet + outlet) → feuille Courbe_QH_900 + Calcul_B.",
        "   C) Qout = Q_900 + Q_overflow; V = V_pond (+ V_ditch si B25=1) → Compose_900 + Calcul_C.",
        "4. Méthode A: Qout = constante = Q_plein (jaune Parametres). Bon pour 1re estimation.",
        "5. Méthode B: Qout lu sur la courbe selon H=V/Aire (charge amont), pipe seul.",
        "6. Méthode C: crest = crown; fossé trapèze (b,n,z,S,L) au-dessus; stockage levé + fossé.",
        "7. Sur ce Ø900 (L/D≈56), le calcul FHWA indique surtout un contrôle outlet.",
        "8. Le Ø1200 est aval: n'augmente pas la sortie de la rétention.",
        "",
        "9. Niveau d'eau max Zone 1: A/B via SS_Amont; C via Calcul_C. Zone 2: SS_Aval + Calcul_Aval_A (B55–B57).",
        "",
        "Fichiers liés / anciens Excel: voir feuille Fichiers_lies.",
    ]
    for i, line in enumerate(lines, start=2):
        wm.cell(i, 1, line)
    wm.column_dimensions["A"].width = 110

    wb.save(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path}")
