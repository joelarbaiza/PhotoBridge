# PhotoBridge — Arranque rápido del repositorio (Git + GitHub Actions)

Guía para subir el proyecto a GitHub y compilar el `.ipa`. Si vienes de
**Azure DevOps Pipelines**, abajo hay una tabla de equivalencias para que te
sientas en casa.

---

## 1. Inicializar el repo local

Desde la carpeta `PhotoBridge/` (PowerShell):

```powershell
cd C:\ruta\a\PhotoBridge

git init
git branch -M main

# .gitignore mínimo (evita subir basura de build)
@"
__pycache__/
*.pyc
.venv/
companion_ios/build/
companion_ios/Payload/
companion_ios/*.xcodeproj/
companion_ios/Generated/
*.ipa
"@ | Out-File -Encoding utf8 .gitignore

git add .
git commit -m "PhotoBridge: exportador + app companion + CI"
```

## 2. Crear el repo en GitHub y empujar

Opción A — con la web: crea un repo **público** en github.com (sin README),
copia su URL y:

```powershell
git remote add origin https://github.com/<tu-usuario>/PhotoBridge.git
git push -u origin main
```

Opción B — con GitHub CLI (`gh`):

```powershell
gh repo create PhotoBridge --public --source=. --remote=origin --push
```

> **¿Por qué público?** Los *runners* de macOS son **gratis** en repos públicos.
> En privados consumen minutos de pago. Si el repo debe ser privado, puedes usar
> el plan gratuito con su cuota de minutos, pero macOS cuesta 10× los minutos.

## 3. Ejecutar el workflow y descargar el .ipa

1. En GitHub → pestaña **Actions** → workflow **"Build unsigned IPA"**.
2. Pulsa **Run workflow** (botón a la derecha) → rama `main` → **Run**.
   (También corre solo al hacer push que toque `companion_ios/`.)
3. Espera a que termine (✓ verde). Entra al run → sección **Artifacts** →
   descarga **`PhotoBridgeCompanion-ipa`**.
4. Continúa con `BUILD_AND_SIDELOAD.md` (instalar con AltStore).

---

## GitHub Actions explicado desde Azure DevOps

| Azure DevOps                       | GitHub Actions                          |
|------------------------------------|-----------------------------------------|
| `azure-pipelines.yml`              | `.github/workflows/build-ipa.yml`       |
| Pipeline                           | Workflow                                 |
| Stage / Job                        | Job                                      |
| Task (`- task: ...`)               | Step (`- uses:` o `- run:`)             |
| Trigger (`trigger:`)               | `on:` (push / workflow_dispatch)        |
| Agent pool (`vmImage: macOS-...`)  | `runs-on: macos-14`                     |
| "Run pipeline" manual              | `workflow_dispatch` + botón Run workflow |
| Publish Pipeline Artifact          | `actions/upload-artifact@v4`            |
| Service connection / secret vars   | Repo *Secrets* (Settings → Secrets)     |

En la práctica el `.yml` cumple el mismo rol que tu `azure-pipelines.yml`: define
disparadores, un agente (aquí macOS), pasos (instalar XcodeGen, compilar,
empaquetar) y la publicación del artefacto. No necesitas service connection
porque **no firmamos** en CI (AltStore firma en tu PC).

> Nota: también podrías compilar esto en **Azure DevOps** con un agente
> `macOS-latest` (los hosted de Microsoft existen). Si prefieres quedarte en tu
> ecosistema, el mismo conjunto de pasos se traduce 1:1 a un `azure-pipelines.yml`.
> Avísame y te lo dejo en formato Azure Pipelines.

---

## Estructura del repositorio

```
PhotoBridge/
├── app.py                      # GUI de escritorio (export + import)
├── requirements.txt
├── README.md                   # visión general
├── IMPORT_DESIGN.md            # investigación técnica de la importación
├── BUILD_AND_SIDELOAD.md       # compilar .ipa + AltStore + uso
├── REPO_QUICKSTART.md          # (este archivo)
├── photobridge/                # lógica Python (desktop)
│   ├── device.py               #   conexión iPhone (lockdown + AFC)
│   ├── photos.py               #   escaneo/exportación con metadatos
│   └── importer.py             #   push al sandbox companion (house_arrest)
├── companion_ios/              # app iOS (ruta B)
│   ├── project.yml             #   spec XcodeGen
│   └── Sources/                #   SwiftUI + PhotoKit
└── .github/workflows/
    └── build-ipa.yml           # CI: compila el .ipa en macOS (gratis)
```

## Qué hacer público y qué no

- **Público:** todo el código (no contiene secretos). Necesario para el runner
  macOS gratis.
- **Nunca subas:** tu `.ipa` firmado, certificados, perfiles `.mobileprovision`,
  ni tu Apple ID/contraseña. El `.gitignore` ya excluye `*.ipa` y artefactos de
  build. La firma ocurre solo en tu PC con AltStore.
