# Bio-rétention — pack de dimensionnement v1

Work product (Excel) to **pre-size a bioretention cell** and produce boss/client-ready numbers:

- **Vcap** — capture / water-quality volume  
- **Af** — required filter surface area  
- **t_vid** — governing drawdown time (depends on underdrain flag B21)  
- Layer storage breakdown + Rd scenarios (15 / 25 / 40 mm)  
- Method note + CSA W200-oriented checklist (reminders only)

## File

`Bioretention_Dimensionnement_v1.xlsx`

| Sheet | Role |
|-------|------|
| **Parametres** | Yellow inputs → green Af, Vcap, t_vid (B21 switches formulas) |
| **Couches** | Storage by layer for Af (gravel credited only if B21=1) |
| **Scenarios** | Same catchment, different Rd |
| **Methode** | Formulas & assumptions |
| **Checklist** | Design reminders |

Yellow = inputs · green = results. Edit yellow → Excel recalculates (no Python needed).

## Underdrain switch (B21)

| B21 | ds | t_vid | SWMM Drain coeff |
|-----|----|-------|------------------|
| **1** | dp + dm·nm + df·nf + **dr·nr** | dp / (f'/1000) | > 0 |
| **0** | dp + dm·nm + df·nf (**no gravel credit**) | (dp + df·nf) / (f'/1000) | = 0 |

Af = Vcap / ds → larger Af when B21=0 (smaller ds).

## Rebuild

```bash
cd engineering/drainage-design/bioretention
python3 build_bioretention_excel.py
```

## Formulas (v1 simplified)

```text
Vcap = η × C × (Rd/1000) × Ad
B21=1: ds = dp + dm·nm + df·nf + dr·nr
B21=0: ds = dp + dm·nm + df·nf
Af   = Vcap / ds
B21=1: t_vid = dp / (f'/1000)
B21=0: t_vid = (dp + df·nf) / (f'/1000)     # f' in mm/h
```

## Product positioning

Not a full CSA W200 design. Sell as:

> « Pack Excel bio-rétention (FR) — Af, volume de captage, vidange, checklist. Prêt à adapter à votre municipalité. »

Next: structural beam/column pack (separate).

## References to cite (do not paste normative text)

- CSA W200:18 (R2023) Design of bioretention systems  
- STEP LID wiki — Bioretention: Sizing  
- Local municipal criteria (e.g. Montréal stormwater / LID)
