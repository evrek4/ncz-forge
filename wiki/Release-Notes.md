# Release Notes

🇹🇷 *Türkçe: [[Sürüm Notları|Surum-Notlari]]*

## v1.1.1 — 24 November 2026

**Fixes**
- The program no longer closes silently when many files (6+) are dragged in. Drag and drop was rewritten and now also supports paths longer than 260 characters.
- Batch conversion no longer gets stuck at 0% on Windows.

**Improvements**
- Instead of closing silently on an error, the program shows a message and writes details to `%LOCALAPPDATA%\NCZ Forge\hata_kaydi.log`.
- If a worker process crashes during parallel conversion, the remaining files are retried one by one.

## v1.1.0 — 24 November 2026

**New**
- **Batch conversion:** convert many NCZ/DXF files or whole folders to NCZ ⮂ DXF, PDF or TIF at once, in parallel.
- **New interface:** left-hand menu, card-based layout.
- **Preview** window (zoom / pan).
- Version number and **new-version notification**.
- Confirmation before overwriting an existing file.

**Conversion quality (NCZ ➔ DXF)**
- Layer and entity **colours** are transferred; PDF/TIF output from NCZ is now in colour too.
- Arcs, symbols, blocks, triangles, map sheets and smart objects are no longer skipped.

**Other**
- Exe size reduced from 57 MB to 44 MB; the exe is now built automatically by GitHub Actions.

## v1.0 — 10 October 2026

First release: NCZ ⮂ DXF conversion, vector PDF and TIF export, desktop interface with drag and drop.
