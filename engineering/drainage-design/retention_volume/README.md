# Volume de rétention — ponceau Ø900

Excel pour estimer le **volume de rétention** requis en amont du Ø900 qui contrôle la sortie.

## Hypothèse de capacité

- **n = 0,013**, Manning **pleine section**
- Géométrie Ø900 : L = 50,65 m, radiers 34,88 → 34,45 → **Q_plein ≈ 1,668 m³/s**
- Ancienne valeur bureau **1,77 m³/s** : même méthode, léger écart de calcul
- **Inlet vs outlet control** : non déterminé; Q_plein constant reste une 1re estimation (souvent prudente)

## Fichier

`Volume_Retention_Ponceau_900.xlsx`

| Feuille | Contenu |
|---------|---------|
| **Parametres** | Géométrie, calcul Manning, Qout (jaune), facteur, aire; notes IC/OC |
| **Hydrogramme** | Qin(t) + croisements Qin=Qcap |
| **Calcul_A** | Routage **Qout constant** |
| **Calcul_B** | Routage orifice Q=f(H) plafonné (illustration) |
| **Methode** | Rappels |

## Utilisation

1. Ouvrir le `.xlsx`.
2. Ajuster les cellules **jaunes** (`Qout_cap_900`, facteur, aire). Mettre **1,77** pour retrouver l’ancien calcul.
3. Lire **Vmax** / **V_dimensionnement** sur `Parametres`.

## Reconstruction

```bash
python3 build_retention_excel.py
```
