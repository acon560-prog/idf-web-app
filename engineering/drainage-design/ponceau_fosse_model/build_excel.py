#!/usr/bin/env python3
"""Build Excel workbook for ponceau + fossé compound model."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from hydraulics import (
    CulvertDitchParams,
    build_rating_curve,
    default_triangle_hydrograph,
    route_level_pool,
    solve_HW_for_Q,
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


def main() -> None:
    p = CulvertDitchParams()  # site defaults: beveled, S0 from inverts, surface overflow
    Q_design = 9.0
    summary = summarize(Q_design, p)
    result = solve_HW_for_Q(Q_design, p)
    rating = build_rating_curve(p, n=41)

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
        ("Débit", "Q design (permanent)", Q_design, "m³/s — hydrogramme = amélioration future"),
    ]
    for i, row in enumerate(rows, start=4):
        for j, val in enumerate(row, start=1):
            cell = ws.cell(i, j, val)
            cell.border = THIN
            if i == 4:
                continue
            if j == 3 and i > 4:
                cell.fill = YELLOW
    style_header(ws, 4, 4)
    ws["A26"] = "Cellules jaunes = entrées principales (recalculer via run_model.py / rebuild_excel.py après changement)."
    ws["A26"].font = Font(italic=True, size=10, color="64748B")
    autosize(ws)

    # --- Sheet 2: Resultat Q=9 ---
    ws2 = wb.create_sheet("Resultat_Q9")
    ws2["A1"] = "Résultat pour Q permanent = 9 m³/s"
    ws2["A1"].font = Font(bold=True, size=14)
    data = [
        ("Grandeur", "Valeur", "Unité"),
        ("Q design", Q_design, "m³/s"),
        ("HW (profondeur amont)", round(result.HW, 3), "m"),
        ("WSE amont", round(result.WSE, 3), "m"),
        ("Q_ponceau", round(result.Q_pipe, 3), "m³/s"),
        ("Q_débordement (fossé/rocher)", round(result.Q_ditch, 3), "m³/s"),
        ("Q_total", round(result.Q_total, 3), "m³/s"),
        ("Contrôle", result.control, "-"),
        ("Capacité ponceau à la clé", round(summary["pipe_capacity_at_crown_m3s"], 3), "m³/s"),
        ("Débordement actif?", "Oui" if summary["overflow_active"] else "Non", "-"),
        ("Dépasse elev_max 37.4?", "Oui" if summary["exceeds_max_stage"] else "Non", "-"),
    ]
    for i, row in enumerate(data, start=3):
        for j, val in enumerate(row, start=1):
            cell = ws2.cell(i, j, val)
            cell.border = THIN
    style_header(ws2, 3, 3)
    # highlight result block
    for r in range(4, 14):
        ws2.cell(r, 2).fill = OK if not summary["exceeds_max_stage"] else WARN
    ws2["A16"] = (
        "Interprétation: le ponceau seul (~3.6 m³/s à la clé, ~4.2 m³/s au WSE de calcul) "
        "est insuffisant pour 9 m³/s. L'excédent (~4.8 m³/s) passe dans le fossé au-dessus de la clé "
        "(mode surface / écoulement préférentiel dans le remblai 8–200 mm). WSE ≈ 37.16 m < 37.4 m."
    )
    ws2["A16"].alignment = Alignment(wrap_text=True)
    ws2.merge_cells("A16:C18")
    ws2["A20"] = (
        "Limite importante: ceci est un régime PERMANENT (Q constant). "
        "Pour un événement réel, un hydrogramme d'entrée Q(t) (et éventuellement stockage) est préférable."
    )
    ws2["A20"].alignment = Alignment(wrap_text=True)
    ws2.merge_cells("A20:C22")
    autosize(ws2)

    # --- Sheet 3: Courbe de tarage ---
    ws3 = wb.create_sheet("Courbe_de_tarage")
    ws3["A1"] = "Courbe de tarage Q = f(HW) — ponceau + débordement"
    ws3["A1"].font = Font(bold=True, size=14)
    headers = ["HW (m)", "WSE (m)", "Q_ponceau (m³/s)", "Q_débordement (m³/s)", "Q_total (m³/s)", "Contrôle"]
    for j, h in enumerate(headers, start=1):
        ws3.cell(3, j, h)
    style_header(ws3, 3, 6)
    for i, pt in enumerate(rating, start=4):
        vals = [pt.HW, pt.WSE, pt.Q_pipe, pt.Q_ditch, pt.Q_total, pt.control]
        for j, v in enumerate(vals, start=1):
            cell = ws3.cell(i, j, round(v, 4) if isinstance(v, float) else v)
            cell.border = THIN
            if abs(pt.Q_total - 9.0) < 0.15 and pt.HW > 1.5:
                cell.fill = YELLOW
    ws3["A46"] = "Ligne jaune ≈ voisinage de Q_total ≈ 9 m³/s"
    autosize(ws3)

    # --- Sheet 4: Hydrogramme entrée (editable concept) ---
    ws4 = wb.create_sheet("Hydrogramme_entree")
    ws4["A1"] = "Hydrogramme d'entrée Q(t) — triangle par défaut (pointe = 9 m³/s)"
    ws4["A1"].font = Font(bold=True, size=13)
    ws4["A2"] = (
        "Colonnes jaunes = hydrogramme utilisé pour le routing. "
        "Modifier t / Qin puis relancer: python build_excel.py "
        "(ou plus tard: calcul Excel direct)."
    )
    ws4["A2"].font = Font(italic=True, color="64748B")
    ws4.merge_cells("A2:D2")

    # Routing options
    ws4["A3"] = "Options routing"
    ws4["A3"].font = Font(bold=True)
    ws4["A4"] = "Pond amont A (m²)"
    ws4["B4"] = 50.0  # small headwater pool assumption
    ws4["B4"].fill = YELLOW
    ws4["C4"] = "0 = seulement stockage tuyau+fossé; >0 ajoute un bassin amont simple"
    ws4["A5"] = "Q pointe triangle"
    ws4["B5"] = Q_design
    ws4["B5"].fill = YELLOW
    ws4["A6"] = "Montée (min)"
    ws4["B6"] = 40
    ws4["B6"].fill = YELLOW
    ws4["A7"] = "Descente (min)"
    ws4["B7"] = 80
    ws4["B7"].fill = YELLOW
    ws4["A8"] = "Pas dt (min)"
    ws4["B8"] = 5
    ws4["B8"].fill = YELLOW

    pond_area = float(ws4["B4"].value)
    t_list, q_list = default_triangle_hydrograph(
        Q_peak=float(ws4["B5"].value),
        t_rise_min=float(ws4["B6"].value),
        t_fall_min=float(ws4["B7"].value),
        dt_min=float(ws4["B8"].value),
    )

    ws4["A10"] = "t (min)"
    ws4["B10"] = "Q_in (m³/s)"
    style_header(ws4, 10, 2)
    for i, (t, q) in enumerate(zip(t_list, q_list), start=11):
        ws4.cell(i, 1, t).border = THIN
        c = ws4.cell(i, 2, round(q, 4))
        c.border = THIN
        c.fill = YELLOW
    autosize(ws4)

    # --- Sheet 5: Routing results ---
    route = route_level_pool(t_list, q_list, p, pond_area_m2=pond_area, HW0=0.0)
    wsR = wb.create_sheet("Routing_stockage")
    wsR["A1"] = "Routing stockage — dS/dt = Q_in − Q_out(WSE)"
    wsR["A1"].font = Font(bold=True, size=13)
    wsR["A2"] = (
        f"Méthode Euler + 1 correcteur; stockage ≈ volume ponceau + fossé trapézoïdal × L"
        f" + pond amont ({pond_area:.0f} m²). TW={p.TW} m (libre)."
    )
    wsR["A2"].font = Font(italic=True, color="64748B")
    wsR.merge_cells("A2:H2")

    hdr = [
        "t (min)",
        "Q_in (m³/s)",
        "Q_pipe (m³/s)",
        "Q_overflow (m³/s)",
        "Q_out (m³/s)",
        "HW (m)",
        "WSE (m)",
        "S (m³)",
        "WSE > 37.4?",
    ]
    for j, h in enumerate(hdr, start=1):
        wsR.cell(4, j, h)
    style_header(wsR, 4, 9)

    peak = max(route, key=lambda s: s.WSE)
    for i, s in enumerate(route, start=5):
        over = "OUI" if s.WSE > p.elev_max + 1e-6 else ""
        vals = [
            s.t_min,
            round(s.Q_in, 4),
            round(s.Q_pipe, 4),
            round(s.Q_overflow, 4),
            round(s.Q_out, 4),
            round(s.HW, 4),
            round(s.WSE, 4),
            round(s.S_m3, 2),
            over,
        ]
        for j, v in enumerate(vals, start=1):
            cell = wsR.cell(i, j, v)
            cell.border = THIN
            if s is peak:
                cell.fill = YELLOW
            if over:
                cell.fill = WARN

    summary_row = 5 + len(route) + 1
    wsR.cell(summary_row, 1, "Résumé").font = Font(bold=True)
    wsR.cell(summary_row + 1, 1, "WSE max")
    wsR.cell(summary_row + 1, 2, round(peak.WSE, 3))
    wsR.cell(summary_row + 1, 3, "m")
    wsR.cell(summary_row + 2, 1, "t au pic de niveau")
    wsR.cell(summary_row + 2, 2, peak.t_min)
    wsR.cell(summary_row + 2, 3, "min")
    wsR.cell(summary_row + 3, 1, "Q_in au même instant")
    wsR.cell(summary_row + 3, 2, round(peak.Q_in, 3))
    wsR.cell(summary_row + 4, 1, "Q_out au même instant")
    wsR.cell(summary_row + 4, 2, round(peak.Q_out, 3))
    wsR.cell(summary_row + 5, 1, "S max (approx)")
    wsR.cell(summary_row + 5, 2, round(max(s.S_m3 for s in route), 1))
    wsR.cell(summary_row + 5, 3, "m³")
    for r in range(summary_row + 1, summary_row + 6):
        wsR.cell(r, 2).fill = OK if peak.WSE <= p.elev_max else WARN

    wsR.cell(
        summary_row + 7,
        1,
        "Ligne jaune = pas de temps du WSE max. "
        "Comparer au Resultat_Q9 (régime permanent): le pic transitoire peut être plus bas grâce au stockage.",
    )
    wsR.merge_cells(start_row=summary_row + 7, start_column=1, end_row=summary_row + 8, end_column=9)
    autosize(wsR)

    # --- Sheet 6: Notes hydro ---
    wsN = wb.create_sheet("Hydrogramme_notes")
    wsN["A1"] = "Hyétogramme vs hydrogramme — et ce que fait ce classeur"
    wsN["A1"].font = Font(bold=True, size=13)
    notes = [
        "",
        "Hyétogramme = pluie i(t) [mm/h]. Hydrogramme = débit Q(t) [m³/s] à l'entrée du ponceau.",
        "",
        "Feuille Hydrogramme_entree : Q(t) triangulaire (pointe 9 m³/s, montée 40 min, descente 80 min).",
        "Feuille Routing_stockage : résout dS/dt = Q_in − Q_out(WSE) avec S = f(HW).",
        "",
        "Pour coller VOTRE hydrogramme: remplacez les Qin jaunes (idéalement via rebuild après édition du script,",
        "ou demandez une version 100% formules Excel).",
        "",
        "Chaîne complète future: hyétogramme → ruissellement (rationnel/SCS) → hydrogramme → ce routing.",
    ]
    for i, line in enumerate(notes, start=2):
        wsN.cell(i, 1, line)
    wsN.column_dimensions["A"].width = 110

    # --- Sheet 7: Comparaison modes ---
    ws5 = wb.create_sheet("Comparaison_modes")
    ws5["A1"] = "Comparaison overflow porous vs surface pour Q=9 (mêmes géométrie/S0)"
    ws5["A1"].font = Font(bold=True, size=12)
    ws5.append([])
    hdr = ["Mode", "WSE (m)", "Q_pipe", "Q_overflow", "Q_total", "Sous 37.4?"]
    ws5.append(hdr)
    style_header(ws5, 3, 6)
    for mode in ("porous", "surface", "both"):
        pm = CulvertDitchParams(overflow_mode=mode)
        r = solve_HW_for_Q(9.0, pm)
        ok = "Oui" if r.Q_total >= 9.0 - 1e-3 and r.WSE <= pm.elev_max + 1e-6 else "Non / limite"
        ws5.append([mode, round(r.WSE, 3), round(r.Q_pipe, 3), round(r.Q_ditch, 3), round(r.Q_total, 3), ok])
    ws5["A8"] = (
        "Note: mode porous (Wilkins) seul ne passe pas ~9 m³/s sous 37.4 m. "
        "Mode surface (fossé rugueux / macropores dans 8–200 mm) est le défaut pratique."
    )
    ws5["A8"].alignment = Alignment(wrap_text=True)
    ws5.merge_cells("A8:F10")
    autosize(ws5)

    wb.save(OUT)
    print(f"Wrote {OUT}")
    print(
        f"Routing peak WSE={peak.WSE:.3f} m at t={peak.t_min:.0f} min "
        f"(Qin={peak.Q_in:.2f}, Qout={peak.Q_out:.2f})"
    )


if __name__ == "__main__":
    main()
