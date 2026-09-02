# Volume de rétention — ponceau Ø900

Excel pour estimer le **volume de rétention** requis en amont du Ø900 qui contrôle la sortie.

## Fichier

`Volume_Retention_Ponceau_900.xlsx`

| Feuille | Contenu |
|---------|---------|
| **Parametres** | Configuration Ø1500 → rétention → Ø900 → Ø1200; Qcap, facteur de sécurité, aire bassin |
| **Hydrogramme** | Qin(t) + graphique |
| **Calcul_A** | Routage avec **Qout constant** = capacité Ø900 (1,77 m³/s) |
| **Calcul_B** | Routage **Qout = f(H)** orifice Ø900 plafonné à Qcap |
| **Methode** | Rappels de calcul |

## Utilisation

1. Ouvrir le `.xlsx` (Excel ou LibreOffice).
2. Ajuster les cellules **jaunes** dans `Parametres` (Qcap, facteur de sécurité, aire).
3. Lire **Vmax** et **V_dimensionnement** sur `Parametres` / `Calcul_A`.

## Reconstruction

```bash
python3 build_retention_excel.py
```

## Résultat indicatif (Qout = 1,77 m³/s)

Avec l’hydrogramme fourni et un routage trapézoïdal : **Vmax ≈ 5 400 m³** (ordre de grandeur cohérent avec ~5 300 m³).
