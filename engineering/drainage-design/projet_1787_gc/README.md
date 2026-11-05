# 1787 GC — Réseau pluvial hybride (optimisé)

Fichier: `Reseau_pluvial_1787_GC_hybride.xlsx`

## Changements (optimisation)

| Avant | Maintenant |
|-------|------------|
| RT saisi (jaune) | **RT calculé** = DART/DA |
| DA_t sur pipes + Qin_tr | **DA_t retiré** — gazon tranchée seulement dans `Tranchees` (plus de double comptage) |
| DA_g / DA_p | Conservés (jaune) → DA, DART dérivés avec C_g / C_p |
| Qp tranchée = underdrain seul | **Qp_ud + Qp_trench (Manning b×y) = Qp_total** |
| Dia_bouch répété | Ø / H regard dans **Inputs** → Vol_bouch auto |

## Colonnes gardées (pas redondantes)

`DART`, `A`, `AR`, `R` restent : chaîne rationnelle pour revue / municipal.

## Lien

`Tranchees!Noeud_aval` = `Calcul_reseau!Amont` → `Qin_tr` ajouté à `Qmax`.

## Pull

```bash
git pull origin cursor/drainage-1787-trench-hybrid-d87f
```

LibreOffice: **Ctrl+Shift+F9** après ouverture.
