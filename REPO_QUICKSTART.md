# PhotoBridge — Arranque rápido del repositorio (Git + GitHub Actions)

Guía para subir el proyecto a GitHub y compilar el `.ipa`. Si vienes de
**Azure DevOps Pipelines**, abajo hay una tabla de equivalencias.

---

## 1. Inicializar el repo local

Desde la carpeta `PhotoBridge/` (PowerShell):

```powershell
cd C:\ruta\a\PhotoBridge

git init
git branch -M main

git add .
git commit -m "PhotoBridge: exportador + app companion + CI"
```

## 2. Crear el repo en GitHub y empujar

```powershell
git remote add origin https://github.com/<tu-usuario>/PhotoBridge.git
git push -u origin main
```

O con GitHub CLI:

```powershell
gh repo create PhotoBridge --public --source=. --remote=origin --push
```

> **¿Por qué público?** Los *runners* de macOS son **gratis** en repos públicos.
> En privados consumen minutos de pago (macOS cuesta 10× los minutos Linux).

---

## 3. Compilar el .ipa y descargar

El workflow se dispara automáticamente al hacer push que modifique
`companion_ios/**`. Para lanzarlo manualmente:

1. GitHub → pestaña **Actions** → **"Build unsigned IPA"** → **Run workflow**.
2. Espera a que termine (✓ verde, ~3-5 min).
3. Entra al run → sección **Artifacts** → descarga **`PhotoBridgeCompanion-ipa`**.
4. Extrae el zip → obtienes `PhotoBridgeCompanion.ipa`.
5. Instala con **Sideloadly** (ver [BUILD_AND_SIDELOAD.md](BUILD_AND_SIDELOAD.md)).

---

## GitHub Actions explicado desde Azure DevOps

| Azure DevOps                       | GitHub Actions                          |
|------------------------------------|-----------------------------------------|
| `azure-pipelines.yml`              | `.github/workflows/build-ipa.yml`       |
| Pipeline                           | Workflow                                |
| Stage / Job                        | Job                                     |
| Task (`- task: ...`)               | Step (`- uses:` o `- run:`)             |
| Trigger (`trigger:`)               | `on:` (push / workflow_dispatch)        |
| Agent pool (`vmImage: macOS-...`)  | `runs-on: macos-15`                     |
| "Run pipeline" manual              | `workflow_dispatch` + botón Run workflow|
| Publish Pipeline Artifact          | `actions/upload-artifact@v4`            |
| Service connection / secret vars   | Repo *Secrets* (Settings → Secrets)     |

En la práctica el `.yml` cumple el mismo rol que tu `azure-pipelines.yml`: define
disparadores, un agente (aquí macOS), pasos (instalar XcodeGen, compilar,
empaquetar) y la publicación del artefacto. No necesitas service connection
porque **no firmamos** en CI (Sideloadly firma en tu PC).

---

## Estructura del repositorio

```
PhotoBridge/
├── app.py                      # GUI de escritorio (export + import)
├── requirements.txt
├── README.md                   # visión general y uso
├── IMPORT_DESIGN.md            # diseño técnico e investigación (con hallazgos)
├── BUILD_AND_SIDELOAD.md       # compilar .ipa + Sideloadly + flujo completo
├── REPO_QUICKSTART.md          # (este archivo)
├── photobridge/                # lógica Python (desktop)
│   ├── device.py               #   conexión iPhone (lockdown + AFC)
│   ├── photos.py               #   escaneo/exportación con metadatos
│   └── importer.py             #   push al sandbox companion (house_arrest)
├── companion_ios/              # app iOS companion (ruta B)
│   ├── project.yml             #   spec XcodeGen (genera .xcodeproj en CI)
│   └── Sources/
│       ├── ContentView.swift       #   UI SwiftUI
│       ├── ImportService.swift     #   InboxScanner + ImportViewModel + PhotoKit
│       └── PhotoBridgeApp.swift    #   entry point
└── .github/workflows/
    └── build-ipa.yml           # CI: compila el .ipa en macOS gratis
```

## Qué hacer público y qué no

- **Público:** todo el código (no contiene secretos). Necesario para el runner
  macOS gratuito.
- **Nunca subas:** tu `.ipa` firmado, certificados, perfiles `.mobileprovision`,
  ni tu Apple ID/contraseña. El `.gitignore` ya excluye `*.ipa` y artefactos de
  build. La firma ocurre solo en tu PC con Sideloadly.
