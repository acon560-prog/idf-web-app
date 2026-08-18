# Modèle hydraulique composé — Ponceau + fossé (remblai poreux)

## Données site (mises à jour)

| Paramètre | Valeur |
|-----------|--------|
| `D` | 1,05 m |
| `L` | 50,9 m |
| Invert amont | **35,36 m** |
| Invert aval | **34,47 m** |
| `S0 = Δz/L` | **0,0175** (≈ 0,017) |
| `b`, `z` | 2,0 m ; 2H:1V |
| Max WSE | 37,4 m |
| Entrée | **biseautée (beveled)** → Ke≈0,2 |
| Débordement | Au-dessus de la clé jusqu’à 37,4 m — **mode `surface`** (fossé enrochement / macropores). Mode `porous` (Wilkins) disponible mais **insuffisant pour ~9 m³/s**. |
| Tailwater | **inconnu** → hypothèse exutoire libre (TW=0) |

## Comportement

```
Q_total = Q_ponceau(HW) + Q_remblai_poreux(HW)
```

1. Tant que WSE < clé du tuyau → ponceau seul  
2. Au-delà → écoulement **turbulent dans le granulaire** (formule type Wilkins)  
3. Option `--mode both` : poreux + surface libre au-dessus du remblai  

## Lancer

```bash
cd engineering/drainage-design/ponceau_fosse_model
python3 run_model.py --Q 9 --csv rating.csv
python3 run_model.py --Q 9.5 --Cd-rock 1.0 --d50 0.06
python3 run_model.py --Q 9 --TW 0.5   # si niveau aval connu
```

## Calage du remblai (important)

`d50` (défaut 0,05 m) et `Cd_rock` (défaut 0,85) contrôlent le débit poreux.  
Fourchette utile à explorer : `d50=0.03–0.10 m`, `Cd_rock=0.5–1.5`.

## Hydrogramme + stockage

```bash
python3 build_excel.py
```

Ouvre `Ponceau_Fosse_Modele_Hydraulique.xlsx` :
- **Hydrogramme_entree** — triangle en **formules Excel live**: changez `B5` (Q pointe, ex. 9→12), Montée, Descente, Pond A, dt
- **Routing_stockage** — `dS/dt = Q_in − Q_out(WSE)` en **formules live** (méthode Puls)

Comparer le WSE max transitoire au **Resultat_Q9** (régime permanent).
