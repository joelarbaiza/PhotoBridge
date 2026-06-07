<div align="center">

# 📸 PhotoBridge

**Open source tool to migrate photos and videos between iPhones from Windows,  
preserving metadata (capture date, GPS) and Live Photos — no Mac, no cloud.**

[![Latest Release](https://img.shields.io/github/v/release/joelarbaiza/PhotoBridge?style=flat-square&color=blue&label=Download%20IPA)](https://github.com/joelarbaiza/PhotoBridge/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Build IPA](https://img.shields.io/github/actions/workflow/status/joelarbaiza/PhotoBridge/build-ipa.yml?style=flat-square&label=Build%20IPA)](https://github.com/joelarbaiza/PhotoBridge/actions)

**🌐 Language / Idioma:** [🇪🇸 Español (README principal)](README.md) · 🇺🇸 English (this file)

</div>

---

## What it does

PhotoBridge is an **open source** iPhone migration tool built on [`pymobiledevice3`](https://github.com/doronz88/pymobiledevice3) — a pure-Python implementation of Apple's USB protocols — with a GUI powered by PySide6 (Qt).

### Export from source iPhone → PC
- Detects the connected iPhone over USB (name, model, iOS version).
- Scans `/DCIM` and classifies everything: **Live Photos**, **photos**, **videos**.
- Copies **original bytes** to a local folder — never converts HEIC→JPG, so EXIF/GPS metadata stays inside the file untouched.
- "Separate Live Photos" option: organizes output into `LivePhotos/` and `Normals/`.

### Import to destination iPhone ✅ **Fully working**
- Pushes files to the **companion app** sandbox via `house_arrest` (native Apple protocol, no jailbreak).
- The companion app ingests them with **PhotoKit** (`PHAssetCreationRequest`):
  - Live Photos reconstructed as **native** Live Photos (`.photo` + `.pairedVideo` pair).
  - EXIF, GPS and capture date intact.
  - Zero duplicates.

---

## 📲 Download the companion app

The companion app (`PhotoBridgeCompanion.ipa`) is pre-built in every  
**[GitHub Release](https://github.com/joelarbaiza/PhotoBridge/releases/latest)**.

> **The `.ipa` is unsigned by design.** Apple requires every sideloaded app to be signed with the *installing user's* Apple ID. [Sideloadly](https://sideloadly.io) does this automatically in seconds, for free.

**Quick steps:**
1. Download `PhotoBridgeCompanion.ipa` from the latest [Release](https://github.com/joelarbaiza/PhotoBridge/releases/latest).
2. Install it with **[Sideloadly](https://sideloadly.io)** using your Apple ID.
3. Follow the full guide in [BUILD_AND_SIDELOAD.md](BUILD_AND_SIDELOAD.md).

---

## Requirements

### PC (Windows 10/11)
- **Python 3.10+**
- **iTunes** (Apple’s version, **not** the Microsoft Store one) → [Download iTunes for Windows 64-bit](https://www.apple.com/itunes/download/win64)
- USB cable and tap **"Trust"** on the iPhone on first connection

### Destination iPhone
- **PhotoBridgeCompanion** app installed (see [BUILD_AND_SIDELOAD.md](BUILD_AND_SIDELOAD.md))

---

## Installation (PC desktop app)

```bash
git clone https://github.com/joelarbaiza/PhotoBridge.git
cd PhotoBridge
python -m venv .venv
.venv\Scripts\activate        # PowerShell
pip install -r requirements.txt
```

## Usage

```bash
python app.py
```

### Export flow (source iPhone → PC)
1. Connect the **source** iPhone via USB. Tap "Trust" if prompted.
2. Click **Detect iPhone** in the app.
3. Click **Scan library** → see the count (Live / Photos / Videos).
4. Check **Separate Live Photos** (recommended), choose a destination folder.
5. Click **Export**. You'll get `LivePhotos/` and `Normals/` on your PC.

### Import flow (PC → destination iPhone)
1. Install the companion app on the destination iPhone (see [BUILD_AND_SIDELOAD.md](BUILD_AND_SIDELOAD.md)).
2. Connect the **destination** iPhone via USB.
3. In the import tab, choose the exported folder.
4. **Open the PhotoBridge app on the iPhone** and keep it in the foreground.
5. Click **Push to iPhone** — the progress bar shows file-by-file progress.
6. When done, tap **Import to Camera Roll** in the iPhone app.
7. PhotoKit ingests everything: Live Photos, EXIF and GPS preserved.

---

## Architecture

```
PhotoBridge/
├── app.py                    # PySide6 GUI — export + import in one program
├── requirements.txt
├── photobridge/
│   ├── device.py             # iPhone connection: usbmux + lockdown + AFC
│   ├── photos.py             # /DCIM scan, classification and export
│   └── importer.py           # push to companion sandbox via house_arrest
└── companion_ios/
    ├── project.yml           # XcodeGen spec (generates .xcodeproj in CI)
    └── Sources/
        ├── ContentView.swift     # SwiftUI UI
        ├── ImportService.swift   # InboxScanner + ImportViewModel + PhotoKit
        └── PhotoBridgeApp.swift
```

### How the push works (technical detail)

`HouseArrestService.VendDocuments` mounts AFC at the **app container root**,
not directly at `Documents/`. The correct path structure is:

```
AFC root/
└── Documents/
    └── inbox/       ← importer.py writes here
```

That's why `importer.py` uses the `Documents/inbox/` prefix with `set_file_contents`
to create each file. The Swift app reads `Documents/inbox/` using
`FileManager.contentsOfDirectory(atPath:)`.

> **Key findings during development:**
> - The companion app **must be in the foreground** during transfer. iOS suspends sandbox access for background apps (`AFC_E_PERM_DENIED`, status 10).
> - `set_file_contents` is the correct write method — `push()` does a `GET_FILE_INFO` stat first and fails with status 8 on new files.
> - `contentsOfDirectory(atPath:)` (String variant) is more reliable than the URL variant for detecting files written via AFC.

---

## How to build / publish a new release

The GitHub Actions workflow builds the `.ipa` automatically:

| Trigger | Result |
|---------|--------|
| Push to `main` touching `companion_ios/` | Temporary artifact (expires in 90 days) |
| Push a `v*.*.*` tag | **Permanent GitHub Release** with `.ipa` attached ✅ |

To publish a new release:
```powershell
git tag v0.3.0
git push origin v0.3.0
```

The workflow runs on free macOS runners (public repo), installs XcodeGen,
builds with `xcodebuild` unsigned, and creates the Release automatically.

---

## Roadmap

- [ ] Date / type filters in the GUI.
- [ ] Thumbnail preview.
- [ ] Resume interrupted exports with hash verification.
- [ ] macOS/Linux support (`pymobiledevice3` is already cross-platform).

## License

MIT. Depends on [`pymobiledevice3`](https://github.com/doronz88/pymobiledevice3) (LGPL-3.0) and `PySide6` (LGPL-3.0).

## Disclaimer

Use only with devices you own. This tool does not bypass any Apple security protections
or activation; it exclusively uses public Apple APIs (AFC/house_arrest and PhotoKit).
