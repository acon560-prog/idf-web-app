#!/usr/bin/env python3
"""
1787 GC — modèle hybride pluvial (optimisé)

Bloc A Calcul_reseau:
  - DA_g / DA_p seulement (jaune) → DA, DART, RT dérivés (plus de RT saisi)
  - Pas de DA_t sur les pipes (évite double comptage avec Tranchees)
  - Qin_tranchée = SUMIF depuis Tranchees → ajouté à Qmax
  - Radiers / couverture / Vol_cond gardés; Vol_bouch optionnel condensé

Bloc B Tranchees:
  - Qp_ud (underdrain) + Qp_trench (Manning section ouverte b×y)
  - Qp_total = somme; Vol_stock = b×H×L×porosité
"""
from __future__ import annotations

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

# IDF Mirabel (règlement 457 — MAJORÉ) — coeffs saisis dans Inputs; table de secours
IDF_MIRABEL_NOTE = "Pluie de Mirabel règlement 457 — MAJORÉ (vérifier période)"
# A, B, C as used in user file screenshot for active design
IDF_ACTIVE = (2134.17, 10.5, 0.921)

ZONES = [
    ("Z-BAT", "Bâtiment proposé RDC", 2434.75, 0.95, "toiture→pipes"),
    ("Z-P1", "Pavage (SUP croquis)", 851.9, 0.90, "pavage→pipes"),
    ("Z-P2", "Pavage (SUP croquis)", 882.5, 0.90, "pavage→pipes"),
    ("Z-P3", "Pavage (SUP croquis)", 736.8, 0.90, "pavage→pipes"),
    ("Z-G1", "Gazon bande nord", 425.0, 0.25, "gazon→T-NORD"),
    ("Z-G2", "Gazon bande sud", 378.2, 0.25, "gazon→T-SUD"),
    ("Z-G3", "Gazon bande sud", 330.3, 0.25, "gazon→T-SUD"),
    ("Z-G4", "Gazon bande est", 326.1, 0.25, "gazon→T-EST"),
    ("Z-A1", "Autre / annexe", 123.0, 0.60, "à classer"),
    ("Z-A2", "Autre / annexe", 98.2, 0.60, "à classer"),
    ("Z-A3", "Autre / annexe", 73.3, 0.60, "à classer"),
]

# id, desc, outlet_puisard, L, b, H, n_open, por, ud_mm, s, y_flow (depth for Manning open)
TRANCHEES = [
    ("T-NORD", "Tranchée nord (gazon / sur-pente)", "P-09", 45.0, 0.60, 0.70, 0.028, 0.35, 200, 0.005, 0.30),
    ("T-SUD", "Tranchée sud (gazon / sur-pente)", "P-08", 55.0, 0.60, 0.70, 0.028, 0.35, 200, 0.005, 0.30),
    ("T-EST", "Tranchée est (gazon)", "RP-05", 35.0, 0.50, 0.70, 0.028, 0.35, 200, 0.005, 0.30),
]

# Topology aligned with user's working file (screenshot)
# amont, aval, DA_g, DA_p, s, dnom, L, sol_am, sol_av, rad_am, rad_av
PIPES = [
    ("P-09", "P-08", 0.0400, 0.0000, 0.0050, 150, 20.00, 24.50, 24.45, 23.20, 23.10),
    ("P-08", "RP-05", 0.0420, 0.0500, 0.0050, 250, 28.00, 24.45, 24.40, 23.10, 22.90),
    ("RP-05", "P-05", 0.0200, 0.0800, 0.0050, 250, 32.00, 24.40, 24.35, 22.90, 22.70),
    ("P-05", "RP-01", 0.0150, 0.1000, 0.0050, 300, 35.00, 24.35, 24.30, 22.70, 22.40),
    ("RPP-02", "RS-01", 0.0100, 0.1200, 0.0080, 375, 44.14, 24.33, 24.60, 22.22, 20.14),
    ("RS-01", "EXUTOIRE", 0.0000, 0.0500, 0.0100, 375, 30.00, 24.60, 24.50, 20.14, 19.90),
]


def style_header(ws, row: int, ncols: int) -> None:
    for c in range(1, ncols + 1):
        cell = ws.cell(row, c)
        cell.font = HEADER
        cell.fill = HEADER_FILL
        cell.border = THIN
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")


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

    # ----- Guide -----
    wg = wb.active
    wg.title = "Guide"
    wg["A1"] = "1787 GC — Réseau pluvial hybride (version optimisée)"
    wg["A1"].font = Font(bold=True, size=14, color="0F5C5C")
    for i, line in enumerate(
        [
            "",
            "Optimisations vs version précédente / colonnes redondantes",
            "  • RT n'est plus saisi: RT = DART/DA (vert), avec DART = DA_g×C_g + DA_p×C_p",
            "  • DA_t retiré des pipes: les aires gazon des tranchées vivent dans Tranchees / Zones",
            "    → évite de compter deux fois le même gazon (DA_t + Qin_tranchée)",
            "  • Qin_tranchée (SUMIF) = seul apport des tranchées vers le noeud Amont",
            "  • Sur Tranchees: Qp_ud + Qp_trench (Manning b×y) + Qp_total (plus seulement le pipe)",
            "  • Vol_bouch: une seule colonne (Ø bouche fixe dans Inputs) — moins de bruit",
            "",
            "Colonnes CONSERVÉES (pas redondantes — chaîne rationnelle)",
            "  DA → DART → A (cumul) → AR (cumul) → R=AR/A → I(tc) → Qmax",
            "  DART/AR/R sont des étapes utiles pour vérification municipale; on les garde en vert.",
            "",
            "Couleurs: Jaune=saisie | Vert=calculé | Orange=ID à valider sur plan",
            "",
            "Fichiers: croquis PDF dans ce dossier; régénérer = python3 build_1787_hybrid_excel.py",
        ],
        start=2,
    ):
        wg.cell(i, 1, line)
    wg.column_dimensions["A"].width = 108

    # ----- Inputs -----
    wi = wb.create_sheet("Inputs")
    wi["A1"] = "INPUTS — 1787 GC"
    wi["A1"].font = Font(bold=True, size=13, color="0F5C5C")
    wi["A2"] = "Paramètre"
    wi["B2"] = "Valeur"
    wi["C2"] = "Unité"
    wi["D2"] = "Note"
    style_header(wi, 2, 4)

    rows_in = [
        (3, "Periode_retour_ans", 25, "ans", "Design"),
        (4, "IDF_A", IDF_ACTIVE[0], "-", IDF_MIRABEL_NOTE),
        (5, "IDF_B", IDF_ACTIVE[1], "min", "I = A/(tc+B)^C"),
        (6, "IDF_C", IDF_ACTIVE[2], "-", ""),
        (7, "n_pipe", 0.013, "-", "Manning conduites"),
        (8, "n_trench_open", 0.028, "-", "Manning écoulement dans tranchée (pierre/media)"),
        (9, "n_underdrain", 0.013, "-", "Manning underdrain"),
        (10, "C_grass", 0.25, "-", "Ruissellement gazon (DA_g)"),
        (11, "C_pave", 0.90, "-", "Ruissellement pavage/toit (DA_p)"),
        (12, "Trench_porosity", 0.35, "-", "Porosité utile stockage"),
        (13, "Dia_bouch_m", 1.20, "m", "Regard/puisard typ. pour Vol_bouch"),
        (14, "H_bouch_m", 1.50, "m", "Hauteur utile approx. regard"),
        (15, "Vmin_mps", 0.60, "m/s", "Auto-curage"),
        (16, "Vmax_mps", 3.00, "m/s", "Érosion"),
        (17, "Safety_Q", 1.00, "-", "Facteur sur Qmax"),
        (18, "k_rational", 0.00275, "-", "Q(m³/s)=k·A(ha)·R·I(mm/h)"),
    ]
    for r, name, val, unit, note in rows_in:
        wi.cell(r, 1, name)
        fmt = "0.000" if isinstance(val, float) and abs(val) < 10 else "0.00"
        if name == "IDF_A":
            fmt = "0.00"
        yellow(wi.cell(r, 2, val), fmt)
        wi.cell(r, 3, unit)
        wi.cell(r, 4, note)
    for col, w in zip("ABCD", [22, 12, 8, 55]):
        wi.column_dimensions[col].width = w

    # ----- Zones -----
    wz = wb.create_sheet("Zones_tributaires")
    wz["A1"] = "Zones — SUP croquis (gazon → Tranchees; pavage/toit → pipes via DA_g/DA_p)"
    wz["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    for j, h in enumerate(
        ["Zone_ID", "Description", "SUP (m²)", "C (-)", "Aire (ha)", "Destination", "Note"], 1
    ):
        wz.cell(3, j, h)
    style_header(wz, 3, 7)
    for i, (zid, desc, area, c, note) in enumerate(ZONES, start=4):
        wz.cell(i, 1, zid).border = THIN
        yellow(wz.cell(i, 2, desc))
        yellow(wz.cell(i, 3, area), "0.0")
        yellow(wz.cell(i, 4, c), "0.00")
        green(wz.cell(i, 5, f"=C{i}/10000"), "0.0000")
        if "T-NORD" in note:
            dest = "T-NORD"
        elif "T-SUD" in note:
            dest = "T-SUD"
        elif "T-EST" in note:
            dest = "T-EST"
        elif "pipes" in note:
            dest = "PIPE (DA_p sur Calcul_reseau)"
        else:
            dest = "à classer"
        cell = wz.cell(i, 6, dest)
        cell.fill = ORANGE
        cell.border = THIN
        wz.cell(i, 7, note).border = THIN
    last_z = 3 + len(ZONES)
    wz.cell(last_z + 2, 1, "Total SUP (m²)")
    green(wz.cell(last_z + 2, 3, f"=SUM(C4:C{last_z})"), "0.0")
    for col, w in zip("ABCDEFG", [10, 28, 12, 8, 10, 28, 28]):
        wz.column_dimensions[col].width = w

    # ----- Temps -----
    wt = wb.create_sheet("Temps_concentration")
    wt["A1"] = "Temps de concentration"
    wt["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wt["A3"] = "tc_entrée (min)"
    yellow(wt.cell(3, 2, 10.0), "0.0")
    wt["C3"] = "Défaut (screenshot utilisateur). Ajuster selon overland réel."
    wt.column_dimensions["A"].width = 18
    wt.column_dimensions["B"].width = 10
    wt.column_dimensions["C"].width = 55

    # ----- Tranchees -----
    wtr = wb.create_sheet("Tranchees")
    wtr["A1"] = "Bloc B — Tranchées drainantes (collecte + stockage + conveyance)"
    wtr["A1"].font = Font(bold=True, size=12, color="0F5C5C")
    wtr["A2"] = (
        "Qp_ud = underdrain plein. Qp_trench = Manning sur section b × y_flow (écoulement dans le media/fossé). "
        "Qp_total = Qp_ud + Qp_trench. Vol_stock = b×H×L×porosité (stockage — rôle distinct de Qp)."
    )
    wtr.merge_cells("A2:P2")
    wtr["A2"].alignment = Alignment(wrap_text=True)

    wtr["A4"] = "tc_ref (min)"
    wtr["B4"] = "=Temps_concentration!B3"
    green(wtr["B4"], "0.0")
    wtr["A5"] = "I_ref (mm/h)"
    wtr["B5"] = "=Inputs!B4/((B4+Inputs!B5)^Inputs!B6)"
    green(wtr["B5"], "0.00")

    th = [
        "Trench_ID",
        "Description",
        "Noeud_aval",
        "L (m)",
        "b (m)",
        "H stock (m)",
        "y_flow (m)",
        "n_open",
        "Porosité",
        "Ø ud (mm)",
        "s (m/m)",
        "A_ha",
        "C_moy",
        "Q_zone (m³/s)",
        "Qp_ud (m³/s)",
        "Qp_trench (m³/s)",
        "Qp_total (m³/s)",
        "Vol_stock (m³)",
        "Check",
    ]
    for j, h in enumerate(th, 1):
        wtr.cell(7, j, h)
    style_header(wtr, 7, len(th))
    wtr.row_dimensions[7].height = 34

    r0 = 8
    for i, (tid, desc, outlet, L, b, H, n_o, por, ud, s, y) in enumerate(TRANCHEES):
        r = r0 + i
        wtr.cell(r, 1, tid).border = THIN
        yellow(wtr.cell(r, 2, desc))
        cell = wtr.cell(r, 3, outlet)
        cell.fill = ORANGE
        cell.border = THIN
        yellow(wtr.cell(r, 4, L), "0.0")
        yellow(wtr.cell(r, 5, b), "0.00")
        yellow(wtr.cell(r, 6, H), "0.00")
        yellow(wtr.cell(r, 7, y), "0.00")
        yellow(wtr.cell(r, 8, n_o), "0.000")
        yellow(wtr.cell(r, 9, por), "0.00")
        yellow(wtr.cell(r, 10, ud), "0")
        yellow(wtr.cell(r, 11, s), "0.0000")
        green(
            wtr.cell(r, 12, f'=SUMIF(Zones_tributaires!$F$4:$F$20,A{r},Zones_tributaires!$E$4:$E$20)'),
            "0.0000",
        )
        green(
            wtr.cell(
                r,
                13,
                f'=IF(L{r}<=0,Inputs!$B$10,'
                f'SUMPRODUCT((Zones_tributaires!$F$4:$F$20=A{r})*(Zones_tributaires!$E$4:$E$20)*(Zones_tributaires!$D$4:$D$20))/L{r})',
            ),
            "0.00",
        )
        green(wtr.cell(r, 14, f"=Inputs!$B$17*Inputs!$B$18*L{r}*M{r}*$B$5"), "0.000")
        # Qp_ud
        green(
            wtr.cell(
                r,
                15,
                f'=IF(OR(J{r}<=0,K{r}<=0),0,'
                f'((J{r}/4000)^(2/3)*SQRT(K{r}))/Inputs!$B$9*PI()*(J{r}/1000)^2/4)',
            ),
            "0.000",
        )
        # Qp_trench Manning rectangular: A=b*y, P=b+2y, R=A/P
        green(
            wtr.cell(
                r,
                16,
                f'=IF(OR(E{r}<=0,G{r}<=0,K{r}<=0,H{r}<=0),0,'
                f'(1/H{r})*(E{r}*G{r})*(((E{r}*G{r})/(E{r}+2*G{r}))^(2/3))*SQRT(K{r}))',
            ),
            "0.000",
        )
        green(wtr.cell(r, 17, f"=O{r}+P{r}"), "0.000")
        green(wtr.cell(r, 18, f"=E{r}*F{r}*D{r}*I{r}"), "0.0")
        green(
            wtr.cell(r, 19, f'=IF(Q{r}<=0,"—",IF(Q{r}>=N{r},"OK","AUGMENTER b/y/Ø/s"))'),
        )

    last_t = r0 + len(TRANCHEES) - 1
    wtr.cell(last_t + 2, 1, "Σ Vol_stock (m³)")
    green(wtr.cell(last_t + 2, 18, f"=SUM(R{r0}:R{last_t})"), "0.0")
    wtr.cell(last_t + 3, 1, "Σ Q_zone (m³/s)")
    green(wtr.cell(last_t + 3, 14, f"=SUM(N{r0}:N{last_t})"), "0.000")
    wtr.cell(last_t + 4, 1, "Σ Qp_total (m³/s)")
    green(wtr.cell(last_t + 4, 17, f"=SUM(Q{r0}:Q{last_t})"), "0.000")

    wtr["A20"] = (
        "Noeud_aval doit = Amont d'un tronçon dans Calcul_reseau (ex. P-09, P-08, RP-05). "
        "y_flow ≤ H stock. Si Check = AUGMENTER: élargir b, augmenter y, Ø ud ou pente."
    )
    wtr.merge_cells("A20:S21")
    wtr["A20"].alignment = Alignment(wrap_text=True)
    for col in range(1, 20):
        wtr.column_dimensions[get_column_letter(col)].width = 11
    wtr.column_dimensions["B"].width = 34

    # ----- Calcul_reseau (optimized) -----
    wc = wb.create_sheet("Calcul_reseau")
    wc["A1"] = "Bloc A — Conduites + regards (structure optimisée)"
    wc["A1"].font = Font(bold=True, size=13, color="0F5C5C")
    wc["A2"] = "Projet"
    yellow(wc.cell(2, 2, "1787 GC — hybride pipes + tranchées"))
    wc["A3"] = "No dossier"
    yellow(wc.cell(3, 2, "1787"))
    wc["A4"] = "Date"
    yellow(wc.cell(4, 2, "2026-11-05"))
    wc["A5"] = "IDF"
    wc["B5"] = IDF_MIRABEL_NOTE
    wc["B5"].fill = BLUE

    wc["E2"] = "Retour (ans)"
    wc["F2"] = "=Inputs!B3"
    green(wc["F2"], "0")
    wc["E3"] = "n / A,B,C"
    wc["F3"] = "=Inputs!B7"
    wc["G3"] = "=Inputs!B4"
    wc["H3"] = "=Inputs!B5"
    wc["I3"] = "=Inputs!B6"
    green(wc["F3"], "0.000")
    green(wc["G3"], "0.00")
    green(wc["H3"], "0.0")
    green(wc["I3"], "0.000")

    wc["A7"] = (
        "DA_g / DA_p = accroissements directs sur CE tronçon (gazon local hors tranchée modélisée, pavage/toit). "
        "Aires des tranchées → onglet Tranchees seulement. Qin_tr = SUMIF(Tranchees). "
        "RT dérivé (plus saisi). Qmax = k·A·R·I + Qin_tr."
    )
    wc.merge_cells("A7:X8")
    wc["A7"].alignment = Alignment(wrap_text=True)

    # Compact headers — removed redundant RT input & DA_t & separate Dia_bouch column (use Inputs)
    headers = [
        "Amont",
        "Liaison",
        "Aval",
        "tc (min)",
        "DA_g (ha)",
        "DA_p (ha)",
        "DA (ha)",
        "DART (ha)",
        "RT (-)",
        "A (ha)",
        "AR (ha)",
        "R (-)",
        "I (mm/h)",
        "Qin_tr (m³/s)",
        "Qmax (m³/s)",
        "s (m/m)",
        "dnom (mm)",
        "v (m/s)",
        "L (m)",
        "tf (min)",
        "Qp (m³/s)",
        "Sol am (m)",
        "Sol av (m)",
        "Rad am (m)",
        "Rad av (m)",
        "Cov am (m)",
        "Cov av (m)",
        "Vol_cond (m³)",
        "Vol_bouch (m³)",
        "Check",
        "Note",
    ]
    for j, h in enumerate(headers, 1):
        wc.cell(10, j, h)
    style_header(wc, 10, len(headers))
    wc.row_dimensions[10].height = 36

    n_ref = "$F$3"
    a_idf, b_idf, c_idf = "$G$3", "$H$3", "$I$3"
    r0p = 11

    for i, (am, av, dag, dap, s, dnom, L, sol_a, sol_v, rad_a, rad_v) in enumerate(PIPES):
        r = r0p + i
        yellow(wc.cell(r, 1, am))
        wc.cell(r, 2, "@").border = THIN
        yellow(wc.cell(r, 3, av))

        if i == 0:
            green(wc.cell(r, 4, "=Temps_concentration!B3"), "0.00")
            green(wc.cell(r, 10, f"=G{r}"), "0.0000")  # A
            green(wc.cell(r, 11, f"=H{r}"), "0.0000")  # AR
        else:
            p = r - 1
            green(wc.cell(r, 4, f"=MAX(Temps_concentration!B3,D{p}+T{p})"), "0.00")
            green(wc.cell(r, 10, f"=J{p}+G{r}"), "0.0000")
            green(wc.cell(r, 11, f"=K{p}+H{r}"), "0.0000")

        yellow(wc.cell(r, 5, dag), "0.0000")
        yellow(wc.cell(r, 6, dap), "0.0000")
        green(wc.cell(r, 7, f"=E{r}+F{r}"), "0.0000")  # DA
        green(
            wc.cell(r, 8, f"=E{r}*Inputs!$B$10+F{r}*Inputs!$B$11"),
            "0.0000",
        )  # DART
        green(wc.cell(r, 9, f"=IF(G{r}=0,0,H{r}/G{r})"), "0.00")  # RT
        green(wc.cell(r, 12, f"=IF(J{r}=0,0,K{r}/J{r})"), "0.00")  # R
        green(
            wc.cell(r, 13, f"=IF(D{r}<=0,0,{a_idf}/((D{r}+{b_idf})^{c_idf}))"),
            "0.00",
        )
        green(
            wc.cell(r, 14, f'=SUMIF(Tranchees!$C$8:$C$20,A{r},Tranchees!$N$8:$N$20)'),
            "0.000",
        )
        green(
            wc.cell(r, 15, f"=Inputs!$B$17*Inputs!$B$18*J{r}*L{r}*M{r}+N{r}"),
            "0.000",
        )
        yellow(wc.cell(r, 16, s), "0.0000")
        yellow(wc.cell(r, 17, dnom), "0")
        green(
            wc.cell(
                r,
                18,
                f'=IF(OR(Q{r}<=0,P{r}<=0),0,((Q{r}/4000)^(2/3)*SQRT(P{r}))/{n_ref})',
            ),
            "0.00",
        )
        yellow(wc.cell(r, 19, L), "0.00")
        green(wc.cell(r, 20, f"=IF(R{r}=0,0,S{r}/(R{r}*60))"), "0.00")
        green(wc.cell(r, 21, f"=R{r}*PI()*(Q{r}/1000)^2/4"), "0.000")
        yellow(wc.cell(r, 22, sol_a), "0.000")
        yellow(wc.cell(r, 23, sol_v), "0.000")
        yellow(wc.cell(r, 24, rad_a), "0.000")
        yellow(wc.cell(r, 25, rad_v), "0.000")
        green(wc.cell(r, 26, f"=V{r}-(X{r}+Q{r}/1000)"), "0.00")
        green(wc.cell(r, 27, f"=W{r}-(Y{r}+Q{r}/1000)"), "0.00")
        green(wc.cell(r, 28, f"=PI()*(Q{r}/1000)^2/4*S{r}"), "0.000")
        green(
            wc.cell(r, 29, f"=PI()*(Inputs!$B$13/2)^2*Inputs!$B$14"),
            "0.000",
        )
        green(
            wc.cell(r, 30, f'=IF(U{r}<=0,"—",IF(U{r}>=O{r},"OK","AUGMENTER Ø"))'),
        )
        note = ""
        if am in {t[2] for t in TRANCHEES}:
            note = "reçoit tranchée(s)"
            wc.cell(r, 31, note).fill = ORANGE
        else:
            wc.cell(r, 31, note)
        wc.cell(r, 31).border = THIN

    last_p = r0p + len(PIPES) - 1
    wc.cell(last_p + 2, 1, "TOTAL L (m)")
    green(wc.cell(last_p + 2, 19, f"=SUM(S{r0p}:S{last_p})"), "0.00")
    wc.cell(last_p + 3, 1, "TOTAL Vol_cond (m³)")
    green(wc.cell(last_p + 3, 28, f"=SUM(AB{r0p}:AB{last_p})"), "0.000")
    wc.cell(last_p + 4, 1, "TOTAL Vol_bouch (m³)")
    green(wc.cell(last_p + 4, 29, f"=SUM(AC{r0p}:AC{last_p})"), "0.000")

    wc.cell(last_p + 6, 1, "Légende rapide")
    wc.cell(
        last_p + 7,
        1,
        "DA_g/DA_p jaune → DA, DART, RT verts. A/AR/R = cumul. Qin_tr depuis Tranchees. Check = Qp≥Qmax.",
    )
    wc.merge_cells(f"A{last_p+7}:O{last_p+7}")

    for col in range(1, 32):
        wc.column_dimensions[get_column_letter(col)].width = 10
    wc.column_dimensions["A"].width = 10
    wc.column_dimensions["C"].width = 10
    wc.column_dimensions["AE"].width = 18

    ch = LineChart()
    ch.title = "Qmax vs Qp"
    ch.y_axis.title = "Q (m³/s)"
    ch.add_data(Reference(wc, min_col=15, min_row=10, max_row=last_p), titles_from_data=True)
    ch.add_data(Reference(wc, min_col=21, min_row=10, max_row=last_p), titles_from_data=True)
    ch.set_categories(Reference(wc, min_col=1, min_row=r0p, max_row=last_p))
    wc.add_chart(ch, "A40")

    # ----- Resume -----
    wr = wb.create_sheet("Resume")
    wr["A1"] = "Résumé 1787 GC (optimisé)"
    wr["A1"].font = Font(bold=True, size=13, color="0F5C5C")
    wr["A2"] = "Indicateur"
    wr["B2"] = "Valeur"
    style_header(wr, 2, 2)
    items = [
        (3, "Retour (ans)", "=Inputs!B3"),
        (4, "Σ SUP zones (m²)", f"=SUM(Zones_tributaires!C4:C{3+len(ZONES)})"),
        (5, "Σ Vol_stock tranchées (m³)", f"=Tranchees!R{last_t+2}"),
        (6, "Σ Qp_total tranchées (m³/s)", f"=Tranchees!Q{last_t+4}"),
        (7, "Σ L pipes (m)", f"=Calcul_reseau!S{last_p+2}"),
        (8, "Σ Vol_cond (m³)", f"=Calcul_reseau!AB{last_p+3}"),
        (9, "Σ Vol_bouch (m³)", f"=Calcul_reseau!AC{last_p+4}"),
        (10, "Checks pipe NOK", f'=COUNTIF(Calcul_reseau!AD{r0p}:AD{last_p},"AUGMENTER Ø")'),
        (11, "Checks tranchée NOK", f'=COUNTIF(Tranchees!S{r0}:S{last_t},"AUGMENTER b/y/Ø/s")'),
    ]
    for r, lab, f in items:
        wr.cell(r, 1, lab)
        green(wr.cell(r, 2, f), "0.000")
    wr["A13"] = "Statut"
    wr["B13"] = '=IF(AND(B10=0,B11=0),"OK — valider IDs/radiers sur plan","À AJUSTER")'
    wr["B13"].fill = GREEN
    wr["A15"] = (
        "Rappel: gazon de tranchée ne doit PAS être re-saisi en DA_g sur le même apport "
        "(sinon double comptage avec Qin_tr)."
    )
    wr.merge_cells("A15:B16")
    wr["A15"].alignment = Alignment(wrap_text=True)
    wr.column_dimensions["A"].width = 36
    wr.column_dimensions["B"].width = 16

    wb.save(OUT)
    return OUT


if __name__ == "__main__":
    print(f"Wrote {build()}")
