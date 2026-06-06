# PhotoBridge — Compilar el .ipa (sin Mac) e instalar con AltStore

Esta guía cierra la **ruta B**: compilar la app companion en la nube y meterla
en tu iPhone desde Windows, sin poseer un Mac.

---

## Resumen del flujo completo

```
[iPhone 8]  --PhotoBridge (export)-->  [carpeta en PC: LivePhotos/ + Normales/]
                                                |
                                                v
[PC] --importer.py / house_arrest push-->  [sandbox de la app companion en iPhone 17]
                                                |
                                                v
[iPhone 17] --abres la app--> PhotoKit ingesta --> CARRETE (Live Photos + EXIF)
```

---

## Parte 1 — Compilar el .ipa con GitHub Actions (gratis)

1. Crea un repositorio en GitHub (puede ser **público** para usar minutos de
   macOS gratis) y sube TODO este proyecto, incluida la carpeta
   `.github/workflows/`.
2. En GitHub ve a la pestaña **Actions**. Verás el workflow *"Build unsigned IPA"*.
   - Se ejecuta solo al hacer push, o lánzalo a mano con **Run workflow**
     (gracias a `workflow_dispatch`).
3. Cuando termine (unos minutos), entra al run y descarga el artefacto
   **`PhotoBridgeCompanion-ipa`**. Dentro está `PhotoBridgeCompanion.ipa`.

> El .ipa sale **sin firma**. Es correcto: AltStore lo firma con tu Apple ID.

### ¿Qué hace el workflow?
- Levanta un runner **macOS** (no necesitas Mac propio).
- Instala **XcodeGen** y genera el `.xcodeproj` desde `project.yml`.
- Compila con `xcodebuild` **sin firma** (`CODE_SIGNING_ALLOWED=NO`).
- Empaqueta el `.app` en `Payload/` y lo comprime como `.ipa`.

---

## Parte 2 — Instalar AltStore en Windows y sideloadear el .ipa

1. Instala **AltServer** en tu PC: <https://altstore.io> (necesita iTunes +
   iCloud para Windows, versiones de Apple, para los drivers/cuenta).
2. Conecta el iPhone 17 por USB, abre AltServer y elige
   **Install AltStore → (tu iPhone)**. Inicia sesión con un **Apple ID**
   (una cuenta secundaria gratuita es ideal).
3. En el iPhone: *Ajustes › General › VPN y gestión de dispositivos* → **confía**
   en tu Apple ID de desarrollador.
4. Abre **AltStore** en el iPhone → pestaña **My Apps** → botón **+** →
   selecciona `PhotoBridgeCompanion.ipa`. AltStore lo firma e instala.

### Límites de un Apple ID gratuito (tenlo en cuenta)
- La app caduca cada **7 días**; AltStore la **re-firma** automáticamente si el
  PC con AltServer está en la misma red (o manualmente conectando por USB).
- Máximo **3 apps** sideloadeadas a la vez con cuenta gratuita.
- Para tu migración única, 7 días sobran de margen.

---

## Parte 3 — Empujar archivos e importar

1. En la PC, asegúrate de tener tus archivos exportados y organizados
   (`LivePhotos/` y `Normales/` que produce PhotoBridge).
2. Empuja al sandbox de la app companion:
   ```bash
   python -m photobridge.importer "C:\ruta\a\LivePhotos"
   python -m photobridge.importer "C:\ruta\a\Normales"
   ```
   (Esto usa `house_arrest` para copiar a `Documents/inbox` de la app.)
3. En el iPhone 17, **abre la app PhotoBridge** y pulsa **Importar al carrete**.
   PhotoKit ingesta todo: Live Photos reconstruidas, fecha y GPS intactos.

---

## Notas técnicas importantes

- **Live Photos**: el emparejamiento `.photo` + `.pairedVideo` requiere que el
  `.HEIC` y el `.MOV` conserven el *content identifier* original. PhotoBridge
  exporta originales sin recomprimir, así que se preserva. Si usaras archivos
  re-procesados por otra herramienta que lo borre, el par podría no formarse.
- **Permisos**: la primera vez la app pedirá permiso para *añadir* a Fotos
  (`NSPhotoLibraryAddUsageDescription`). Acéptalo.
- **File sharing**: `UIFileSharingEnabled=YES` es lo que permite que el PC
  escriba en `Documents/` de la app vía house_arrest.
- **Sin riesgo para el dispositivo**: a diferencia de la inyección por backup,
  aquí no hay restore ni reinicio; es la API pública de Apple.
