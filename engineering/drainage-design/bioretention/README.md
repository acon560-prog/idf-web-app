# Bio-rétention — pack de dimensionnement v1

Work product (Excel) to **pre-size a bioretention cell** and produce boss/client-ready numbers:

- **Vcap** — capture / water-quality volume  
- **Af** — required filter surface area  
- **tp** — surface ponding drawdown time  
- Layer storage breakdown + Rd scenarios (15 / 25 / 40 mm)  
- Method note + CSA W200-oriented checklist (reminders only)

## File

`Bioretention_Dimensionnement_v1.xlsx`

| Sheet | Role |
|-------|------|
| **Parametres** | Yellow inputs → green Af, Vcap, tp |
| **Couches** | Storage by layer for Af |
| **Scenarios** | Same catchment, different Rd |
| **Methode** | Formulas & assumptions |
| **Checklist** | Design reminders |

Yellow = inputs · green = results. Edit yellow → Excel recalculates (no Python needed).

## Rebuild

```bash
cd engineering/drainage-design/bioretention
python3 build_bioretention_excel.py
```

## Formulas (v1 simplified)

```text
Vcap = η × C × (Rd/1000) × Ad
ds   = dp + dm·nm + df·nf + dr·nr
Af   = Vcap / ds
tp   = dp / (f'/1000)     # f' in mm/h
```

## Product positioning

Not a full CSA W200 design. Sell as:

> « Pack Excel bio-rétention (FR) — Af, volume de captage, vidange, checklist. Prêt à adapter à votre municipalité. »

Next: structural beam/column pack (separate).

## References to cite (do not paste normative text)

- CSA W200:18 (R2023) Design of bioretention systems  
- STEP LID wiki — Bioretention: Sizing  
- Local municipal criteria (e.g. Montréal stormwater / LID)
