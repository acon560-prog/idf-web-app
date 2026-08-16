# Modèle hydraulique composé — Ponceau + fossé

Outil Python pour simuler le comportement d’un **ponceau circulaire** sous un **fossé trapézoïdal** (remblai granulaire).  
Lorsque la capacité du ponceau est atteinte, le débit excédentaire passe dans le fossé.

## Géométrie (selon votre coupe)

| Paramètre | Valeur |
|-----------|--------|
| Diamètre ponceau `D` | 1,05 m (1050 mm) |
| Longueur `L` | 50,9 m |
| Largeur fond fossé `b` | 2,0 m |
| Talus `z` | 2H:1V |
| Invert | 35,13 m |
| Max hauteur d’eau | 37,4 m |
| Remblai | granulaire 8–200 mm |
| Débit entrant | ≈ 9 m³/s |

## Comportement modélisé

```
Q_total(HW) = Q_ponceau(HW) + Q_fossé(HW)
```

1. **Ponceau** — contrôle d’entrée (FHWA HDS-5 Form 2, SI) et contrôle de sortie (Manning + pertes) ; le plus limitatif gouverne.  
2. **Fossé** — Manning trapézoïdal **au-dessus du seuil de débordement** (par défaut = clé du tuyau / crown).  
   Le remblai 8–200 mm est représenté par un **n élevé** (défaut 0,045).

## Lancer

```bash
cd engineering/drainage-design/ponceau_fosse_model
python3 run_model.py --Q 9 --S0 0.01
python3 run_model.py --Q 9 --S0 0.005 --csv rating_curve.csv --json result.json
```

## Entrées encore requises (à confirmer)

Sans ces valeurs, le modèle utilise des **hypothèses** :

1. **Pente longitudinale `S0`** (m/m) du ponceau / fossé — *critique*  
2. **Matériau / n du tuyau** (béton ≈ 0,012–0,015 ; PEHD ≈ 0,011–0,012)  
3. **n du fossé / remblai** (enrochement grossier ≈ 0,035–0,080)  
4. **Niveau aval (tailwater)** au droit de la sortie  
5. **Type d’entrée** (mur de tête, chanfrein, biseau) — change les coeffs HDS-5  
6. Le fossé coule-t-il **à la surface du remblai** (canal rugueux) ou **à travers** le remblai (milieu poreux / Forchheimer) ?  
   → Version actuelle = **canal rugueux parallèle** (plus simple, courant en pré-dim.)

## Limites

- 1D, stationnaire, préliminaire  
- Pas un substitut à HEC-RAS / HY-8 pour dimensionnement final  
- Le débit ~9 m³/s pour D = 1,05 m est très élevé : le fossé portera une grande part du débit sauf pente très forte
