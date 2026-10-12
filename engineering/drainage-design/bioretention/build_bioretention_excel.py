#!/usr/bin/env python3
"""
Bio-rétention — pack de dimensionnement v1 (formules Excel live).

Produit vendable / livrable:
  - surface filtrante requise Af
  - volume de captage Vcap
  - temps de vidange (ponding)
  - bilan de couches (mulch / média / réservoir)
  - note Méthode + checklist CSA W200 (rappels, pas le texte de la norme)

Références de pratique (Canada): STEP LID wiki sizing, esprit CSA W200:18.
Jaune = entrées · vert = résultats · bleu = intermédiaires.
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

HERE = Path(__file__).resolve().parent
OUT = HERE / "Bioretention_Dimensionnement_v1.xlsx"

YELLOW = PatternFill("solid", fgColor="FFF59D")
GREEN = PatternFill("solid", fgColor="C8E6C9")
BLUE = PatternFill("solid", fgColor="BBDEFB")
ORANGE = PatternFill("solid", fgColor="FFE0B2")
HDR = PatternFill("solid", fgColor="1B5E4B")
HDR_FONT = Font(bold=True, color="FFFFFF")
THIN = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)


def hdr_row(ws, row: int, ncols: int) -> None:
    for c in range(1, ncols + 1):
        cell = ws.cell(row, c)
        cell.fill = HDR
        cell.font = HDR_FONT
        cell.border = THIN


def yellow(ws, r, c, val, fmt=None):
    cell = ws.cell(r, c, val)
    cell.fill = YELLOW
    cell.border = THIN
    if fmt:
        cell.number_format = fmt
    return cell


def green(ws, r, c, val, fmt=None):
    cell = ws.cell(r, c, val)
    cell.fill = GREEN
    cell.border = THIN
    if fmt:
        cell.number_format = fmt
    return cell


def blue(ws, r, c, val, fmt=None):
    cell = ws.cell(r, c, val)
    cell.fill = BLUE
    cell.border = THIN
    if fmt:
        cell.number_format = fmt
    return cell


def build() -> Path:
    wb = Workbook()

    # ---------- Parametres ----------
    ws = wb.active
    ws.title = "Parametres"
    ws["A1"] = "BIO-RÉTENTION — Dimensionnement v1 (formules Excel)"
    ws["A1"].font = Font(bold=True, size=14, color="1B5E4B")
    ws.merge_cells("A1:F1")
    ws["A2"] = (
        "But: estimer la surface filtrante Af et vérifier la vidange pour un volume de captage "
        "(qualité d'eau / petite pluie). Jaune = entrées. Vert = résultats. "
        "Adapter aux exigences municipales + CSA W200."
    )
    ws.merge_cells("A2:F3")
    ws["A2"].alignment = Alignment(wrap_text=True)

    ws["A5"] = "1) Bassin versant (jaune)"
    ws["A5"].font = Font(bold=True)
    rows_bv = [
        (6, "Aire drainée Ad (m2)", 2500, "0"),
        (7, "Coefficient de ruissellement C (-)", 0.70, "0.00"),
        (8, "Profondeur de pluie de captage Rd (mm)", 25, "0.0"),
        (9, "Facteur de captage η (-)", 0.90, "0.00"),
    ]
    for r, lab, val, fmt in rows_bv:
        ws.cell(r, 1, lab)
        yellow(ws, r, 2, val, fmt)
    ws["C8"] = "Souvent 25 mm (première chasse / WQ) — confirmer ville"
    ws["C9"] = "Fraction du volume théorique réellement ciblée (0.8–1.0)"

    ws["A11"] = "2) Géométrie & sols (jaune)"
    ws["A11"].font = Font(bold=True)
    rows_geo = [
        (12, "Profondeur d'ennoiement max dp (m)", 0.30, "0.00"),
        (13, "Profondeur média filtrant df (m)", 0.60, "0.00"),
        (14, "Porosité effective média nf (-)", 0.35, "0.00"),
        (15, "Profondeur réservoir/gravier dr (m)", 0.30, "0.00"),
        (16, "Porosité effective réservoir nr (-)", 0.40, "0.00"),
        (17, "Profondeur mulch dm (m)", 0.075, "0.000"),
        (18, "Porosité mulch nm (-)", 0.20, "0.00"),
        (19, "Taux d'infiltration de conception f' (mm/h)", 25, "0.0"),
        (20, "Temps de vidange max admis t_max (h)", 48, "0"),
        (21, "Sous-drain présent? (1=oui, 0=non)", 1, "0"),
    ]
    for r, lab, val, fmt in rows_geo:
        ws.cell(r, 1, lab)
        yellow(ws, r, 2, val, fmt)
    ws["C13"] = "0.30 pelouse/toit · 0.60 arbustes · 1.00 arbres (STEP typique)"
    ws["C19"] = "f' de conception (facteur de sécurité sur essai in situ)"
    ws["C21"] = "1 = underdrain (dr compte dans ds; tp = ennoiement). 0 = infiltration seule (dr exclu; tp = profil)"

    ws["A23"] = "3) Résultats (formules live — dépendent de B21)"
    ws["A23"].font = Font(bold=True, size=12, color="1B5E4B")

    # Vcap = η * C * Rd(mm)/1000 * Ad  (independent of underdrain)
    ws["A24"] = "Volume de captage Vcap (m3)"
    green(ws, 24, 2, "=B9*B7*(B8/1000)*B6", "0.00")
    ws["C24"] = "Vcap = η × C × (Rd/1000) × Ad  (indépendant de B21)"

    # ds with underdrain includes gravel; without excludes gravel voids from credited storage
    ws["A25"] = "Profondeur de stockage effective ds (m)"
    blue(
        ws,
        25,
        2,
        "=IF(B21=1,B12+B17*B18+B13*B14+B15*B16,B12+B17*B18+B13*B14)",
        "0.000",
    )
    ws["C25"] = "B21=1: ds=dp+dm·nm+df·nf+dr·nr · B21=0: sans dr·nr (pas de crédit réservoir drainé)"

    # Af = Vcap / ds  (changes when ds changes with B21)
    ws["A26"] = "Surface filtrante requise Af (m2)"
    green(ws, 26, 2, "=IF(B25<=0,\"ds=0\",B24/B25)", "0.0")
    ws["C26"] = "Af = Vcap / ds  → augmente si B21=0 (ds plus petit)"

    # Ratio Af/Ad
    ws["A27"] = "Ratio Af / Ad (%)"
    green(ws, 27, 2, "=IF(B6<=0,0,100*B26/B6)", "0.0")
    ws["C27"] = "Ordre de grandeur typique souvent 5–20 % selon Rd et C"

    # Governing drawdown time used for OK check
    # B21=1: surface ponding tp = dp / (f'/1000)
    # B21=0: must infiltrate ponding + media voids (+ no drain assist): t = (dp+df*nf)/(f'/1000)
    ws["A28"] = "Temps de vidange gouvernant t_vid (h)"
    green(
        ws,
        28,
        2,
        '=IF(B19<=0,"f\'=0",IF(B21=1,B12/(B19/1000),(B12+B13*B14)/(B19/1000)))',
        "0.0",
    )
    ws["C28"] = "B21=1: t=dp/(f'/1000) · B21=0: t=(dp+df·nf)/(f'/1000) infiltration seule"

    # Secondary: media+reservoir clock (always shown; gravel term × B21)
    ws["A29"] = "Temps média (+gravier si drain) tm (h)"
    green(
        ws,
        29,
        2,
        '=IF(B19<=0,"f\'=0",(B13*B14+IF(B21=1,B15*B16,0))/(B19/1000))',
        "0.0",
    )
    ws["C29"] = "(df·nf + B21·dr·nr) / (f'/1000)"

    ws["A30"] = "Mode hydraulique"
    green(
        ws,
        30,
        2,
        '=IF(B21=1,"Avec sous-drain (SWMM Drain coeff > 0)","Sans sous-drain (SWMM Drain coeff = 0)")',
    )
    ws["B30"].fill = ORANGE

    ws["A31"] = "Vidange OK vs t_max?"
    green(
        ws,
        31,
        2,
        '=IF(OR(B28="f\'=0",B28=""),"",IF(B28<=B20,"OUI — t_vid ≤ t_max","NON — ↑Af, ↓dp, ↑f\' ou ajouter drain"))',
    )
    ws["B31"].fill = ORANGE

    ws["A32"] = "Longueur indicative L si largeur = 3 m"
    yellow(ws, 32, 2, 3.0, "0.0")
    ws["A33"] = "Longueur L (m) pour largeur B32"
    green(ws, 33, 2, "=IF(B32<=0,\"\",B26/B32)", "0.0")

    ws["A35"] = "Message produit"
    ws["A35"].font = Font(bold=True)
    ws["A36"] = (
        "Livrable: Af + Vcap + t_vid. B21 change ds/Af/t_vid. "
        "Pas un design final CSA W200 — valider f', plantation, prétraitement, trop-plein, municipalité."
    )
    ws.merge_cells("A36:F37")
    ws["A36"].alignment = Alignment(wrap_text=True)

    for col, w in zip("ABCDEF", [46, 14, 55, 12, 12, 12]):
        ws.column_dimensions[col].width = w

    # ---------- Couches ----------
    wc = wb.create_sheet("Couches")
    wc["A1"] = "Profil de couches — volumes pour Af calculée"
    wc["A1"].font = Font(bold=True, size=12, color="1B5E4B")
    wc["A2"] = (
        "Af = Parametres!B26. Stockage = Af × profondeur × porosité. "
        "Gravier crédité seulement si Parametres!B21=1 (sous-drain)."
    )
    wc.merge_cells("A2:E3")
    wc["A2"].alignment = Alignment(wrap_text=True)
    for j, h in enumerate(["Couche", "Profondeur (m)", "Porosité n", "Stockage (m3)", "Volume solide+vide (m3)"], 1):
        wc.cell(4, j, h)
    hdr_row(wc, 4, 5)

    layers = [
        (5, "Ennoiement (ponding)", "=Parametres!B12", 1.0, None),
        (6, "Mulch", "=Parametres!B17", "=Parametres!B18", None),
        (7, "Média filtrant", "=Parametres!B13", "=Parametres!B14", None),
        # Gravel storage × B21: no drain → no credited reservoir voids in ds/Af balance
        (8, "Réservoir / gravier (×B21)", "=Parametres!B15", "=Parametres!B16", "B21"),
    ]
    for r, name, dref, nref, gate in layers:
        wc.cell(r, 1, name)
        blue(wc, r, 2, dref, "0.000")
        if isinstance(nref, float):
            blue(wc, r, 3, nref, "0.00")
        else:
            blue(wc, r, 3, nref, "0.00")
        if gate == "B21":
            green(wc, r, 4, f"=Parametres!$B$21*Parametres!$B$26*B{r}*C{r}", "0.00")
            green(wc, r, 5, f"=Parametres!$B$21*Parametres!$B$26*B{r}", "0.00")
        else:
            green(wc, r, 4, f"=Parametres!$B$26*B{r}*C{r}", "0.00")
            green(wc, r, 5, f"=Parametres!$B$26*B{r}", "0.00")

    wc["A10"] = "Stockage total crédité (m3)"
    green(wc, 10, 2, "=SUM(D5:D8)", "0.00")
    wc["A11"] = "Écart vs Vcap (m3)"
    green(wc, 11, 2, "=B10-Parametres!B24", "0.00")
    wc["C11"] = "≈ 0 si Af = Vcap/ds (gravier exclu quand B21=0)"

    ch = BarChart()
    ch.title = "Stockage par couche (m3)"
    ch.add_data(Reference(wc, min_col=4, min_row=4, max_row=8), titles_from_data=True)
    ch.set_categories(Reference(wc, min_col=1, min_row=5, max_row=8))
    wc.add_chart(ch, "A14")

    for col, w in zip("ABCDE", [22, 14, 12, 14, 18]):
        wc.column_dimensions[col].width = w

    # ---------- Scenarios ----------
    ws2 = wb.create_sheet("Scenarios")
    ws2["A1"] = "Scénarios rapides — même bassin, Rd variable"
    ws2["A1"].font = Font(bold=True, size=12, color="1B5E4B")
    ws2["A2"] = (
        "Utile pour montrer au client: 15 / 25 / 40 mm. "
        "Les colonnes C–E sont des formules basées sur Parametres (même C, Ad, ds, f')."
    )
    ws2.merge_cells("A2:F3")

    for j, h in enumerate(["Rd (mm)", "Vcap (m3)", "Af (m2)", "t_vid (h)", "Vidange OK?"], 1):
        ws2.cell(5, j, h)
    hdr_row(ws2, 5, 5)

    for i, rd in enumerate([15.0, 25.0, 40.0]):
        r = 6 + i
        yellow(ws2, r, 1, rd, "0.0")
        green(ws2, r, 2, f"=Parametres!$B$9*Parametres!$B$7*(A{r}/1000)*Parametres!$B$6", "0.00")
        green(ws2, r, 3, f"=IF(Parametres!$B$25<=0,0,B{r}/Parametres!$B$25)", "0.0")
        # Same governing t_vid as Parametres!B28 (depends on B21)
        green(
            ws2,
            r,
            4,
            (
                f'=IF(Parametres!$B$19<=0,0,'
                f'IF(Parametres!$B$21=1,Parametres!$B$12/(Parametres!$B$19/1000),'
                f'(Parametres!$B$12+Parametres!$B$13*Parametres!$B$14)/(Parametres!$B$19/1000)))'
            ),
            "0.0",
        )
        green(
            ws2,
            r,
            5,
            f'=IF(D{r}<=Parametres!$B$20,"OUI","NON")',
        )

    ws2["A11"] = (
        "Note: t_vid dépend de B21, dp, f' (et df·nf si B21=0) — pas de Rd. "
        "Colonne D identique par scénario. Af change avec ds(B21)."
    )
    ws2.merge_cells("A11:E12")
    ws2["A11"].alignment = Alignment(wrap_text=True)
    for col, w in zip("ABCDE", [12, 12, 12, 10, 12]):
        ws2.column_dimensions[col].width = w

    # ---------- Methode ----------
    wm = wb.create_sheet("Methode")
    wm["A1"] = "Méthode — Bio-rétention v1"
    wm["A1"].font = Font(bold=True, size=13, color="1B5E4B")
    lines = [
        "",
        "Objectif commercial: pack Excel prêt à éditer (jaune) pour pré-dimensionner une cellule de bio-rétention.",
        "",
        "Formules (B21 = sous-drain 1/0):",
        "  Vcap = η × C × (Rd/1000) × Ad     (indépendant de B21)",
        "  B21=1: ds = dp + dm·nm + df·nf + dr·nr",
        "  B21=0: ds = dp + dm·nm + df·nf          (pas de crédit réservoir drainé)",
        "  Af   = Vcap / ds",
        "  B21=1: t_vid = dp / (f'/1000)            (vidange d'ennoiement)",
        "  B21=0: t_vid = (dp + df·nf) / (f'/1000)  (infiltration seule)",
        "  tm   = (df·nf + B21·dr·nr) / (f'/1000)",
        "",
        "Lien SWMM LID (Drain tab):",
        "  B21=1 → Drain Coefficient > 0 (underdrain actif)",
        "  B21=0 → Drain Coefficient = 0 (infiltration seule)",
        "",
        "Hypothèses simplifiées (à déclarer dans la note de calcul):",
        "  • Volume de captage type « qualité d'eau / petite pluie » (Rd souvent 25 mm).",
        "  • Stockage crédité = ennoiement + vides média (+ vides gravier seulement si B21=1).",
        "  • Vidange basée sur f' de conception (essai in situ ÷ facteur de sécurité).",
        "  • B21 pilote ds / Af / t_vid; un design CSA W200 détaille diamètre, pente, IWS, etc.",
        "",
        "Références à citer (ne pas copier le texte normatif):",
        "  • CSA W200:18 (R2023) Design of bioretention systems",
        "  • STEP / Sustainable Technologies — Bioretention: Sizing (guide LID)",
        "  • Exigences municipales locales (Montréal / arrondissement / schéma)",
        "",
        "Prochaines versions possibles:",
        "  v1.1 hydrogramme + bypass",
        "  v1.2 prétraitement (fosse à sédiments)",
        "  v1.3 plantation / sel de voirie (climat froid QC)",
        "",
        "Regénérer: python3 build_bioretention_excel.py",
    ]
    for i, line in enumerate(lines, start=2):
        wm.cell(i, 1, line)
    wm.column_dimensions["A"].width = 100

    # ---------- Checklist ----------
    wk = wb.create_sheet("Checklist")
    wk["A1"] = "Checklist conception (rappels — vérifier CSA W200 + ville)"
    wk["A1"].font = Font(bold=True, size=12, color="1B5E4B")
    items = [
        "Essai d'infiltration in situ → f' de conception documenté",
        "Prétraitement (sédimentation) si voirie / abrasifs d'hiver",
        "Trop-plein / bypass vers réseau pluvial existant",
        "Sous-drain: diamètre, pente, enrobage, regard de nettoyage",
        "Membrane / liner si biofiltre ou protection de fondations",
        "Media mix (sable/fines/MO) adapté drainage vs traitement",
        "Profondeur média vs type de végétation (herbe / arbuste / arbre)",
        "Ennoiement max compatible sécurité / plantation",
        "Temps de vidange ≤ exigence locale (ex. 24–48 h)",
        "Accès entretien (paillis, décompression, vacuum)",
        "Sel de déglaçage / espèces tolérantes (climat froid)",
        "Raccordement légal au réseau / permis / limite de travaux",
    ]
    wk.cell(3, 1, "Item")
    wk.cell(3, 2, "OK? (jaune)")
    wk.cell(3, 3, "Note")
    hdr_row(wk, 3, 3)
    for i, item in enumerate(items):
        r = 4 + i
        wk.cell(r, 1, item)
        yellow(wk, r, 2, "à faire")
        wk.cell(r, 3, "")
        for c in range(1, 4):
            wk.cell(r, c).border = THIN
    for col, w in zip("ABC", [70, 14, 30]):
        wk.column_dimensions[col].width = w

    wb.save(OUT)
    return OUT


if __name__ == "__main__":
    p = build()
    print(f"Wrote {p}")
