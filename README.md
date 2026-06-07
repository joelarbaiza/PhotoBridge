<div align="center">

# 📸 PhotoBridge

**Herramienta open source para migrar fotos y videos entre iPhones desde Windows,  
conservando metadatos (fecha, GPS) y Live Photos — sin Mac, sin nube.**

[![Última versión](https://img.shields.io/github/v/release/joelarbaiza/PhotoBridge?style=flat-square&color=blue&label=Descargar%20IPA)](https://github.com/joelarbaiza/PhotoBridge/releases/latest)
[![Licencia: MIT](https://img.shields.io/badge/Licencia-MIT-green?style=flat-square)](LICENSE)
[![Build IPA](https://img.shields.io/github/actions/workflow/status/joelarbaiza/PhotoBridge/build-ipa.yml?style=flat-square&label=Build%20IPA)](https://github.com/joelarbaiza/PhotoBridge/actions)

**🌐 Language / Idioma:** 🇪🇸 Español (este archivo) · [🇺🇸 English](README.en.md)

</div>

Construido sobre [`pymobiledevice3`](https://github.com/doronz88/pymobiledevice3)
(implementación pura en Python de los protocolos de Apple) con GUI en PySide6 (Qt).

---


## 📲 Descargar la app companion (para todos los usuarios)

La app companion (`PhotoBridgeCompanion.ipa`) viene precompilada en cada
**[GitHub Release](https://github.com/joelarbaiza/PhotoBridge/releases/latest)**.

> **El `.ipa` no tiene firma** — cada usuario lo firma con **su propio Apple ID**
> usando [Sideloadly](https://sideloadly.io) (gratis). Esto es por diseño:
> Apple no permite distribuir apps iOS fuera del App Store sin la firma del usuario.

**Pasos rápidos:**
1. Descarga `PhotoBridgeCompanion.ipa` de la última [Release](https://github.com/joelarbaiza/PhotoBridge/releases/latest).
2. Instálalo con **Sideloadly** usando tu Apple ID.
3. Sigue la guía completa en [BUILD_AND_SIDELOAD.md](BUILD_AND_SIDELOAD.md).

---

## Qué hace (v0.2 — flujo completo)

### Exportar desde el iPhone origen
- Detecta el iPhone conectado por USB y muestra nombre / modelo / versión de iOS.
- Escanea `/DCIM` y clasifica todo en **Live Photos**, **fotos** y **videos**.
- Exporta a una carpeta local **copiando los bytes originales** — nunca convierte
  HEIC→JPG, así que los metadatos EXIF/GPS viajan intactos dentro del archivo.
- Opción "Separar Live Photos": deja la salida en `LivePhotos/` y `Normales/`.

### Importar al iPhone destino ✅ **Funciona completamente**
- Empuja los archivos al sandbox de la **app companion** vía `house_arrest`
  (protocolo nativo Apple, sin jailbreak).
- La app companion los ingesta con **PhotoKit** (`PHAssetCreationRequest`):
  - Live Photos reconstruidas como Live Photos **nativas** (par `.photo` + `.pairedVideo`).
  - EXIF, GPS y fecha de captura intactos.
  - Sin duplicados.

---

## Requisitos

### PC (Windows 10/11)
- **Python 3.10+**
- **iTunes** (versión de Apple, **no** la de Microsoft Store) → [Descargar iTunes para Windows 64-bit](https://www.apple.com/la/itunes/)
- Cable USB y pulsar **"Confiar"** en el iPhone la primera vez

### iPhone destino
- App companion **PhotoBridgeCompanion** instalada (ver [BUILD_AND_SIDELOAD.md](BUILD_AND_SIDELOAD.md))

---

## Instalación

```bash
git clone https://github.com/joelarbaiza/PhotoBridge.git
cd PhotoBridge
python -m venv .venv
.venv\Scripts\activate        # PowerShell
pip install -r requirements.txt
```

## Uso

```bash
python app.py
```

### Flujo de exportación (iPhone origen → PC)
1. Conecta el iPhone **origen** por USB. Pulsa "Confiar" si lo pide.
2. Clic en **Detectar iPhone** en la app.
3. Clic en **Escanear biblioteca** → verás el conteo (Live / Fotos / Videos).
4. Marca **Separar Live Photos** (recomendado), elige carpeta destino.
5. Clic en **Exportar**. Obtendrás `LivePhotos/` y `Normales/` en tu PC.

### Flujo de importación (PC → iPhone destino)
1. Instala la app companion en el iPhone destino (ver [BUILD_AND_SIDELOAD.md](BUILD_AND_SIDELOAD.md)).
2. Conecta el iPhone **destino** por USB.
3. En la pestaña de importación, elige la carpeta exportada.
4. **Abre la app PhotoBridge en el iPhone** y mantenla en primer plano.
5. Clic en **Empujar al iPhone** — la barra de progreso mostrará el avance.
6. Cuando termine, pulsa **Importar al carrete** en la app del iPhone.
7. PhotoKit ingesta todo: Live Photos, EXIF y GPS conservados.

---

## Arquitectura

```
PhotoBridge/
├── app.py                    # GUI PySide6 — export + import en un solo programa
├── requirements.txt
├── photobridge/
│   ├── device.py             # conexión: usbmux + lockdown + AFC
│   ├── photos.py             # escaneo /DCIM, clasificación y exportación
│   └── importer.py           # push al sandbox companion vía house_arrest
└── companion_ios/
    ├── project.yml           # spec XcodeGen (genera .xcodeproj en CI)
    └── Sources/
        ├── ContentView.swift     # UI SwiftUI
        ├── ImportService.swift   # InboxScanner + ImportViewModel + PhotoKit
        └── PhotoBridgeApp.swift
```

### Cómo funciona el push (detalle técnico)

`VendDocuments` de `HouseArrestService` monta AFC en la **raíz del contenedor**
de la app (no directamente en `Documents/`). La ruta correcta es:

```
AFC root/
└── Documents/
    └── inbox/       ← aquí escribe importer.py
```

Por eso `importer.py` usa el prefijo `Documents/inbox/` y `set_file_contents`
para crear cada archivo. La app Swift lee `Documents/inbox/` con
`FileManager.contentsOfDirectory(atPath:)`.

---

## Roadmap

- [ ] Filtros por fecha / tipo en la GUI.
- [ ] Vista previa de miniaturas.
- [ ] Reanudar exportaciones y verificación por hash.
- [ ] Soporte macOS/Linux (pymobiledevice3 ya es multiplataforma).

## Licencia

MIT. Depende de `pymobiledevice3` (LGPL-3.0) y `PySide6` (LGPL-3.0).

## Aviso

Úsalo solo con dispositivos propios. No elude protecciones de Apple ni bypasea
activación; usa exclusivamente APIs públicas (AFC/house_arrest y PhotoKit).
