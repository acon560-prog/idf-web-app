# Volume de rétention

## FILE 1 — Composite Ø1200 + fosse trapèze

`Retention_1200_File1_Composite.xlsx` — **Idée 1** (fichier séparé).

```
Qin → bassin amont Ø1200 → Qout = Q_1200(WSE) + Q_overflow_trapèze(WSE ≥ crest)
```

Résultats: WSEmax, Vmax, Q_1200 / Q_overflow / Q_down à la pointe.

```bash
python3 build_retention_file1_composite.py
```

## FILES 2–5 — Comparaison, stress, séries, crest

Même bassin / orage / Stage_Storage. Reconstruction commune:

```bash
python3 build_retention_files_2_to_5.py
```

| Fichier | Idée | Contenu |
|---------|------|---------|
| `Retention_1200_File2_Compare.xlsx` | 2 | Pipe seul vs composite (V_hold, WSEmax, Q_down) |
| `Retention_1200_File3_Stress.xlsx` | 3 | Pipe 100% / 50% / bloqué ± overflow |
| `Retention_1200_File4_TimeSeries.xlsx` | 4 | Qin, Q_1200, Q_overflow, Q_down, WSE vs temps |
| `Retention_1200_File5_CrestSensitivity.xlsx` | 5 | Sensibilité au crest (plusieurs cotes) |

Jaune = entrées · vert = résultats. Après édition: relancer le script.

Helpers partagés: `retention_common.py` (routage level-pool + FHWA Ø1200 + overflow trapèze).

---

## Nouveau (sans Ø900) — classeur général

`Volume_Retention_Sans_900.xlsx` — le client **élimine le Ø900** pour agrandir le bassin.

```
Ø1500 (in) → bassin agrandi → Ø1200 (contrôle) [+ overflow optionnel sur crest]
```

| Feuille | Contenu |
|---------|---------|
| **Parametres** | Géométrie Ø1200, crest/fossé, résultats A/B/C (jaune = entrées) |
| **Hydrogramme** | Qin(t) live |
| **Calcul_A** | Qout = Q_plein Ø1200 constant |
| **Courbe_QH_1200** | Q=f(H) FHWA live + graphique |
| **Calcul_B** | Routage pipe Ø1200 |
| **Stage_Storage** | Surfaces levé (aires plus grandes à éditer) |
| **Compose_1200** | Q_1200 + Q_overflow; V_pond + V_ditch |
| **Calcul_C** | Routage composé |
| **Methode** | Hypothèses |

```bash
python3 build_retention_no_900_excel.py
```

---

# Ancien — ponceau Ø900 (conservé pour comparaison)

Excel pour estimer le **volume de rétention** requis en amont du Ø900 qui contrôle la sortie.

## Hypothèse de capacité

- **n = 0,013**, Manning **pleine section** → **Q_plein ≈ 1,668 m³/s** (Méthode A)
- **Courbe Q = f(H)** FHWA HDS-5 → feuille **Courbe_QH_900** en **formules live** (changer n, L, entrée, TW en jaune)
- Entrée inconnue → hypothèse `square_edge` (conservatrice)
- Sur ce tuyau (L/D≈56), le calcul indique surtout un **contrôle outlet**

## Fichier principal

`Volume_Retention_Ponceau_900.xlsx`

| Feuille | Contenu |
|---------|---------|
| **Parametres** | Géométrie, Qout, aire, fossé C + **résultats A/B/C** |
| **Hydrogramme** | Qin(t) |
| **Calcul_A** | Routage Qout constant |
| **Courbe_QH_900** | Table + graphique Q=f(H) FHWA |
| **Calcul_B** | Routage pipe seul Q=f(H) |
| **Compose_900** | Q_900 + Q_overflow; V_pond + V_ditch |
| **Calcul_C** | Routage composé (crest = crown, trapèze) |
| **Stage_Storage** | Surfaces levé → V(WSE) → lecture WSEmax A/B |
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
