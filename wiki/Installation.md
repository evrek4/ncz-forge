# Installation

🇹🇷 *Türkçe: [[Kurulum]]*

## Windows (recommended)

NCZ Forge is **portable**: a single `.exe`, no installer.

1. Download **NCZ.Forge.exe** from the [latest release](https://github.com/evrek4/ncz-forge/releases/latest).
2. Put it in any folder (e.g. Desktop) and double-click it.

> The first start can take a few seconds while the program unpacks itself to a temporary folder.

### "Windows protected your PC" warning

The exe is not digitally signed, so Windows SmartScreen may show this warning.

1. Click **More info**.
2. Click **Run anyway**.

You are only asked once. The exe is built automatically from the source code in this repository by **GitHub Actions**; the build logs are public in the [Actions](https://github.com/evrek4/ncz-forge/actions) tab.

### Updating

When a new version is available, the program shows **"⬆ Yeni sürüm hazır"** (*new version available*) at the bottom of the left menu (v1.1.0 and later). Click it to open the download page, then replace the old exe with the new one. There is no settings file, so nothing is lost.

### Uninstalling

Delete the exe. If an error log was written, you can also delete the `%LOCALAPPDATA%\NCZ Forge` folder.

## Running from source (Windows / Linux / macOS)

Requires Python 3.10 or newer.

```bash
git clone https://github.com/evrek4/ncz-forge.git
cd ncz-forge
pip install -r requirements.txt
python nczforge.py          # desktop app
python ncz_tool.py --help   # command line
```

> Drag and drop only works on Windows; on other systems use the **Gözat** (*Browse*) buttons.

Next: [[User Guide|User-Guide]]
