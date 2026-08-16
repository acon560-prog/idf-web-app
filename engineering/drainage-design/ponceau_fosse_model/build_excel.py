#!/usr/bin/env python3
"""Build Excel workbook for ponceau + fossé compound model.

Hydrogramme_entree and Routing_stockage use live Excel formulas so the user can
change Q peak / rise / fall / pond / dt without re-running Python.
The rating curve Q(HW) and geometric storage S_geo still come from hydraulics.py.
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from hydraulics import (
    CulvertDitchParams,
    build_rating_curve,
    default_triangle_hydrograph,
    route_level_pool,
    solve_HW_for_Q,
    storage_m3,
    summarize,
)


OUT = Path(__file__).resolve().parent / "Ponceau_Fosse_Modele_Hydraulique.xlsx"

HEADER = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="0F5C5C")
YELLOW = PatternFill("solid", fgColor="FFF59D")
WARN = PatternFill("solid", fgColor="FDE68A")
OK = PatternFill("solid", fgColor="D1FAE5")
THIN = Border(
    left=Side(style="thin", color="CBD5E1"),
    right=Side(style="thin", color="CBD5E1"),
    top=Side(style="thin", color="CBD5E1"),
    bottom=Side(style="thin", color="CBD5E1"),
)

# Pre-create enough hydrograph/routing rows for long events / small dt
N_TIME_ROWS = 120  # e.g. 120 * 5 min = 600 min max span


def style_header(ws, row: int, cols: int) -> None:
    for c in range(1, cols + 1):
        cell = ws.cell(row, c)
        cell.font = HEADER
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="center")


def autosize(ws, min_w=12, max_w=42) -> None:
    for col in ws.columns:
        letter = get_column_letter(col[0].column)
        width = min_w
        for cell in col:
            if cell.value is None:
                continue
            width = max(width, min(max_w, len(str(cell.value)) + 2))
        ws.column_dimensions[letter].width = width


def excel_interp(
    x: str,
    value_col: str,
    rating_end: int,
    x_col: str = "I",
) -> str:
    """Local linear interpolation on Courbe_de_tarage: value vs x_col (Ind or Q or HW)."""
    xs = f"Courbe_de_tarage!${x_col}$4:${x_col}${rating_end}"
    val = f"Courbe_de_tarage!${value_col}$4:${value_col}${rating_end}"
    m = f"MATCH({x},{xs},1)"
    forecast = (
        f"FORECAST({x},"
        f"INDEX({val},{m}):INDEX({val},{m}+1),"
        f"INDEX({xs},{m}):INDEX({xs},{m}+1))"
    )
    return (
        f"IFERROR({forecast},"
        f"IFERROR(INDEX({val},{m}),INDEX({val},1)))"
    )


def main() -> None:
    p = CulvertDitchParams()  # site defaults: beveled, S0 from inverts, surface overflow
    Q_design = 9.0
    pond_area = 50.0
    t_rise = 40.0
    t_fall = 80.0
    dt_min = 5.0

    summary = summarize(Q_design, p)
    result = solve_HW_for_Q(Q_design, p)
    rating = build_rating_curve(p, n=41)
    rating_end = 3 + len(rating)  # last data row on Courbe_de_tarage

    # Python routing (reference / peak highlight only; Excel has live Puls formulas)
    t_list, q_list = default_triangle_hydrograph(Q_design, t_rise, t_fall, dt_min)
    route = route_level_pool(t_list, q_list, p, pond_area_m2=pond_area, HW0=0.0)
    peak = max(route, key=lambda s: s.WSE)

    wb = Workbook()

    # --- Sheet 1: Paramètres ---
    ws = wb.active
    ws.title = "Parametres"
    ws["A1"] = "Modèle composé — Ponceau + fossé (remblai)"
    ws["A1"].font = Font(bold=True, size=14)
    ws.merge_cells("A1:C1")
    ws["A2"] = "Outil préliminaire 1D — pas un substitut à HEC-RAS / HY-8"
    ws["A2"].font = Font(italic=True, color="64748B")

    rows = [
        ("Section", "Paramètre", "Valeur", "Unité / note"),
        ("Géométrie", "Diamètre ponceau D", p.D, "m (1050 mm)"),
        ("Géométrie", "Longueur L", p.L, "m"),
        ("Géométrie", "Largeur fond fossé b", p.b, "m"),
        ("Géométrie", "Talus z", p.z, "H:V"),
        ("Cote", "Invert amont", p.elev_invert, "m"),
        ("Cote", "Invert aval", p.elev_invert_ds, "m"),
        ("Cote", "Max hauteur d'eau", p.elev_max, "m"),
        ("Cote", "Clé du tuyau (crown)", p.elev_invert + p.D, "m = invert + D"),
        ("Hydraulique", "Pente S0 = Δz/L", round(p.S0, 6), "m/m"),
        ("Hydraulique", "n ponceau", p.n_pipe, "Manning"),
        ("Hydraulique", "Entrée", p.entrance, f"Ke={p.Ke}; coeffs HDS-5 Form2"),
        ("Hydraulique", "Tailwater TW", p.TW, "m au-dessus invert aval (inconnu → 0)"),
        ("Débordement", "Mode", p.overflow_mode, "surface = fossé enrochement / macropores"),
        ("Débordement", "Début débordement", p.overflow_depth(), "m au-dessus invert (= crown)"),
        ("Débordement", "n surface (rocher)", p.n_surface, "si mode surface/both"),
        ("Débordement", "d50 remblai", p.d50, "m (si mode porous)"),
        ("Débordement", "Porosité", p.n_porosity, "-"),
        ("Débordement", "Cd_rock", p.Cd_rock, "calage poreux"),
        ("Débit", "Q design (permanent)", "=Resultat_Q9!B4", "m³/s — lié à Resultat_Q9 (éditer là-bas)"),
    ]
    for i, row in enumerate(rows, start=4):
        for j, val in enumerate(row, start=1):
            cell = ws.cell(i, j, val)
            cell.border = THIN
            if i == 4:
                continue
            # Yellow = editable inputs; skip formula-linked Q design (last row)
            if j == 3 and i > 4 and not (isinstance(val, str) and val.startswith("=")):
                cell.fill = YELLOW
    style_header(ws, 4, 4)
    ws["A26"] = (
        "Pour l'hydrogramme / routing: éditer les jaunes sur Hydrogramme_entree "
        "(Q pointe, Montée, Descente, Pond, dt) — formules Excel live. "
        "Si vous changez D, n, L, S0…: python build_excel.py"
    )
    ws["A26"].font = Font(italic=True, size=10, color="64748B")
    autosize(ws)

    # --- Sheet: Formules & explications ---
    wsF = wb.create_sheet("Formules_explications", 1)
    wsF["A1"] = "Comment les valeurs sont calculées (formules + méthode)"
    wsF["A1"].font = Font(bold=True, size=14)
    wsF.column_dimensions["A"].width = 28
    wsF.column_dimensions["B"].width = 95

    lines = [
        ("Important", "Hydrogramme_entree + Routing_stockage = FORMULES Excel live. Changez Q pointe (9→12), Montée, Descente, Pond A ou dt → recalcul auto. Courbe Q(HW) = Python: si D/n/L change → python build_excel.py"),
        ("", ""),
        ("1. Cotes", ""),
        ("HW", "Profondeur d'eau amont au-dessus de l'invert du ponceau (m)"),
        ("WSE", "WSE = invert_amont + HW   →   35.36 + HW"),
        ("Clé (crown)", "elev_clé = invert_amont + D = 35.36 + 1.05 = 36.41 m"),
        ("S0", "S0 = (invert_amont - invert_aval) / L = (35.36 - 34.47) / 50.9 ≈ 0.0175 m/m"),
        ("", ""),
        ("2. Courbe de tarage = quoi?", ""),
        ("Définition", "Table débit évacuable pour chaque HW. On fixe HW, on calcule Q. Ce n'est PAS un hydrogramme (Q vs temps)."),
        ("Construction", "HW = 0, 0.05, … Hmax : Q_total(HW) = Q_pipe(HW) + Q_overflow(HW)"),
        ("Colonnes live", "S = S_geo + PondA*HW ; Ind = 2*S/(dt_sec) + Q_total  (pour routing Puls)"),
        ("", ""),
        ("3. Q_ponceau (FHWA HDS-5 + Manning)", ""),
        ("Contrôle d'entrée", "Forme 2 SI: HW/D = K [Q/(Ku*A*sqrt(D))]^M (non subm.) ; HW/D = c [Q/(Ku*A*sqrt(D))]^2 + Y (subm.). Ku=1.811. Biseau: K=0.0018, M=2.5, c=0.030, Y=0.74"),
        ("Contrôle de sortie", "Plein tuyau: H = (1+Ke)*V^2/(2g) + n^2*V^2*L/R^(4/3), R=D/4, Ke=0.2"),
        ("Q retenu", "Q_pipe = min(Q_entrée, Q_sortie) au même HW"),
        ("", ""),
        ("4. Q_débordement surface (HW > D)", ""),
        ("Seuil", "Si HW <= D : Q_overflow = 0.  Si HW > D : y = HW - D"),
        ("Aire A", "A = (b + z*y) * y     b=2, z=2"),
        ("Périmètre P", "P = b + 2*y*sqrt(1+z^2)"),
        ("Rayon R", "R = A / P"),
        ("FORMULE Manning", "Q_overflow = (1/n) * A * R^(2/3) * S0^(1/2)     n≈0.045"),
        ("", ""),
        ("5. Pourquoi Manning et pas Bernoulli au-dessus de D?", ""),
        ("Bernoulli EST utilisé", "Pour le tuyau (contrôle sortie): HW = TW + (1+Ke)*V^2/(2g) + pertes"),
        ("Pourquoi pas orifice Bernoulli", "Au-dessus de la clé: long fossé rugueux, pas un orifice court. Q=Cd*A*sqrt(2gH) ignore L, n, pente → surestime"),
        ("Résumé", "Pipe = HDS-5 + énergie. Overflow fossé = Manning canal ouvert."),
        ("", ""),
        ("6. Régime permanent (Resultat_Q9) — FORMULES LIVE", ""),
        ("Q design", "Cellule jaune B4: changez 9→12. Les lignes suivantes lisent la Courbe_de_tarage."),
        ("Méthode", "On cherche HW tel que Q_total(HW) ≈ Q_design (interpolation sur col. E de la courbe)"),
        ("HW / WSE / Q_pipe / Q_débord", "Formules Excel = interpolation inverse Q→HW, puis lecture des colonnes"),
        ("", ""),
        ("6b. Colonne Routing « 2S/dt−Q » — à quoi ça sert?", ""),
        ("Nom exact", "2*S/dt_sec − Q_out   (PAS « 2S+dt−Q »)"),
        ("Rôle", "Terme de report de la méthode Puls. Il mémorise l'état du pas actuel pour calculer le suivant."),
        ("Formule du pas suivant", "RHS_suivant = (2S/dt − Q)_actuel + Q_in_actuel + Q_in_suivant"),
        ("Puis", "On cherche sur Courbe_de_tarage la ligne où Ind (= 2S/dt+Q) ≈ RHS → nouveau Q_out, HW, S"),
        ("Sans cette colonne", "Le routing ne pourrait pas enchaîner les pas de temps correctement"),
        ("", ""),
        ("6c. Feuille Comparaison_modes — à quoi ça sert?", ""),
        ("But", "Comparer 3 façons de modéliser le débordement AU-DESSUS de la clé, pour le MÊME Q permanent"),
        ("porous", "Seulement écoulement dans les vides du remblai (Wilkins) — débit trop faible pour ~9 m³/s"),
        ("surface (défaut)", "Manning fossé rugueux / macropores — c'est le mode utilisé partout ailleurs dans le classeur"),
        ("both", "Poreux jusqu'au sommet du remblai + surface libre au-dessus"),
        ("Lecture", "Regardez WSE et « Sous 37.4? ». porous échoue; surface et both passent sous 37.4 m"),
        ("Pas live", "Table calculée à la construction (Python). Pour un autre Q: changez B3 puis python build_excel.py — ou ignorez cette feuille au quotidien"),
        ("", ""),
        ("7. Hydrogramme d'entrée — FORMULES EXCEL LIVE", ""),
        ("Où éditer", "Feuille Hydrogramme_entree: B4=Pond A ; B5=Q pointe ; B6=Montée (min) ; B7=Descente (min) ; B8=dt (min)"),
        ("Changer 9 → 12", "Mettre 12 dans B5. Colonne Q_in + feuille Routing_stockage se mettent à jour."),
        ("Temps t", "A11=0 ; puis A12 = SI(A11+dt > Montée+Descente; \"\"; A11+dt)"),
        ("Montée", "Si t <= Montée:  Q_in = Qpointe * (t / Montée)"),
        ("Descente", "Si t > Montée:   Q_in = Qpointe * (1 - (t-Montée)/Descente)"),
        ("Formule Excel Q_in", "=SI(A11=\"\";\"\";SI(A11<=$B$6;$B$5*A11/$B$6;MAX(0;$B$5*(1-(A11-$B$6)/$B$7))))"),
        ("Exemple", "Q=9, Montée=40: t=20→4.5; t=40→9; t=60→6.75.  Q=12: t=20→6; t=40→12"),
        ("", ""),
        ("8. Routing stockage — FORMULES EXCEL (méthode Puls)", ""),
        ("Bilan", "dS/dt = Q_in - Q_out"),
        ("dt_sec", "dt_sec = dt_min * 60  (Hydrogramme_entree!B8)"),
        ("Indicateur", "Ind = 2*S/dt_sec + Q_out   (colonne I de Courbe_de_tarage)"),
        ("Étape 0", "t=0: HW=0; Q_out=0; S=0"),
        ("Étape n", "RHS = (2*S_prev/dt_sec - Q_out_prev) + Q_in_prev + Q_in_n"),
        ("Lecture courbe", "Interpoler où Ind ≈ RHS → Q_out, HW, S, Q_pipe, Q_overflow"),
        ("WSE", "WSE = 35.36 + HW"),
        ("S", "S = S_geo(tuyau+fossé) + PondA*HW"),
        ("", ""),
        ("9. Fichiers source", ""),
        ("hydraulics.py", "Tarage Q(HW) et S_geo"),
        ("build_excel.py", "Génère le classeur + formules live"),
        ("run_model.py", "Résultat permanent terminal"),
    ]
    wsF["A3"] = "Sujet"
    wsF["B3"] = "Formule / explication"
    style_header(wsF, 3, 2)
    for i, (a, b) in enumerate(lines, start=4):
        wsF.cell(i, 1, a)
        wsF.cell(i, 2, b)
        wsF.cell(i, 2).alignment = Alignment(wrap_text=True, vertical="top")
        if a and not b:
            wsF.cell(i, 1).font = Font(bold=True, color="0F5C5C")
        wsF.row_dimensions[i].height = 35 if len(b) > 80 else 18

    # --- Sheet: Resultat Q (LIVE via rating-curve lookup) ---
    ws2 = wb.create_sheet("Resultat_Q9")
    ws2["A1"] = "Résultat régime permanent — FORMULES EXCEL LIVE (changez Q design en B4)"
    ws2["A1"].font = Font(bold=True, size=14)
    ws2["A2"] = (
        "Éditez B4 (jaune). HW / WSE / débits sont lus sur Courbe_de_tarage "
        "(Q_total ≈ Q design). Ce n'est PAS l'hydrogramme: c'est un débit constant."
    )
    ws2["A2"].font = Font(italic=True, color="64748B")
    ws2.merge_cells("A2:D2")

    # Headers
    for j, h in enumerate(("Grandeur", "Valeur", "Unité", "Comment obtenu"), start=1):
        ws2.cell(3, j, h)
    style_header(ws2, 3, 4)

    q_cell = "$B$4"
    # Row 4: Q design editable
    ws2["A4"] = "Q design"
    ws2["B4"] = Q_design
    ws2["B4"].fill = YELLOW
    ws2["B4"].border = THIN
    ws2["C4"] = "m³/s"
    ws2["D4"] = "ÉDITER ICI (ex. 9 → 12). Jaune = entrée."

    # Live lookups: interpolate rating where Q_total (col E) ≈ Q design
    live_rows = [
        (5, "HW (profondeur amont)", excel_interp(q_cell, "A", rating_end, x_col="E"), "m",
         "Interpolation Courbe_de_tarage: Q_total → HW"),
        (6, "WSE amont", f"=35.36+B5", "m", "WSE = 35.36 + HW"),
        (7, "Q_ponceau", excel_interp(q_cell, "C", rating_end, x_col="E"), "m³/s",
         "Q_pipe au même HW (courbe)"),
        (8, "Q_débordement (fossé/rocher)", excel_interp(q_cell, "D", rating_end, x_col="E"), "m³/s",
         "Q_overflow au même HW (courbe)"),
        (9, "Q_total", f"=B7+B8", "m³/s", "Doit ≈ Q design (B4)"),
        (10, "Contrôle (approx.)",
         f'=IFERROR(INDEX(Courbe_de_tarage!$F$4:$F${rating_end},'
         f'MATCH({q_cell},Courbe_de_tarage!$E$4:$E${rating_end},1)),"-")',
         "-", "Texte du point de courbe le plus proche"),
        (11, "Capacité ponceau à la clé",
         excel_interp("1.05", "C", rating_end, x_col="A"), "m³/s",
         "Q_pipe quand HW = D = 1.05 m"),
        (12, "Débordement actif?",
         '=IF(B5>1.05,"Oui","Non")', "-", "Oui si HW > clé (D=1.05)"),
        (13, "Dépasse elev_max 37.4?",
         '=IF(B6>37.4,"Oui","Non")', "-", "Oui si WSE > 37.4 m"),
    ]
    for row, label, formula, unit, note in live_rows:
        ws2.cell(row, 1, label).border = THIN
        cell = ws2.cell(row, 2, f"={formula}" if not str(formula).startswith("=") else formula)
        cell.border = THIN
        cell.fill = OK
        if row in (5, 6, 7, 8, 9, 11):
            cell.number_format = "0.000"
        ws2.cell(row, 3, unit).border = THIN
        ws2.cell(row, 4, note).border = THIN

    # Conditional: warn fill on B13 when Oui — use CF
    warn_fill = PatternFill(start_color="FDE68A", end_color="FDE68A", fill_type="solid")
    ws2.conditional_formatting.add(
        "B13",
        FormulaRule(formula=['B13="Oui"'], fill=warn_fill),
    )

    ws2["A15"] = (
        "Interprétation: si Q_ponceau < Q design, l'excédent passe en débordement (fossé). "
        "Si « Dépasse 37.4? » = Oui, capacité insuffisante sous la cote max. "
        "Pour un orage dans le temps: Hydrogramme_entree + Routing_stockage "
        "(B5 hydrogramme peut être le même chiffre que B4 ici, ou différent)."
    )
    ws2["A15"].alignment = Alignment(wrap_text=True)
    ws2.merge_cells("A15:D17")
    ws2["A18"] = (
        "Note: Resultat_Q9 = débit CONSTANT. Hydrogramme = débit qui varie dans le temps. "
        "Les deux utilisent la même courbe de tarage."
    )
    ws2["A18"].font = Font(italic=True, size=10, color="64748B")
    ws2.merge_cells("A18:D18")
    autosize(ws2)

    # --- Sheet: Courbe de tarage (+ S_geo, S live, Ind live) ---
    ws3 = wb.create_sheet("Courbe_de_tarage")
    ws3["A1"] = "Courbe de tarage Q = f(HW) — ponceau + débordement"
    ws3["A1"].font = Font(bold=True, size=14)
    ws3["A2"] = (
        "Q_pipe / Q_débord / Q_total = Python (fixe tant que géométrie fixe). "
        "Colonnes S et Ind = formules Excel live (dépendent de Pond A et dt). "
        "Utilisées par Routing_stockage (méthode Puls)."
    )
    ws3["A2"].font = Font(italic=True, color="64748B")
    ws3.merge_cells("A2:I2")
    headers = [
        "HW (m)",
        "WSE=35.36+HW",
        "Q_ponceau",
        "Q_débord.",
        "Q_total",
        "Contrôle",
        "S_geo (m³)",
        "S=S_geo+Pond*HW",
        "Ind=2S/dt+Q",
    ]
    for j, h in enumerate(headers, start=1):
        ws3.cell(3, j, h)
    style_header(ws3, 3, 9)

    for i, pt in enumerate(rating, start=4):
        s_geo = storage_m3(pt.HW, p, pond_area_m2=0.0)
        ws3.cell(i, 1, round(pt.HW, 4)).border = THIN
        c_wse = ws3.cell(i, 2, f"=35.36+A{i}")
        c_wse.border = THIN
        c_wse.number_format = "0.000"
        for j, v in enumerate([pt.Q_pipe, pt.Q_ditch, pt.Q_total, pt.control], start=3):
            cell = ws3.cell(i, j, round(v, 4) if isinstance(v, float) else v)
            cell.border = THIN
        # S_geo static
        c_sg = ws3.cell(i, 7, round(s_geo, 4))
        c_sg.border = THIN
        c_sg.number_format = "0.00"
        # S live = S_geo + PondA * HW
        c_s = ws3.cell(i, 8, f"=G{i}+Hydrogramme_entree!$B$4*A{i}")
        c_s.border = THIN
        c_s.number_format = "0.00"
        # Ind = 2*S/(dt_sec) + Q_total
        c_ind = ws3.cell(i, 9, f"=2*H{i}/(Hydrogramme_entree!$B$8*60)+E{i}")
        c_ind.border = THIN
        c_ind.number_format = "0.00"
        if abs(pt.Q_total - 9.0) < 0.15 and pt.HW > 1.5:
            for col in range(1, 7):
                ws3.cell(i, col).fill = YELLOW

    ws3.cell(rating_end + 2, 1, "Ligne jaune ≈ Q_total ≈ 9 m³/s (référence)")
    ws3.cell(
        rating_end + 3,
        1,
        "H = S_geo + PondA*HW ; I = 2*S/(dt*60)+Q_total. PondA et dt = Hydrogramme_entree B4 et B8.",
    )
    ws3.cell(rating_end + 3, 1).font = Font(italic=True, size=10, color="64748B")
    autosize(ws3)

    # --- Sheet: Hydrogramme entrée (LIVE formulas) ---
    ws4 = wb.create_sheet("Hydrogramme_entree")
    ws4["A1"] = "Hydrogramme d'entrée Q(t) — TRIANGLE avec FORMULES EXCEL LIVE"
    ws4["A1"].font = Font(bold=True, size=13)
    ws4["A2"] = (
        "Éditez les cellules JAUNES (B4–B8). Exemple: pour Q=12, mettez 12 dans B5. "
        "La colonne Q_in et la feuille Routing_stockage se recalculent automatiquement. "
        "Formules: voir Formules_explications §7."
    )
    ws4["A2"].font = Font(italic=True, color="64748B")
    ws4.merge_cells("A2:D2")

    ws4["A3"] = "Options (éditer ici)"
    ws4["A3"].font = Font(bold=True)
    inputs = [
        (4, "Pond amont A (m²)", pond_area, "0 = tuyau+fossé seulement; >0 = bassin amont simplifié"),
        (5, "Q pointe triangle (m³/s)", Q_design, "Changer 9 → 12 ici pour un nouvel hydrogramme"),
        (6, "Montée (min)", t_rise, "Durée de la montée jusqu'à la pointe"),
        (7, "Descente (min)", t_fall, "Durée de la descente après la pointe"),
        (8, "Pas dt (min)", dt_min, "Pas de temps de l'hydrogramme / routing"),
    ]
    for row, label, val, note in inputs:
        ws4.cell(row, 1, label)
        c = ws4.cell(row, 2, val)
        c.fill = YELLOW
        c.border = THIN
        ws4.cell(row, 3, note).font = Font(italic=True, size=9, color="64748B")

    ws4["A9"] = (
        "Formule Q_in: SI(t<=Montée; Qpointe*t/Montée; MAX(0; Qpointe*(1-(t-Montée)/Descente)))"
    )
    ws4["A9"].font = Font(size=10, color="0F5C5C")

    ws4["A10"] = "t (min)"
    ws4["B10"] = "Q_in (m³/s)  ← formule"
    style_header(ws4, 10, 2)

    # Row 11 = t=0; subsequent rows chain on dt until rise+fall
    first_data = 11
    last_data = first_data + N_TIME_ROWS - 1
    ws4.cell(first_data, 1, 0).border = THIN
    ws4.cell(
        first_data,
        2,
        f'=IF(A{first_data}="","",IF(A{first_data}<=$B$6,$B$5*A{first_data}/$B$6,'
        f"MAX(0,$B$5*(1-(A{first_data}-$B$6)/$B$7))))",
    ).border = THIN
    ws4.cell(first_data, 2).number_format = "0.0000"

    for r in range(first_data + 1, last_data + 1):
        prev = r - 1
        # t = previous + dt if still within event, else blank
        ws4.cell(
            r,
            1,
            f'=IF(A{prev}="","",IF(A{prev}+$B$8>$B$6+$B$7,"",A{prev}+$B$8))',
        ).border = THIN
        ws4.cell(
            r,
            2,
            f'=IF(A{r}="","",IF(A{r}<=$B$6,$B$5*A{r}/$B$6,'
            f"MAX(0,$B$5*(1-(A{r}-$B$6)/$B$7))))",
        ).border = THIN
        ws4.cell(r, 2).number_format = "0.0000"

    # Light yellow on Q_in to show computed (not manually typed)
    for r in range(first_data, last_data + 1):
        ws4.cell(r, 2).fill = PatternFill("solid", fgColor="E0F2FE")

    autosize(ws4)

    # --- Sheet: Routing_stockage (LIVE Puls formulas) ---
    wsR = wb.create_sheet("Routing_stockage")
    wsR["A1"] = "Routing stockage — FORMULES EXCEL LIVE (méthode Puls)"
    wsR["A1"].font = Font(bold=True, size=13)
    wsR["A2"] = (
        "dS/dt = Qin - Qout.  À chaque pas: RHS = (2S/dt - Q)_prev + Qin_prev + Qin. "
        "On interpole la Courbe_de_tarage où Ind ≈ RHS. "
        "Changez Q pointe / Pond / dt sur Hydrogramme_entree → cette feuille se met à jour. "
        "Détail → Formules_explications §8."
    )
    wsR["A2"].font = Font(italic=True, color="64748B")
    wsR.merge_cells("A2:K2")

    hdr = [
        "t (min)",
        "Q_in",
        "Q_pipe",
        "Q_overflow",
        "Q_out",
        "HW (m)",
        "WSE (m)",
        "S (m³)",
        "WSE>37.4?",
        "RHS (Ind cible)",
        "2S/dt−Q (report Puls)",
    ]
    for j, h in enumerate(hdr, start=1):
        wsR.cell(4, j, h)
    style_header(wsR, 4, 11)

    wsR["A3"] = (
        "Colonne « 2S/dt−Q » = terme de report Puls: RHS_suivant = cette_valeur + Qin_actuel + Qin_suivant. "
        "Pas un débit physique — c'est un auxiliaire de calcul."
    )
    wsR["A3"].font = Font(italic=True, size=9, color="64748B")
    wsR.merge_cells("A3:K3")

    # Excel routing rows align with hydrogramme rows
    r0 = 5  # first routing data row (= hydro first_data)
    r_last = r0 + N_TIME_ROWS - 1
    dt_ref = "Hydrogramme_entree!$B$8"

    # Initial state t=0
    hydro_r = first_data
    wsR.cell(r0, 1, f"=Hydrogramme_entree!A{hydro_r}").border = THIN
    wsR.cell(r0, 2, f"=Hydrogramme_entree!B{hydro_r}").border = THIN
    wsR.cell(r0, 3, 0).border = THIN  # Q_pipe
    wsR.cell(r0, 4, 0).border = THIN  # Q_overflow
    wsR.cell(r0, 5, 0).border = THIN  # Q_out
    wsR.cell(r0, 6, 0).border = THIN  # HW
    wsR.cell(r0, 7, f"=IF(A{r0}=\"\",\"\",35.36+F{r0})").border = THIN
    wsR.cell(r0, 8, 0).border = THIN  # S
    wsR.cell(r0, 9, f'=IF(G{r0}="","",IF(G{r0}>37.4,"OUI",""))').border = THIN
    wsR.cell(r0, 10, "").border = THIN
    wsR.cell(r0, 11, f"=IF(A{r0}=\"\",\"\",2*H{r0}/({dt_ref}*60)-E{r0})").border = THIN

    for i in range(1, N_TIME_ROWS):
        r = r0 + i
        prev = r - 1
        hydro_r = first_data + i
        rhs = f"K{prev}+B{prev}+B{r}"

        wsR.cell(r, 1, f"=Hydrogramme_entree!A{hydro_r}").border = THIN
        wsR.cell(r, 2, f"=Hydrogramme_entree!B{hydro_r}").border = THIN

        # Only compute when t is present
        def gated(formula: str) -> str:
            return f'=IF(A{r}="","",{formula})'

        wsR.cell(r, 3, gated(excel_interp(rhs, "C", rating_end))).border = THIN  # Q_pipe
        wsR.cell(r, 4, gated(excel_interp(rhs, "D", rating_end))).border = THIN  # Q_overflow
        wsR.cell(r, 5, gated(excel_interp(rhs, "E", rating_end))).border = THIN  # Q_out
        wsR.cell(r, 6, gated(excel_interp(rhs, "A", rating_end))).border = THIN  # HW
        wsR.cell(r, 7, f'=IF(A{r}="","",35.36+F{r})').border = THIN
        wsR.cell(r, 8, gated(excel_interp(rhs, "H", rating_end))).border = THIN  # S
        wsR.cell(r, 9, f'=IF(G{r}="","",IF(G{r}>37.4,"OUI",""))').border = THIN
        wsR.cell(r, 10, gated(rhs)).border = THIN  # RHS
        wsR.cell(r, 11, f'=IF(A{r}="","",2*H{r}/({dt_ref}*60)-E{r})').border = THIN

        for col in (2, 3, 4, 5, 6, 7, 8, 10, 11):
            wsR.cell(r, col).number_format = "0.0000"

    for col in (2, 3, 4, 5, 6, 7, 8, 11):
        wsR.cell(r0, col).number_format = "0.0000"

    # Conditional highlight when WSE is max among non-blank rows
    # (simple: yellow if G equals MAX of column — works in Excel)
    yellow_fill = PatternFill(start_color="FFF59D", end_color="FFF59D", fill_type="solid")
    wsR.conditional_formatting.add(
        f"A{r0}:K{r_last}",
        FormulaRule(
            formula=[f'AND($A{r0}<>"",$G{r0}=MAX($G${r0}:$G${r_last}))'],
            fill=yellow_fill,
        ),
    )

    summary_row = r_last + 2
    wsR.cell(summary_row, 1, "Résumé (formules live)").font = Font(bold=True)
    wsR.cell(summary_row + 1, 1, "WSE max")
    wsR.cell(summary_row + 1, 2, f"=MAX(G{r0}:G{r_last})")
    wsR.cell(summary_row + 1, 2).fill = OK
    wsR.cell(summary_row + 1, 3, "m")
    wsR.cell(summary_row + 2, 1, "S max")
    wsR.cell(summary_row + 2, 2, f"=MAX(H{r0}:H{r_last})")
    wsR.cell(summary_row + 2, 3, "m³")
    wsR.cell(summary_row + 3, 1, "Q_in max")
    wsR.cell(summary_row + 3, 2, f"=MAX(B{r0}:B{r_last})")
    wsR.cell(summary_row + 3, 3, "m³/s")
    wsR.cell(summary_row + 4, 1, "Réf. Python (build)")
    wsR.cell(summary_row + 4, 2, round(peak.WSE, 3))
    wsR.cell(summary_row + 4, 3, "m WSE max au moment du build (Puls Excel ≈ ce nombre)")

    wsR.cell(
        summary_row + 6,
        1,
        "Ligne jaune (mise en forme conditionnelle) = pas où WSE = WSE max. "
        "Si vous changez Q pointe à 12 sur Hydrogramme_entree!B5, ce résumé change tout seul.",
    )
    wsR.merge_cells(
        start_row=summary_row + 6, start_column=1, end_row=summary_row + 7, end_column=11
    )
    autosize(wsR)

    # --- Sheet: Notes ---
    wsN = wb.create_sheet("Hydrogramme_notes")
    wsN["A1"] = "Hyétogramme vs hydrogramme — et ce que fait ce classeur"
    wsN["A1"].font = Font(bold=True, size=13)
    notes = [
        "",
        "Hyétogramme = pluie i(t) [mm/h]. Hydrogramme = débit Q(t) [m³/s] à l'entrée du ponceau.",
        "",
        "COMMENT CHANGER LE DÉBIT DE POINTE (ex. 9 → 12):",
        "  1. Ouvrir Hydrogramme_entree",
        "  2. Mettre 12 dans la cellule jaune B5 (Q pointe)",
        "  3. La colonne Q_in et Routing_stockage se recalculent (formules Excel)",
        "",
        "Autres jaunes: B4=Pond A, B6=Montée, B7=Descente, B8=dt.",
        "",
        "Formule triangle:",
        "  montée:   Qin = Qpointe * t / Montée",
        "  descente: Qin = Qpointe * (1 - (t - Montée) / Descente)",
        "",
        "Routing = méthode Puls (pas besoin de relancer Python pour Q pointe / pond / dt).",
        "Si vous changez D, n, L, pente: relancer python build_excel.py (courbe de tarage).",
    ]
    for i, line in enumerate(notes, start=2):
        wsN.cell(i, 1, line)
    wsN.column_dimensions["A"].width = 110

    # --- Sheet: Comparaison modes ---
    ws5 = wb.create_sheet("Comparaison_modes")
    ws5["A1"] = "Comparaison des modes de débordement (référence pédagogique)"
    ws5["A1"].font = Font(bold=True, size=12)
    ws5["A2"] = (
        "Cette feuille compare 3 HYPOTHÈSES pour le débit AU-DESSUS de la clé du tuyau, "
        "à un Q permanent fixe (B3). Elle n'est PAS utilisée par l'hydrogramme ni le routing "
        "(ceux-ci utilisent toujours le mode « surface »)."
    )
    ws5["A2"].font = Font(italic=True, color="64748B")
    ws5.merge_cells("A2:F2")

    ws5["A3"] = "Q permanent de comparaison"
    ws5["B3"] = Q_design
    ws5["B3"].fill = YELLOW
    ws5["C3"] = "m³/s — changez puis relancez python build_excel.py pour recalculer ce tableau"
    ws5["C3"].font = Font(italic=True, size=9, color="64748B")

    hdr = ["Mode", "Signification", "WSE (m)", "Q_pipe", "Q_overflow", "Q_total", "Sous 37.4?"]
    for j, h in enumerate(hdr, start=1):
        ws5.cell(5, j, h)
    style_header(ws5, 5, 7)

    mode_notes = {
        "porous": "Eau seulement dans les pores du remblai (Wilkins) — très faible débit",
        "surface": "Manning fossé rugueux / macropores — DÉFAUT du modèle",
        "both": "Poreux + surface libre au-dessus du remblai",
    }
    for i, mode in enumerate(("porous", "surface", "both"), start=6):
        pm = CulvertDitchParams(overflow_mode=mode)
        r = solve_HW_for_Q(Q_design, pm)
        ok = "Oui" if r.Q_total >= Q_design - 1e-3 and r.WSE <= pm.elev_max + 1e-6 else "Non / limite"
        vals = [
            mode,
            mode_notes[mode],
            round(r.WSE, 3),
            round(r.Q_pipe, 3),
            round(r.Q_ditch, 3),
            round(r.Q_total, 3),
            ok,
        ]
        for j, v in enumerate(vals, start=1):
            cell = ws5.cell(i, j, v)
            cell.border = THIN
            if mode == "surface":
                cell.fill = OK
            elif ok.startswith("Non"):
                cell.fill = WARN

    ws5["A10"] = (
        "Comment lire: la ligne « surface » (verte) est celle du reste du classeur. "
        "« porous » montre pourquoi on n'utilise pas seulement l'écoulement dans le remblai: "
        "WSE trop haut / capacité insuffisante. "
        "B3 jaune n'est PAS live (besoin de 3 courbes différentes) — rebuild Python si vous changez B3."
    )
    ws5["A10"].alignment = Alignment(wrap_text=True)
    ws5.merge_cells("A10:G12")
    autosize(ws5)

    wb.save(OUT)
    print(f"Wrote {OUT}")
    print(
        f"Routing peak WSE={peak.WSE:.3f} m at t={peak.t_min:.0f} min "
        f"(Qin={peak.Q_in:.2f}, Qout={peak.Q_out:.2f})"
    )
    print(f"Live Excel rows: {N_TIME_ROWS}; rating rows 4..{rating_end}")


if __name__ == "__main__":
    main()
