# Developer Guide

🇹🇷 *Türkçe: [[Geliştirici Rehberi|Gelistirici-Rehberi]]*

## Project layout

| File | Purpose |
|---|---|
| `nczforge.py` | Entry point of the exe |
| `dxftoncz_gui.py` | Desktop interface (tkinter) |
| `win_dnd.py` | Windows drag-and-drop support |
| `ncz_parser.py` | NCZ reader |
| `ncz_writer.py` | NCZ writer |
| `ncz_to_dxf.py` / `dxf_to_ncz.py` | Converters |
| `cad_export.py` | PDF / TIF / preview rendering (ezdxf + matplotlib) |
| `batch_convert.py` | Batch and parallel conversion |
| `ncz_tool.py` | Command line |
| `version.py` | Version number and update check |
| `tests/` | pytest tests |
| `wiki/` | Source of this wiki |

## Development setup

```bash
pip install -r requirements-dev.txt
python -m pytest -q tests
python nczforge.py
```

Tests run on every push in GitHub Actions on **Windows and Linux**. The Windows tests drive the interface end to end by sending a real drag-and-drop message.

## Using it as a Python library

### Reading NCZ
```python
from ncz_parser import parse_ncz

r = parse_ncz("examples/103_11.NCZ")
for e in r["entities"][:5]:
    print(e["geometry_kind"], e["layer_name"], e["coordinates"][0])
```

### Converting
```python
from ncz_to_dxf import convert_ncz_to_dxf
from dxf_to_ncz import convert_dxf_to_ncz
from batch_convert import collect_files, batch_convert

convert_ncz_to_dxf("input.NCZ", "output.dxf")
convert_dxf_to_ncz("input.dxf", "output.NCZ", template_path="examples/103_11.NCZ")

summary = batch_convert(collect_files(["project_folder"]), target="pdf", workers=4)
print(len(summary.succeeded), len(summary.failed))
```

### Creating an NCZ from scratch (`ncz_writer.py`)
```python
from ncz_writer import NCZWriter

# Start a writer, optionally from a template:
writer = NCZWriter(template_path="examples/103_11.NCZ")

# Add layers:
writer.add_layer("PARSEL", color_code=251)
writer.add_layer("BINA", color_code=4)

# Add a point (X = Easting, Y = Northing):
writer.add_point(x=472500.0, y=4108000.0, z=0.0, layer="NOKTA", name="P1")

# Add a line:
writer.add_line(x1=472500.0, y1=4108000.0, x2=472600.0, y2=4108050.0, layer="PARSEL")

# Add a polyline / polygon:
writer.add_polygon([
    (472500.0, 4108000.0, 0.0),
    (472600.0, 4108000.0, 0.0),
    (472600.0, 4108100.0, 0.0),
    (472500.0, 4108100.0, 0.0),
], layer="BINA")

# Add text:
writer.add_text(x=472550.0, y=4108050.0, text="103/11", height=2.5, rotation_deg=0.0, layer="YAZI")

# Add a circle:
writer.add_circle(cx=472550.0, cy=4108050.0, radius=5.0, layer="0")

# Build and save the NCZ file:
writer.save("new_drawing.NCZ")
```

## Publishing a new release

1. Bump `__version__` in `version.py` (e.g. `1.1.2`).
2. Add the changes to the release notes (`wiki/Surum-Notlari.md` and `wiki/Release-Notes.md`).
3. Merge into `main`.
4. On GitHub, go to **Actions → Windows Exe Derle ve Yayınla → Run workflow**.

The workflow runs the tests on Windows, builds the exe with PyInstaller, creates the `v<version>` tag and Release, and attaches **NCZ.Forge.exe**. Users then see the update notice in the program.

## Editing the wiki

Wiki pages live in the repository's `wiki/` folder. When that folder changes on `main`, the **Wiki'yi Yayınla** (*Publish wiki*) workflow copies the pages to the GitHub Wiki. Do not edit the wiki in the GitHub web interface; such edits are overwritten on the next publish. Turkish pages have Turkish file names; English pages have English file names (e.g. `User-Guide.md`), and each links to its counterpart at the top.
