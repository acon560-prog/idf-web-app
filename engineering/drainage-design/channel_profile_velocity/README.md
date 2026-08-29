# Channel profile → velocity (demo with invented data)

Learn the method **before** AutoCAD DXF arrives.

## Idea

1. Longitudinal profile = bed elevation vs station  
2. Cross-sections = shape of the ditch at several stations  
3. You choose a flow **Q**  
4. At each section: solve Manning normal depth → **V = Q / A**

```
Q_manning = (1/n) * A * R^(2/3) * sqrt(S0)
V = Q / A
```

## Run the demo

```bat
cd /d "G:\My Drive\My website\civil-eng-website\engineering\drainage-design\channel_profile_velocity"
python profile_velocity.py
python build_excel_demo.py
start Profil_Vitesse_Demo_Invente.xlsx
```

- Change **Q** / **n** in Excel yellow cells, then re-run `python build_excel_demo.py`  
  (depth solve is iterative → Python rebuilds the result table)

## Files

| File | Role |
|------|------|
| `demo_data/Longitudinal_demo.csv` | Invented bed profile |
| `demo_data/section_STA*.csv` | Invented cross-sections |
| `profile_velocity.py` | Manning engine |
| `build_excel_demo.py` | Builds the Excel workbook |
| `incoming/` | Drop real AutoCAD exports later |

## Ste-Thérèse real survey run

```bat
cd engineering\drainage-design\channel_profile_velocity
python build_st_therese_velocity.py
start SteTherese_Fosse_Vitesse_Q736.xlsx
```

Uses uploaded longitudinal + 8 surveyed sections. Default: **Q = 7.36 m³/s**, **n = 0.035**.
Clean CSVs in `st_therese_data/`.

## When you have DXF/CSV from AutoCAD


Put CSVs in `incoming/` with columns:

- Longitudinal: `station_m,elev_m`
- Sections: `station_m,offset_m,elev_m`

Then we point the engine at those files instead of `demo_data/`.
