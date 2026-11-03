# 1787 GC — Réseau pluvial hybride

Excel: `Reseau_pluvial_1787_GC_hybride.xlsx`  
Croquis: `1787-GC-00_Croquis_des_reseaux.pdf`  
Builder: `python3 build_1787_hybrid_excel.py`

## Structure

| Onglet | Rôle |
|--------|------|
| **Guide** | Mode d'emploi |
| **Inputs** | IDF, Manning, porosité, critères V |
| **Zones_tributaires** | SUP croquis (m²) → destination pipe/tranchée |
| **Tranchees** | Bloc B — gazon / tranchée drainante → puisard |
| **Calcul_reseau** | Bloc A — même structure que le modèle ADAPTE (pipes + radiers + couverture + volumes) |
| **Temps_concentration** | tc d'entrée |
| **Resume** | Totaux + checks |

## Lien hydraulique

`Tranchees!Noeud_aval` = `Calcul_reseau!Amont`  
→ `Qin_tranchées` (col AC) ajouté à `Qmax`.

## À faire sur le dossier

1. Remplacer IDs placeholders (`RP-N1`, `RP-S1`, `RP-E1`) par les puisards du plan.
2. Mesurer L, b, H, pente des « tranchées drainantes avec sur-pente ».
3. Brancher IDF locale 1787 dans **Inputs**.
4. Ajuster radiers / couvertures / Ø jusqu'à Check = OK.
