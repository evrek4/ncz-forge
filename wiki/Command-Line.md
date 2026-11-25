# Command Line (CLI)

🇹🇷 *Türkçe: [[Komut Satırı|Komut-Satiri]]*

Everything can also be done from a terminal with `ncz_tool.py`. To run from source, see [[Installation]]. (Program messages are in Turkish.)

```bash
python ncz_tool.py --help
python ncz_tool.py --version
```

## Commands

| Command | What it does |
|---|---|
| `info` | Shows an NCZ file's version, projection, layers, entity counts and extents |
| `ncz2dxf` | NCZ ➔ DXF |
| `dxf2ncz` | DXF ➔ NCZ |
| `ncz2pdf` / `ncz2tif` | NCZ ➔ PDF / TIF |
| `dxf2pdf` / `dxf2tif` | DXF ➔ PDF / TIF |
| `batch` | Many files or folders |
| `reencode` | Reads an NCZ and writes it again (for validation) |

### info
```bash
python ncz_tool.py info examples/103_11.NCZ
```

### ncz2dxf
```bash
python ncz_tool.py ncz2dxf input.NCZ output.dxf [--version R2010]
```

### dxf2ncz
```bash
python ncz_tool.py dxf2ncz input.dxf output.NCZ [--template template.NCZ] [--swap-xy]
```

### PDF and TIF
```bash
python ncz_tool.py ncz2pdf input.NCZ output.pdf [--bg white|black]
python ncz_tool.py ncz2tif input.NCZ output.tif [--dpi 300] [--bg white|black]
python ncz_tool.py dxf2pdf input.dxf output.pdf
python ncz_tool.py dxf2tif input.dxf output.tif --dpi 600
```

### batch
```bash
python ncz_tool.py batch INPUT [INPUT ...] [options]
```
Each `INPUT` can be a file or a folder.

| Option | Default | Description |
|---|---|---|
| `--to auto\|pdf\|tif` | `auto` | `auto`: NCZ ➔ DXF and DXF ➔ NCZ |
| `--out`, `-o` | source folder | Output folder |
| `--recursive`, `-r` | off | Include subfolders |
| `--jobs`, `-j` | `0` | Number of parallel processes (`0` = automatic, `1` = sequential) |
| `--template`, `-t` | — | Template for DXF ➔ NCZ |
| `--swap-xy` | off | Swap X/Y for DXF ➔ NCZ |
| `--version` | `R2010` | DXF version for NCZ ➔ DXF |
| `--dpi` | `300` | PDF/TIF resolution |
| `--bg` | `white` | PDF/TIF background |

Examples:
```bash
# Everything in a folder and its subfolders to PDF
python ncz_tool.py batch D:\Projects --recursive --to pdf --out D:\PDF

# Three files, one after another (no parallelism)
python ncz_tool.py batch a.NCZ b.NCZ c.dxf --jobs 1
```

**Exit code:** `0` if every file succeeded, `2` if at least one failed, `1` if no files were found. Useful for error checks in `.bat` scripts.

### reencode
```bash
python ncz_tool.py reencode input.NCZ re-encoded.NCZ
```
