#!/usr/bin/env python3
"""
1787 GC — modèle hybride pluvial:
  Bloc A = conduites + puisards/regards (structure type ADAPTE / Saint-Hubert)
  Bloc B = tranchées drainantes (gazon) → outlet = puisard → Bloc A

Jaune = saisie; Vert = calculé; Bleu = formule intermédiaire.
"""
from __future__ import annotations

import math
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HERE = Path(__file__).resolve().parent
OUT = HERE / "Reseau_pluvial_1787_GC_hybride.xlsx"

YELLOW = PatternFill("solid", fgColor="FFF59D")
GREEN = PatternFill("solid", fgColor="C8E6C9")
BLUE = PatternFill("solid", fgColor="BBDEFB")
ORANGE = PatternFill("solid", fgColor="FFE0B2")
HEADER_FILL = PatternFill("solid", fgColor="0F5C5C")
HEADER = Font(bold=True, color="FFFFFF")
THIN = Border(
    left=Side(style="thin", color="CBD5E1"),
    right=Side(style="thin", color="CBD5E1"),
    top=Side(style="thin", color="CBD5E1"),
    bottom=Side(style="thin", color="CBD5E1"),
)

# Placeholder IDF (1/25 ans style — à remplacer par IDF locale 1787)
IDF = {
    "1/2": (603.83, 6.2, 0.794),
    "1/5": (509.21, 3.7, 0.683),
    "1/10": (508.07, 2.9, 0.644),
    "1/25": (515.88, 2.1, 0.607),
    "1/50": (548.6, 1.9, 0.595),
    "1/100": (569.21, 1.6, 0.579),
}

# Surfaces lues sur croquis 1787 (m²) — jaunes, à valider
ZONES = [
    ("Z-BAT", "Bâtiment proposé RDC", 2434.75, 0.95, "toiture"),
    ("Z-P1", "Pavage / stationnement (SUP croquis)", 851.9, 0.90, "pavage"),
    ("Z-P2", "Pavage / aire (SUP croquis)", 882.5, 0.90, "pavage"),
    ("Z-P3", "Pavage / aire (SUP croquis)", 736.8, 0.90, "pavage"),
    ("Z-G1", "Gazon / bande (SUP croquis)", 425.0, 0.25, "gazon→tranchée"),
    ("Z-G2", "Gazon / bande (SUP croquis)", 378.2, 0.25, "gazon→tranchée"),
    ("Z-G3", "Gazon / bande (SUP croquis)", 330.3, 0.25, "gazon→tranchée"),
    ("Z-G4", "Gazon / bande (SUP croquis)", 326.1, 0.25, "gazon→tranchée"),
    ("Z-A1", "Autre / annexe (SUP croquis)", 123.0, 0.60, "à classer"),
    ("Z-A2", "Autre / annexe (SUP croquis)", 98.2, 0.60, "à classer"),
    ("Z-A3", "Autre / annexe (SUP croquis)", 73.3, 0.60, "à classer"),
]

# Tranchées proposées (placeholders — lier aux puisards du plan)
TRANCHEES = [
    # id, amont_label, aval_puisard, L_m, b_m, H_m, n_open, porosite, underdrain_mm, s, zones
    ("T-NORD", "Limite nord / gazon", "RP-N1", 45.0, 0.60, 0.70, 0.028, 0.35, 200, 0.005, "Z-G1"),
    ("T-SUD", "Gazon sud / bande", "RP-S1", 55.0, 0.60, 0.70, 0.028, 0.35, 200, 0.005, "Z-G2+Z-G3"),
    ("T-EST", "Bande est gazon", "RP-E1", 35.0, 0.50, 0.70, 0.028, 0.35, 200, 0.005, "Z-G4"),
]

# Pipe chain placeholders (remplacer par topologie réelle 1787)
# amont, aval, DA_ha, C, s, dnom_mm, L_m, sol_am, sol_av, rad_am, rad_av
PIPES = [
    ("RP-N1", "RP-01", 0.05, 0.55, 0.005, 300, 25.0, 24.50, 24.40, 22.50, 22.38),
    ("RP-S1", "RP-01", 0.08, 0.50, 0.005, 300, 30.0, 24.40, 24.40, 22.45, 22.38),
    ("RP-E1", "RP-01", 0.04, 0.45, 0.005, 250, 20.0, 24.45, 24.40, 22.55, 22.38),
    ("RP-01", "RPP-02", 0.10, 0.70, 0.005, 375, 35.0, 24.40, 24.33, 22.38, 22.22),
    ("RPP-02", "RS-01", 0.05, 0.80, 0.008, 375, 40.0, 24.33, 24.60, 22.22, 20.14),
    ("RS-01", "EXUTOIRE", 0.02, 0.85, 0.010, 375, 15.0, 24.60, 24.50, 20.14, 19.99),
]


def style_header(ws, row: int, ncols: int) -> None:
    for c in range(1, ncols + 1):
        cell = ws.cell(row, c)
        cell.font = HEADER
        cell.fill = HEADER_FILL
        cell.border = THIN
        cell.alignment = Alignment(wrap_text=True, vertical="center")


def yellow(cell, fmt: str | None = None) -> None:
    cell.fill = YELLOW
    cell.border = THIN
    if fmt:
        cell.number_format = fmt


def green(cell, fmt: str | None = None) -> None:
    cell.fill = GREEN
    cell.border = THIN
    if fmt:
        cell.number_format = fmt


def build() -> Path:
    wb = Workbook()

    # ========== Guide ==========
    wg = wb.active
    wg.title = "Guide"
    wg["A1"] = "1787 GC — Réseau pluvial hybride (conduites + tranchées drainantes)"
    wg["A1"].font = Font(bold=True, size=14, color="0F5C5C")
    lines = [
        "",
        "Objectif: reprendre la structure type Calcul_reseau (ADAPTE / Saint-Hubert) et y ajouter",
        "des tranchées drainantes le long des gazons, comme sur le croquis 1787-GC-00.",
        "",
        "Onglets",
        "  1) Inputs — IDF, Manning, porosité, diamètres underdrain, critères Vmin/Vmax",
        "  2) Zones_tributaires — SUP du croquis (m²) + C + destination (pipe / tranchée)",
        "  3) Tranchees (Bloc B) — géométrie, stockage porosité, underdrain, Q → puisard",
        "  4) Calcul_reseau (Bloc A) — tronçons PIPE amont→aval (même colonnes que modèle précédent)",
        "  5) Temps_concentration — tc entrée + parcours",
        "  6) Resume — totaux volumes / checks",
        "",
        "Couleurs: Jaune = saisie | Vert = résultat | Bleu = formule intermédiaire | Orange = à vérifier sur plan",
        "",
        "Lien hydraulique",
        "  Tranchée → Noeud_aval (puisard) → ce même ID apparaît comme Amont dans Calcul_reseau.",
        "  Ne PAS mettre une tranchée comme un Ø dans dnom: utiliser l'onglet Tranchees.",
        "",
        "Croquis source (dans ce dossier): 1787-GC-00_Croquis_des_reseaux.pdf",
        "Placeholders RP-N1 / RP-S1 / RP-E1 = puisards d'arrivée tranchées — renommer selon plan final.",
        "",
        "Prochaines étapes",
        "  1) Remplacer IDs et L/pentes/radiers par le levé / profils 1787",
        "  2) Affecter chaque zone gazon à la bonne tranchée (colonne Destination)",
        "  3) Ajuster IDF locale (Inputs) et période de retour",
        "  4) Vérifier Qp > Qmax (colonne Check) et V dans [Vmin, Vmax]",
    ]
    for i, line in enumerate(lines, start=2):
        wg.cell(i, 1, line)
    wg.column_dimensions["A"].width = 110

    # ========== Inputs ==========
    wi = wb.create_sheet("Inputs")
    wi["A1"] = "INPUTS — paramètres hydrauliques 1787 GC"
    wi["A1"].font = Font(bold=True, size=13, color="0F5C5C")
    wi["A2"] = "Paramètre"
    wi["B2"] = "Valeur"
    wi["C2"] = "Unité"
    wi["D2"] = "Note"
    style_header(wi, 2, 4)

    inputs = [
        (3, "Periode_retour_code", 25, "-", "2 / 5 / 10 / 25 / 50 / 100 — pilote IDF"),
        (4, "n_pipe", 0.013, "-", "Manning conduites (béton typ.)"),
        (5, "n_trench_open", 0.028, "-", "Manning écoulement dans tranchée ouverte / media"),
        (6, "n_underdrain", 0.013, "-", "Manning underdrain perforé"),
        (7, "Trench_porosity", 0.35, "-", "Porosité utile stockage gravier"),
        (8, "Trench_default_b_m", 0.60, "m", "Largeur fond tranchée par défaut"),
        (9, "Trench_default_H_m", 0.70, "m", "Profondeur utile tranchée"),
        (10, "Underdrain_default_mm", 200, "mm", "Ø underdrain par défaut"),
        (11, "Vmin_mps", 0.60, "m/s", "Auto-curage pipes (indicatif)"),
        (12, "Vmax_mps", 3.00, "m/s", "Érosion / abrasion (indicatif)"),
        (13, "Fill_ratio_limit", 0.90, "-", "Qmax/Qp max acceptable"),
        (14, "C_roof", 0.95, "-", "Ruissellement toiture"),
        (15, "C_pave", 0.90, "-", "Ruissellement pavage"),
        (16, "C_grass", 0.25, "-", "Ruissellement gazon"),
        (17, "Safety_Q", 1.00, "-", "Facteur sur Q (1.0 = off)"),
    ]
    for r, name, val, unit, note in inputs:
        wi.cell(r, 1, name)
        yellow(wi.cell(r, 2, val), "0.000" if isinstance(val, float) and val < 10 else "0.00")
        wi.cell(r, 3, unit)
        wi.cell(r, 4, note)

    wi["A19"] = "Table IDF — I = A / (t + B)^C   (t en min, I en mm/h) — REMPLACER par IDF 1787"
    wi["A19"].font = Font(bold=True)
    for j, h in enumerate(["Récurrence", "A", "B", "C", "code"], start=1):
        wi.cell(20, j, h)
    style_header(wi, 20, 5)
    for i, (lab, (a, b, c)) in enumerate(IDF.items(), start=21):
        code = int(lab.split("/")[1])
        wi.cell(i, 1, lab)
        yellow(wi.cell(i, 2, a), "0.00")
        yellow(wi.cell(i, 3, b), "0.0")
        yellow(wi.cell(i, 4, c), "0.000")
        wi.cell(i, 5, code)

    # Live IDF coeffs from selected return period
    wi["A28"] = "A_actif"
    wi["B28"] = '=IFERROR(INDEX(B21:B26,MATCH(B3,E21:E26,0)),515.88)'
    green(wi["B28"], "0.00")
    wi["A29"] = "B_actif"
    wi["B29"] = '=IFERROR(INDEX(C21:C26,MATCH(B3,E21:E26,0)),2.1)'
    green(wi["B29"], "0.0")
    wi["A30"] = "C_actif"
    wi["B30"] = '=IFERROR(INDEX(D21:D26,MATCH(B3,E21:E26,0)),0.607)'
    green(wi["B30"], "0.000")

    for col, w in zip("ABCD", [28, 12, 10, 55]):
        wi.column_dimensions[col].width = w

    # ========== Zones ==========
    wz = wb.create_sheet("Zones_tributaires")
    wz["A1"] = "Zones tributaires — surfaces du croquis 1787 (à valider / réaffecter)"
    wz["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wz["A2"] = (
        "Destination: ID tranchée (T-NORD…) ou ID noeud pipe (RP-…). "
        "Aire_ha = SUP_m2/10000. Ces aires alimentent tc et/ou Q des éléments."
    )
    wz.merge_cells("A2:G2")
    hdr = ["Zone_ID", "Description", "SUP (m²)", "C (-)", "Aire (ha)", "Destination", "Note"]
    for j, h in enumerate(hdr, 1):
        wz.cell(4, j, h)
    style_header(wz, 4, 7)
    for i, (zid, desc, area, c, note) in enumerate(ZONES, start=5):
        wz.cell(i, 1, zid).border = THIN
        yellow(wz.cell(i, 2, desc))
        yellow(wz.cell(i, 3, area), "0.0")
        yellow(wz.cell(i, 4, c), "0.00")
        green(wz.cell(i, 5, f"=C{i}/10000"), "0.0000")
        dest = "T-NORD" if "gazon" in note else ("RP-01" if "pavage" in note or "toiture" in note else "à classer")
        if zid == "Z-G2" or zid == "Z-G3":
            dest = "T-SUD"
        if zid == "Z-G4":
            dest = "T-EST"
        if zid == "Z-G1":
            dest = "T-NORD"
        cell = wz.cell(i, 6, dest)
        cell.fill = ORANGE
        cell.border = THIN
        wz.cell(i, 7, note).border = THIN
    last_z = 4 + len(ZONES)
    wz.cell(last_z + 2, 1, "Total SUP (m²)")
    green(wz.cell(last_z + 2, 3, f"=SUM(C5:C{last_z})"), "0.0")
    wz.cell(last_z + 3, 1, "Total ha")
    green(wz.cell(last_z + 3, 5, f"=SUM(E5:E{last_z})"), "0.000")
    for col, w in zip("ABCDEFG", [10, 40, 12, 8, 10, 14, 22]):
        wz.column_dimensions[col].width = w

    # ========== Temps_concentration ==========
    wt = wb.create_sheet("Temps_concentration")
    wt["A1"] = "Temps de concentration (simplifié) — ajuster L overland / pentes"
    wt["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wt["A3"] = "tc_entrée_min (défaut)"
    yellow(wt.cell(3, 2, 7.0), "0.0")
    wt["C3"] = "minutes — Kirpich/FAA à raffiner si parcours connu"
    wt["A4"] = "Note: Calcul_reseau utilise tc cumulatif le long de la chaîne (tf pipes)."
    for col, w in zip("ABC", [22, 12, 55]):
        wt.column_dimensions[col].width = w

    # ========== Tranchees (Bloc B) ==========
    wtr = wb.create_sheet("Tranchees")
    wtr["A1"] = "Bloc B — Tranchées drainantes (gazon) → puisard"
    wtr["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wtr["A2"] = (
        "Capacité underdrain = Manning pleine section. "
        "Stockage = b × H × L × porosité. "
        "Q_indicatif zone = 0.00275 × A_ha × C × I(tc). "
        "Noeud_aval doit exister comme Amont dans Calcul_reseau."
    )
    wtr.merge_cells("A2:N2")
    wtr["A2"].alignment = Alignment(wrap_text=True)

    wtr["A4"] = "tc_ref (min)"
    wtr["B4"] = "=Temps_concentration!B3"
    green(wtr["B4"], "0.0")
    wtr["A5"] = "I_ref (mm/h)"
    wtr["B5"] = "=Inputs!B28/((B4+Inputs!B29)^Inputs!B30)"
    green(wtr["B5"], "0.00")

    th = [
        "Trench_ID",
        "Description",
        "Noeud_aval (puisard)",
        "L (m)",
        "b (m)",
        "H (m)",
        "n_open",
        "Porosité",
        "Underdrain Ø (mm)",
        "s (m/m)",
        "Zones (IDs)",
        "A_ha_aff",
        "C_moy",
        "Q_zone (m³/s)",
        "V_ud (m/s)",
        "Qp_ud (m³/s)",
        "Vol_stock (m³)",
        "Check Qp≥Q",
    ]
    for j, h in enumerate(th, 1):
        wtr.cell(7, j, h)
    style_header(wtr, 7, len(th))
    wtr.row_dimensions[7].height = 36

    # Helper: sum ha and weighted C from Zones where Destination = trench id
    # Using SUMIF on Zones sheet
    r0 = 8
    for i, row in enumerate(TRANCHEES):
        r = r0 + i
        tid, desc, outlet, L, b, H, n_o, por, ud, s, zones = row
        wtr.cell(r, 1, tid).border = THIN
        yellow(wtr.cell(r, 2, desc))
        cell = wtr.cell(r, 3, outlet)
        cell.fill = ORANGE
        cell.border = THIN
        yellow(wtr.cell(r, 4, L), "0.0")
        yellow(wtr.cell(r, 5, b), "0.00")
        yellow(wtr.cell(r, 6, H), "0.00")
        yellow(wtr.cell(r, 7, n_o), "0.000")
        yellow(wtr.cell(r, 8, por), "0.00")
        yellow(wtr.cell(r, 9, ud), "0")
        yellow(wtr.cell(r, 10, s), "0.0000")
        yellow(wtr.cell(r, 11, zones))
        # A_ha and C from Zones where F = trench id
        green(
            wtr.cell(r, 12, f'=SUMIF(Zones_tributaires!$F$5:$F$20,A{r},Zones_tributaires!$E$5:$E$20)'),
            "0.0000",
        )
        # Weighted C ≈ SUMPRODUCT / A ; if A=0 → Inputs grass C
        green(
            wtr.cell(
                r,
                13,
                f'=IF(L{r}<=0,Inputs!$B$16,'
                f'SUMPRODUCT((Zones_tributaires!$F$5:$F$20=A{r})*(Zones_tributaires!$E$5:$E$20)*(Zones_tributaires!$D$5:$D$20))/L{r})',
            ),
            "0.00",
        )
        green(
            wtr.cell(r, 14, f"=Inputs!$B$17*0.00275*L{r}*M{r}*$B$5"),
            "0.000",
        )
        # V underdrain full
        green(
            wtr.cell(
                r,
                15,
                f'=IF(OR(I{r}<=0,J{r}<=0),0,((I{r}/4000)^(2/3)*SQRT(J{r}))/Inputs!$B$6)',
            ),
            "0.00",
        )
        green(
            wtr.cell(r, 16, f"=O{r}*PI()*(I{r}/1000)^2/4"),
            "0.000",
        )
        green(wtr.cell(r, 17, f"=E{r}*F{r}*D{r}*H{r}"), "0.0")
        green(
            wtr.cell(r, 18, f'=IF(P{r}<=0,"—",IF(P{r}>=N{r},"OK","AUGMENTER Ø/s"))'),
        )

    last_t = r0 + len(TRANCHEES) - 1
    wtr.cell(last_t + 2, 1, "Total Vol_stock tranchées (m³)")
    green(wtr.cell(last_t + 2, 17, f"=SUM(Q{r0}:Q{last_t})"), "0.0")
    wtr.cell(last_t + 3, 1, "Total Q_zone (m³/s)")
    green(wtr.cell(last_t + 3, 14, f"=SUM(N{r0}:N{last_t})"), "0.000")

    wtr["A22"] = (
        "Note: si underdrain seul est trop juste, élargir b/H (stockage) ou Ø, "
        "ou admettre écoulement de surface dans la tranchée (n_open) — hors formule Qp_ud."
    )
    wtr.merge_cells("A22:R23")
    wtr["A22"].alignment = Alignment(wrap_text=True)

    for col in range(1, 19):
        wtr.column_dimensions[get_column_letter(col)].width = 12 if col > 3 else 18
    wtr.column_dimensions["B"].width = 28
    wtr.column_dimensions["K"].width = 16

    # ========== Calcul_reseau (Bloc A) ==========
    wc = wb.create_sheet("Calcul_reseau")
    wc["A1"] = "Bloc A — Calculs réseau d'égout pluvial (conduites + regards/puisards)"
    wc["A1"].font = Font(bold=True, size=13, color="0F5C5C")
    wc["A2"] = "Projet :"
    wc["B2"] = "1787 GC — hybride pipes + tranchées"
    yellow(wc["B2"])
    wc["A3"] = "No dossier :"
    yellow(wc.cell(3, 2, "1787"))
    wc["A4"] = "Date :"
    yellow(wc.cell(4, 2, "2026-11-03"))

    wc["F2"] = "Période de retour (ans) ="
    wc["G2"] = "=Inputs!B3"
    green(wc["G2"], "0")
    wc["F3"] = "n Manning ="
    wc["G3"] = "=Inputs!B4"
    green(wc["G3"], "0.000")
    wc["F4"] = "A,B,C IDF ="
    wc["G4"] = "=Inputs!B28"
    wc["H4"] = "=Inputs!B29"
    wc["I4"] = "=Inputs!B30"
    green(wc["G4"], "0.00")
    green(wc["H4"], "0.0")
    green(wc["I4"], "0.000")

    # Group headers (row 11-14) matching previous model
    wc["A11"] = "Calcul du débit"
    wc["A11"].font = Font(bold=True)
    wc["M11"] = "Calcul des caractéristiques de la conduite"
    wc["M11"].font = Font(bold=True)
    wc["S11"] = "Niveau du sol"
    wc["U11"] = "Hauteur de radier"
    wc["W11"] = "Couverture"
    wc["Y11"] = "Volume retenu"
    wc["AB11"] = "Vérif."

    headers = [
        (1, "Amont"),
        (2, "Liaison"),
        (3, "Aval"),
        (4, "tc (min)"),
        (5, "DA (ha)"),
        (6, "RT (-)"),
        (7, "DART (ha)"),
        (8, "A (ha)"),
        (9, "AR (ha)"),
        (10, "R (-)"),
        (11, "I (mm/h)"),
        (12, "Qmax (m³/s)"),
        (13, "s (m/m)"),
        (14, "dnom (mm)"),
        (15, "v (m/s)"),
        (16, "L (m)"),
        (17, "tf (min)"),
        (18, "Qp (m³/s)"),
        (19, "Sol amont (m)"),
        (20, "Sol aval (m)"),
        (21, "Rad_amont (m)"),
        (22, "Rad_aval (m)"),
        (23, "Cov_amont (m)"),
        (24, "Cov_aval (m)"),
        (25, "Vol_cond (m³)"),
        (26, "Dia_bouch (m)"),
        (27, "Vol_bouch (m³)"),
        (28, "Check Qp>Qmax"),
        (29, "Qin_tranchées (m³/s)"),
        (30, "Note"),
    ]
    for col, h in headers:
        wc.cell(14, col, h)
    style_header(wc, 14, 30)
    wc.row_dimensions[14].height = 40

    # Symbols row
    sym = {
        4: "tc",
        5: "DA",
        6: "RT",
        7: "DART",
        8: "A",
        9: "AR",
        10: "R",
        11: "I",
        12: "Qmax",
        13: "s",
        14: "dnom",
        15: "v",
        16: "L",
        17: "tf",
        18: "Qp",
    }
    for c, s in sym.items():
        wc.cell(15, c, s).border = THIN

    r0p = 16
    n_ref = "$G$3"
    a_idf, b_idf, c_idf = "$G$4", "$H$4", "$I$4"

    for i, (am, av, da, c_r, s, dnom, L, sol_a, sol_v, rad_a, rad_v) in enumerate(PIPES):
        r = r0p + i
        yellow(wc.cell(r, 1, am))
        wc.cell(r, 2, "@").border = THIN
        yellow(wc.cell(r, 3, av))

        if i == 0:
            green(wc.cell(r, 4, "=Temps_concentration!B3"), "0.00")
            green(wc.cell(r, 8, f"=E{r}"), "0.0000")
            green(wc.cell(r, 9, f"=G{r}"), "0.0000")
        else:
            p = r - 1
            green(wc.cell(r, 4, f"=MAX(Temps_concentration!B3,D{p}+Q{p})"), "0.00")
            green(wc.cell(r, 8, f"=H{p}+E{r}"), "0.0000")
            green(wc.cell(r, 9, f"=I{p}+G{r}"), "0.0000")

        yellow(wc.cell(r, 5, da), "0.0000")
        yellow(wc.cell(r, 6, c_r), "0.00")
        green(wc.cell(r, 7, f"=E{r}*F{r}"), "0.0000")
        green(wc.cell(r, 10, f"=IF(H{r}=0,0,I{r}/H{r})"), "0.00")
        green(
            wc.cell(r, 11, f"=IF(D{r}<=0,0,{a_idf}/((D{r}+{b_idf})^{c_idf}))"),
            "0.00",
        )
        # Qmax + optional trench inflow landing on this upstream node
        green(
            wc.cell(
                r,
                12,
                f"=Inputs!$B$17*0.00275*H{r}*J{r}*K{r}+AC{r}",
            ),
            "0.000",
        )
        yellow(wc.cell(r, 13, s), "0.0000")
        yellow(wc.cell(r, 14, dnom), "0")
        green(
            wc.cell(
                r,
                15,
                f'=IF(OR(N{r}<=0,M{r}<=0),0,((N{r}/4000)^(2/3)*SQRT(M{r}))/{n_ref})',
            ),
            "0.00",
        )
        yellow(wc.cell(r, 16, L), "0.00")
        green(wc.cell(r, 17, f"=IF(O{r}=0,0,P{r}/(O{r}*60))"), "0.00")
        green(wc.cell(r, 18, f"=O{r}*PI()*(N{r}/1000)^2/4"), "0.000")
        yellow(wc.cell(r, 19, sol_a), "0.000")
        yellow(wc.cell(r, 20, sol_v), "0.000")
        yellow(wc.cell(r, 21, rad_a), "0.000")
        yellow(wc.cell(r, 22, rad_v), "0.000")
        # Cover = sol - (radier + dnom/1000) approx to crown
        green(wc.cell(r, 23, f"=S{r}-(U{r}+N{r}/1000)"), "0.00")
        green(wc.cell(r, 24, f"=T{r}-(V{r}+N{r}/1000)"), "0.00")
        green(wc.cell(r, 25, f"=PI()*(N{r}/1000)^2/4*P{r}"), "0.000")
        yellow(wc.cell(r, 26, 1.2), "0.00")  # dia bouche placeholder
        green(wc.cell(r, 27, f"=PI()*(Z{r}/2)^2*1.5"), "0.000")  # H~1.5 m approx
        green(
            wc.cell(
                r,
                28,
                f'=IF(R{r}<=0,"—",IF(R{r}>=L{r},"OK","AUGMENTER Ø"))',
            )
        )
        # Qin from trenches whose outlet = this Amont
        green(
            wc.cell(r, 29, f'=SUMIF(Tranchees!$C$8:$C$20,A{r},Tranchees!$N$8:$N$20)'),
            "0.000",
        )
        note = "reçoit tranchée(s)" if i < 3 else ""
        if note:
            wc.cell(r, 30, note).fill = ORANGE
        wc.cell(r, 30).border = THIN

    last_p = r0p + len(PIPES) - 1
    wc.cell(last_p + 2, 1, "TOTAL L (m)")
    green(wc.cell(last_p + 2, 16, f"=SUM(P{r0p}:P{last_p})"), "0.00")
    wc.cell(last_p + 3, 1, "TOTAL Vol_cond (m³)")
    green(wc.cell(last_p + 3, 25, f"=SUM(Y{r0p}:Y{last_p})"), "0.000")
    wc.cell(last_p + 4, 1, "TOTAL Vol_bouch (m³)")
    green(wc.cell(last_p + 4, 27, f"=SUM(AA{r0p}:AA{last_p})"), "0.000")

    wc.cell(last_p + 6, 1, "INSTRUCTIONS")
    wc.cell(last_p + 7, 1, "Jaune = saisie; Vert = calculé. Colonnes Amont des 1ers tronçons = Noeud_aval des Tranchees.")
    wc.cell(last_p + 8, 1, "AC = débit issu des tranchées drainantes (SUMIF). Qmax inclut déjà AC.")
    wc.cell(last_p + 9, 1, "Remplacer pentes/radiers/L/Ø par données de plan. IDs RP-N1/S1/E1 = placeholders.")

    for col in range(1, 31):
        wc.column_dimensions[get_column_letter(col)].width = 11
    wc.column_dimensions["A"].width = 12
    wc.column_dimensions["C"].width = 12
    wc.column_dimensions["AD"].width = 18

    # chart Qmax vs Qp
    ch = LineChart()
    ch.title = "Qmax vs Qp par tronçon"
    ch.y_axis.title = "Q (m³/s)"
    ch.x_axis.title = "Tronçon (amont)"
    ch.add_data(Reference(wc, min_col=12, min_row=14, max_row=last_p), titles_from_data=True)
    ch.add_data(Reference(wc, min_col=18, min_row=14, max_row=last_p), titles_from_data=True)
    ch.set_categories(Reference(wc, min_col=1, min_row=r0p, max_row=last_p))
    wc.add_chart(ch, "A40")

    # ========== Resume ==========
    wr = wb.create_sheet("Resume")
    wr["A1"] = "Résumé — 1787 GC hybride"
    wr["A1"].font = Font(bold=True, size=13, color="0F5C5C")
    rows = [
        (3, "Période de retour (ans)", "=Inputs!B3"),
        (4, "Total SUP zones (m²)", "=Zones_tributaires!C16"),
        (5, "Total Vol_stock tranchées (m³)", f"=Tranchees!Q{last_t+2}"),
        (6, "Total L pipes (m)", f"=Calcul_reseau!P{last_p+2}"),
        (7, "Total Vol_cond pipes (m³)", f"=Calcul_reseau!Y{last_p+3}"),
        (8, "Total Vol_bouch (m³)", f"=Calcul_reseau!AA{last_p+4}"),
        (9, "Volume stockage total utile (m³)", "=B5+B7+B8"),
        (10, "Nb checks pipe non-OK", f'=COUNTIF(Calcul_reseau!AB{r0p}:AB{last_p},"AUGMENTER Ø")'),
        (11, "Nb checks tranchée non-OK", f'=COUNTIF(Tranchees!R{r0}:R{last_t},"AUGMENTER Ø/s")'),
    ]
    wr["A2"] = "Indicateur"
    wr["B2"] = "Valeur"
    style_header(wr, 2, 2)
    for r, lab, formula in rows:
        wr.cell(r, 1, lab)
        green(wr.cell(r, 2, formula), "0.000" if "Vol" in lab or "SUP" in lab or "L pipes" in lab else "0")
    # fix zone total row ref - Zones last data row
    wr["B4"] = f"=SUM(Zones_tributaires!C5:C{4+len(ZONES)})"
    green(wr["B4"], "0.0")
    wr["B5"] = f"=Tranchees!Q{last_t+2}"
    green(wr["B5"], "0.0")

    wr["A14"] = "Statut global"
    wr["B14"] = '=IF(AND(B10=0,B11=0),"OK — revoir radiers/IDs sur plan","À AJUSTER — voir checks")'
    wr["B14"].fill = GREEN
    wr["A16"] = (
        "Rappel: les cotes RP/RS/RPP du croquis (ex. RS-01 E:20.14) sont des points de départ; "
        "les tranchées du plan (« avec sur-pente ») doivent être mesurées (L, b, H) avant IFC."
    )
    wr.merge_cells("A16:D18")
    wr["A16"].alignment = Alignment(wrap_text=True)
    for col, w in zip("AB", [40, 18]):
        wr.column_dimensions[col].width = w

    wb.save(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path}")
