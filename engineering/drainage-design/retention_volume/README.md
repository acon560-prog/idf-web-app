# Volume de rétention — ponceau Ø900

Excel pour estimer le **volume de rétention** requis en amont du Ø900 qui contrôle la sortie.

## Hypothèse de capacité

- **n = 0,013**, Manning **pleine section** → **Q_plein ≈ 1,668 m³/s** (Méthode A)
- **Courbe Q = f(H)** FHWA HDS-5 inlet + outlet → feuille **Courbe_QH_900** (Méthode B)
- Entrée inconnue → hypothèse `square_edge` (conservatrice)
- Sur ce tuyau (L/D≈56), le calcul indique surtout un **contrôle outlet**

## Fichier principal

`Volume_Retention_Ponceau_900.xlsx`

| Feuille | Contenu |
|---------|---------|
| **Parametres** | Géométrie, Manning, Qout, facteur, aire |
| **Hydrogramme** | Qin(t) |
| **Calcul_A** | Routage Qout constant |
| **Courbe_QH_900** | Table + graphique Q=f(H) FHWA |
| **Calcul_B** | Routage avec Q lu sur la courbe |
| **Fichiers_lies** | Où sont les anciens Excel « HY-8 » |
| **Methode** | Rappels |

## Anciens fichiers (autres sites — pas ce Ø900)

| Fichier | Branche / rôle |
|---------|----------------|
| `engineering/drainage-design/Ponceau_Capacite_Inlet_Outlet.xlsx` | type HY-8 / HDS-5 (Ste-Thérèse) |
| `engineering/drainage-design/ponceau_fosse_model/Ponceau_Fosse_Modele_Hydraulique.xlsx` | Ø1050 + fossé (branche `cursor/ponceau-fosse-hydraulic-model-d87f`) |
| `engineering/hec-ras-data/` | DEM seulement — pas de projet HEC-RAS pour ce bassin |

## Reconstruction

```bash
python3 build_retention_excel.py
```

## Stage–storage–discharge teaching guide

`Stage_Storage_Discharge_Guide_900.xlsx` — read sheets 1→7 in order. Explains how the same WSE links survey volume V to culvert Q (boss +1.5 m above crown → 37.28 m → 2.4 m³/s).

```bash
python3 build_stage_storage_guide.py
```
