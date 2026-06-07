# PhotoBridge — Diseño técnico de la importación al carrete

Documentación técnica del mecanismo para escribir fotos/videos/Live Photos
**de vuelta al carrete (Camera Roll)** de un iPhone moderno desde Windows,
usando exclusivamente código abierto y APIs públicas de Apple.

> **Estado actual: ✅ Implementado y funcionando.**
> La ruta B (app companion + PhotoKit + house_arrest) está en producción.

---

## 1. Por qué no se puede "a lo bruto" (AFC directo a /DCIM)

La app Fotos de iOS no muestra lo que haya en `/DCIM`; muestra lo que está
registrado en su base de datos interna (`Photos.sqlite`, dominio `CameraRollDomain`).
Colar archivos por AFC en `/DCIM`:

- **Sí** es técnicamente posible (AFC expone `set_file_contents`, `fwrite`,
  `makedirs`, verificado en `pymobiledevice3`).
- **No** dispara la ingestión a la biblioteca en iOS moderno. Apple cerró el
  auto-import desde `/DCIM` hace muchas versiones. Resultado: los archivos
  quedan "fantasma", invisibles en la app Fotos.

Conclusión: la ruta AFC directa queda **descartada** para iOS moderno.

---

## 2. Ruta A — Inyección por backup/restore (`mobilebackup2`)

### Idea
Generar un backup, inyectar los archivos en `CameraRollDomain`, recomponer
`Manifest.db` y hacer `restore`. iOS reconstruye la biblioteca de Fotos
incluyendo lo inyectado.

### Viabilidad
- `pymobiledevice3` expone lo necesario: `backup`, `restore`, manejo de Manifest.
- 100% en Windows, sin hardware extra.

### Contras serios
- El `restore` **reinicia el iPhone** y sustituye estado; si se interrumpe, riesgo.
- **Live Photos**: emparejar foto+video en `Photos.sqlite` a mano es extremadamente
  difícil. El esquema de la DB no está documentado y cambia entre versiones de iOS.
- Mantenimiento frágil: cada iOS mayor puede romper el formato.

### Veredicto
Plan B sin Mac para fotos/videos normales. **No recomendado para Live Photos.**

---

## 3. Ruta B — App companion + PhotoKit ✅ IMPLEMENTADA

### Idea
Una pequeña **app iOS** instalada en el iPhone, con permiso de biblioteca de fotos,
recibe los archivos desde el PC vía house_arrest y los ingesta con PhotoKit.

### Flujo de datos

```
[PC — importer.py]
  └─ HouseArrestService.send_command(bundle_id, "VendDocuments")
  └─ set_file_contents("Documents/inbox/IMG_xxxx.HEIC", data)
  └─ set_file_contents("Documents/inbox/IMG_xxxx.MOV",  data)
              │
              │  USB / house_arrest / AFC
              ▼
[iPhone — sandbox de la app companion]
  Documents/
  └── inbox/
      ├── IMG_xxxx.HEIC
      └── IMG_xxxx.MOV
              │
              │  FileManager.contentsOfDirectory(atPath:)
              ▼
[InboxScanner.swift]
  └─ Agrupa por nombre base (detecta pares Live Photo)
  └─ PendingItem { imageURL, videoURL }
              │
              │  PHAssetCreationRequest
              ▼
[PhotoKit]
  └─ req.addResource(.photo,       fileURL: imageURL)
  └─ req.addResource(.pairedVideo, fileURL: videoURL)
  └─ → Live Photo nativa en el carrete, EXIF y GPS intactos
```

### Por qué es la mejor opción
- **Estable entre versiones de iOS**: PhotoKit es API pública de Apple.
- **Live Photos perfectas**: único método que las reconstruye de forma nativa.
- **Metadatos intactos**: PhotoKit conserva el EXIF embebido del archivo.
- **Sin reinicios ni riesgo**: a diferencia del restore.

---

## 4. Hallazgos técnicos durante la implementación

### 4.1 Montaje de AFC con VendDocuments

`HouseArrestService.send_command(bundle_id, "VendDocuments")` monta AFC en la
**raíz del contenedor** de la app, NO directamente en `Documents/`.

```
AFC root = /var/mobile/Containers/Data/Application/<UUID>/
├── Documents/        ← se accede como "Documents/"
├── Library/
└── tmp/
```

**Error típico si se usa la ruta incorrecta:**

| Ruta usada   | Resultado AFC          | Causa                          |
|--------------|------------------------|--------------------------------|
| `inbox/file` | `FILE_OPEN status 8`   | OBJECT_NOT_FOUND (raíz ≠ Documents) |
| `./file`     | `FILE_OPEN status 10`  | PERM_DENIED (raíz es read-only) |
| `Documents/inbox/file` | ✅ OK           | Ruta correcta                  |

**Solución:** siempre prefijar con `Documents/`:

```python
INBOX_DIR = "Documents/inbox"
remote = f"Documents/inbox/{filename}"
ha.set_file_contents(remote, data)
```

### 4.2 La app debe estar en primer plano

iOS suspende el acceso al sandbox cuando la app está en segundo plano.
Cualquier operación AFC devuelve `AFC_E_PERM_DENIED` (status 10) si la app
está suspendida. La app debe estar visible en pantalla durante toda la transferencia.

### 4.3 Método de escritura AFC

`push(local, remote)` de pymobiledevice3 hace `GET_FILE_INFO` del destino antes
de escribir. Si el archivo no existe aún (primer push), devuelve `status 8` y aborta.

`set_file_contents(remote, data)` crea el archivo directamente, sin stat previo.
**Es el método correcto para escritura de nuevos archivos.**

### 4.4 Lectura del inbox por Swift

`FileManager.contentsOfDirectory(at: URL, ...)` (variante URL) a veces no lista
archivos escritos vía AFC en iOS. La variante `contentsOfDirectory(atPath: String)`
es más básica y fiable para este caso de uso:

```swift
let names = try fm.contentsOfDirectory(atPath: inbox.path)
```

---

## 5. Componentes del sistema

### Desktop — `photobridge/importer.py`

```python
COMPANION_BUNDLE_ID = "com.photobridge.companion.772A437WN8"
INBOX_DIR = "Documents/inbox"

async def _push_async(udid, files, bundle_id, progress):
    lockdown = await create_using_usbmux(serial=udid)
    ha = HouseArrestService(lockdown)
    await ha.send_command(bundle_id, "VendDocuments")
    await ha.makedirs(INBOX_DIR)  # crea Documents/inbox si no existe
    for local in files:
        remote = f"{INBOX_DIR}/{os.path.basename(local)}"
        data = open(local, "rb").read()
        await ha.set_file_contents(remote, data)
```

### iOS — `companion_ios/Sources/ImportService.swift`

```swift
// InboxScanner detecta archivos y agrupa pares Live Photo
static func scan() -> [PendingItem] {
    let names = try fm.contentsOfDirectory(atPath: inbox.path)
    // Agrupa por nombre base: IMG_xxxx → { imageURL, videoURL }
}

// ImportViewModel ingesta con PhotoKit
private func ingest(_ item: PendingItem) async throws {
    try await PHPhotoLibrary.shared().performChanges {
        let req = PHAssetCreationRequest.forAsset()
        if item.isLivePhoto {
            req.addResource(with: .photo,       fileURL: item.imageURL!, options: opts)
            req.addResource(with: .pairedVideo, fileURL: item.videoURL!, options: opts)
        }
    }
}
```

---

## 6. Tabla de decisión final

| Criterio                    | A) Backup/restore | B) App companion + PhotoKit |
|-----------------------------|-------------------|-----------------------------|
| Solo Windows (sin Mac)      | ✅                | ✅ (GitHub Actions + Sideloadly) |
| Live Photos correctas       | ❌ muy difícil    | ✅ nativo                   |
| Metadatos EXIF/GPS          | ⚠️ frágil         | ✅ intacto                  |
| Riesgo para el dispositivo  | ⚠️ reinicio        | ✅ ninguno                  |
| Estabilidad entre iOS       | ❌ frágil         | ✅ API pública              |
| Estado de implementación    | No implementado   | ✅ Funcionando              |

---

## 7. Referencias de API verificadas en `pymobiledevice3`

- `HouseArrestService`:
  - `send_command(bundle_id, "VendDocuments")` → monta AFC en contenedor de la app.
  - `set_file_contents(path, data)` → crea/sobreescribe archivo. ✅ **Método correcto.**
  - `makedirs(path)` → crea directorios intermedios.
  - `listdir(path)` → lista directorio.
  - `stat(path)` → info de archivo/directorio.
- `afc`: operaciones en `/DCIM` del iPhone (exportación). ✅
- `installation_proxy`: `get_apps()` → localizar bundle ID instalado. ✅
- `mobilebackup2`: `backup`, `restore` → ruta A (no implementada). ℹ️
