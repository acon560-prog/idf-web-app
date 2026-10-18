# Volume de rétention — ponceau Ø900

Deux classeurs distincts (ne pas écraser l'un par l'autre).

## 1) Fichier original (un bassin amont Ø900)

`Volume_Retention_Ponceau_900.xlsx`

- Une zone de rétention **amont du Ø900**
- Une feuille `Stage_Storage`
- Méthodes A / B / C

```bash
python3 build_retention_excel.py
```

## 2) Fichier deux zones (nouveau)

`Volume_Retention_Deux_Zones_1500_900_1200.xlsx`

| Zone | Tronçon | Levé | Routage |
|------|---------|------|---------|
| **1** | Ø1500 → Ø900 | `SS_Amont` | Calcul_A / B / C |
| **2** | Ø900 → Ø1200 | `SS_Aval` | `Calcul_Aval_A` |

WSE et Surface **jaunes (éditables)** — corriger depuis AutoCAD.

```bash
python3 build_retention_two_zone_excel.py
```

## GIS export?

Optionnel: exporter des polygones d'eau depuis AutoCAD/Civil 3D/GIS par cote.  
**Pas nécessaire** si vous tapez les aires dans les cellules jaunes.

## Guide pédagogique

`Stage_Storage_Discharge_Guide_900.xlsx` — `python3 build_stage_storage_guide.py`
