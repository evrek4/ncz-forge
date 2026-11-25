# Troubleshooting and FAQ

🇹🇷 *Türkçe: [[Sorun Giderme|Sorun-Giderme]]*

## The program showed an error / behaved unexpectedly

From v1.1.1 on, every error is recorded in:

```
%LOCALAPPDATA%\NCZ Forge\hata_kaydi.log
```

Paste this path into the File Explorer address bar and press Enter. When you [open an issue](https://github.com/evrek4/ncz-forge/issues/new), attach this file and, if possible, the NCZ/DXF file that caused the problem.

## Frequently asked questions

**Windows says "Windows protected your PC".**
Normal for an unsigned exe. Click **More info → Run anyway**. See [[Installation]].

**The program closed when I dragged in many files.**
This was caused by the drag-and-drop library used up to v1.1.0 and is **fixed in v1.1.1** (tested on Windows with up to 40 files). Download the [latest version](https://github.com/evrek4/ncz-forge/releases/latest).

**Batch conversion is stuck at 0%.**
A Windows-specific problem in v1.1.0, **fixed in v1.1.1**. If it still happens, untick **Paralel işle** (*Process in parallel*), try again and send the error log.

**The drawing looks rotated / mirrored in Netcad.**
On the DXF ➔ NCZ page, tick **X ve Y koordinatlarını yer değiştir** (*Swap X and Y*) and convert again.

**Symbols show up as a circle with a cross in the DXF.**
Netcad symbol shapes are not stored in the NCZ file, so a placeholder is drawn. See [Conversion Details → Known limitations](https://github.com/evrek4/ncz-forge/wiki/Conversion-Details#known-limitations).

**My AutoCAD won't open the DXF.**
On the NCZ ➔ DXF page choose R2000 or R2004 as the **DXF sürümü** (*DXF version*).

**Some lines are missing in the PDF.**
Try the other background (**Beyaz** / **Siyah**). If it persists, report it with the file.

**Can I open DWG files?**
No; save them as DXF first. See [[Conversion Details|Conversion-Details]].

**Does it run on Mac or Linux?**
The ready-made exe is Windows-only. On other systems you can run it from source (without drag and drop). See [[Installation]].

**Does it work offline?**
Yes. The internet is only used at start-up to check for a new version; if there is no connection this is silently skipped. Your files are never sent anywhere.
