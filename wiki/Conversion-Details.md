# Conversion Details

🇹🇷 *Türkçe: [[Dönüşüm Ayrıntıları|Donusum-Ayrintilari]]*

## NCZ ➔ DXF

| NCZ entity | DXF result | Notes |
|---|---|---|
| Point | `POINT` | Elevation (Z) kept |
| Line | `LINE` | |
| Polyline / polygon | `LWPOLYLINE` | Polygons are closed |
| Box, triangle, smart object | Closed `LWPOLYLINE` | |
| Map sheet (pafta) | Closed `LWPOLYLINE` + sheet name text | |
| Text | `TEXT` | Height and rotation kept |
| Circle | `CIRCLE` | |
| Arc | `ARC` | See limitations |
| Symbol | `INSERT` of block `NCZ_SEMBOL_<code>` | See limitations |
| Block reference | `INSERT` of block `NCZ_BLOK_<name>` | See limitations |

### Colours

- Each **layer colour** is written to the DXF layer (24-bit true colour).
- Entities whose colour differs from their layer keep their own colour; the rest are left *ByLayer*.
- **Black and white** become AutoCAD colour 7, which shows black on a white background and white on a black one, so no line disappears into the background.

### Coordinates

Netcad stores Northing first and Easting second. NCZ Forge converts this automatically to the CAD convention (X = Easting, Y = Northing).

## DXF ➔ NCZ

- Layers and colour numbers are transferred.
- **Blocks (`INSERT`) and dimensions (`DIMENSION`) are exploded**: their lines, texts etc. are written at their real coordinates, inheriting layer and colour.
- Curves such as `ARC`, `ELLIPSE` and `SPLINE` are converted to polylines.
- `HATCH` boundaries, `SOLID` / `3DFACE` edges and `LEADER` lines are written as polylines.
- `MTEXT` is stripped of formatting codes and written as plain text.
- The `NCZ_SEMBOL_*` / `NCZ_BLOK_*` blocks created by NCZ Forge are not exploded; their insertion points are written back as **points**.
- If a **template NCZ** is given, projection and style information come from it.

## Known limitations

- **Symbol shapes:** Netcad's symbol library is not stored inside the NCZ file, so symbols appear in the DXF at the correct position, size and angle but drawn as a **placeholder** (a circle with a cross). Edit the `NCZ_SEMBOL_<code>` block in AutoCAD to change the shape of every symbol with that code at once.
- **Block definitions:** the contents of NCZ block references cannot be decoded, so a placeholder (an X) is drawn.
- **Arc angles:** not yet verified against a real Netcad file containing arcs. If your arcs are drawn the wrong way, please [report it](https://github.com/evrek4/ncz-forge/issues) with a sample file.
- **DWG:** not supported. Save the DWG as DXF in AutoCAD, BricsCAD, ZWCAD, QGIS or the free *ODA File Converter* first.
- **Attribute tables** are not transferred to DXF.
