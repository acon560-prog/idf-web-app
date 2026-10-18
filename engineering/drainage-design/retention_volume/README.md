# Volume de rétention — ponceau Ø900

Excel pour estimer le **volume de rétention** et les niveaux d'eau sur **deux zones**:

| Zone | Tronçon | Feuille levé | Routage |
|------|---------|--------------|---------|
| **1** | Ø1500 → Ø900 | `SS_Amont` | Calcul_A / B / C |
| **2** | Ø900 → Ø1200 | `SS_Aval` | `Calcul_Aval_A` |

WSE et Surface sont **jaunes (éditables)** — corriger depuis AutoCAD; ΔWSE / V_pas / V_cumul se recalculent.

## Hypothèse de capacité

- **n = 0,013**, Manning **pleine section** → **Q_plein ≈ 1,668 m³/s** (Méthode A Zone 1)
- **Courbe Q = f(H)** FHWA HDS-5 → feuille **Courbe_QH_900**
- Ø1200 Aval: Q_plein ≈ 4,93 m³/s (`Calcul_Aval_A`)

## Fichier principal

`Volume_Retention_Ponceau_900.xlsx`

| Feuille | Contenu |
|---------|---------|
| **Parametres** | Géométrie + résultats Zone 1 (A/B/C) + Zone 2 |
| **Hydrogramme** | Qin(t) entrée Zone 1 |
| **Calcul_A / B / C** | Routage Zone 1 (contrôle Ø900) |
| **SS_Amont** | Levé Zone 1 — WSE/A éditables |
| **SS_Aval** | Levé Zone 2 — WSE/A éditables |
| **Stage_Storage** | Index comparatif A1+A2 / V1+V2 |
| **Calcul_Aval_A** | Routage Zone 2 (Qin≈sortie Ø900) |
| **Methode** | Rappels |

## Reconstruction

```bash
python3 build_retention_excel.py
```

## GIS export?

Optional: export water-surface polygons from AutoCAD/Civil 3D/GIS per elevation to get areas. **Not required** if you type areas from the plan into the yellow cells.
