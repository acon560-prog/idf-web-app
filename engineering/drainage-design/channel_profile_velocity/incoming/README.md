# Drop your profile files here

Copy into this folder (from Google Drive / Windows Explorer):

```
engineering/drainage-design/channel_profile_velocity/incoming/
```

## Expected names
- `Longitudinal*` → bed/ground profile along the channel (station vs elevation)
- `section*` → cross-sections along that profile

## Preferred formats (best → ok)
1. **CSV / TXT** export of vertices (easiest for the model)
2. **DXF** (polylines)
3. **DWG** (if you can also export DXF)
4. Screenshots alone → not enough for accurate velocity calc

## CSV templates (if you export from CAD)

**Longitudinal_*.csv**
```text
station_m,elev_m
0.0,41.40
5.0,40.10
10.0,37.00
```

**section_STA####.csv** (one file per section; include station in the name or a column)
```text
station_m,offset_m,elev_m
15.0,-4.0,39.5
15.0,-1.0,35.2
15.0,0.0,34.8
15.0,1.0,35.1
15.0,4.0,39.2
```

After files are here, tell the agent: “files are in incoming — build the velocity model.”
