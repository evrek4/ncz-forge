# NCZ File Format

🇹🇷 *Türkçe: [[NCZ Dosya Formatı|NCZ-Dosya-Formati]]*

> This page is for developers and the technically curious. NCZ is Netcad's undocumented binary format; this information was obtained by reverse engineering and may not cover every Netcad version.

## Overall structure

An NCZ file is a sequence of blocks. Each block starts with:
1. `block_type`: 1 byte (uint8)
2. `payload_length`: 4 bytes (uint32, little-endian)
3. `payload`: `payload_length` bytes

## Main block types

* **Block 1 (file header / master index):** total file size, the exact byte offsets of the other main blocks (2, 6, 8, 11, 12, 14, 13, 23), the drawing's bounding box (MinX, MinY, MaxX, MaxY) and the total geometry count.
* **Block 2 (UserInfo):** Netcad file header and user information (`\x06netcad...`).
* **Block 4 (visible extents):** default visible limits of the drawing window.
* **Block 6 (layer table):** names of all layers (Pascal strings in `windows-1254`), colour indices and status flags (29 bytes per record).
* **Block 21 (standard geometry):** all vector entities:
  * **Type 1 (Point):** coordinate, elevation, layer, colour and point name.
  * **Type 2 (Line):** start and end coordinates (X1, Y1, Z1, X2, Y2, Z2) and bounding box.
  * **Type 3 (Circle):** centre and radius.
  * **Type 5 (Text):** insertion point, text height, rotation in radians and text content (`CP1254`, Turkish characters).
  * **Type 7 (Multiline / Polyline / Polygon):** one 24-byte `(X, Y, Z)` double record per vertex, plus the polygon label.

## Coordinate convention (important)

* In international CAD/GIS formats (DXF, SHP, QGIS) the first coordinate is **X (Easting)** and the second **Y (Northing)**.
* In the Netcad binary file, `raw_x` holds **Northing** and `raw_y` holds **Easting**.
* `ncz_writer.py` and `dxf_to_ncz.py` swap them automatically and losslessly (0.00000000 m error).

## Other geometry types recognised by the parser

Besides the above, `ncz_parser.py` also reads arc, symbol, block reference, box, map sheet, triangle and smart object records. Unrecognised record types are counted in `unsupported_geometry_types`:

```python
from ncz_parser import parse_ncz
r = parse_ncz("examples/103_11.NCZ")
print(r["version_name"], r["epsg"], len(r["entities"]))
print(r["unsupported_geometry_types"])   # e.g. {14: 1}
```

Source: [`ncz_parser.py`](https://github.com/evrek4/ncz-forge/blob/main/ncz_parser.py), [`ncz_writer.py`](https://github.com/evrek4/ncz-forge/blob/main/ncz_writer.py)
