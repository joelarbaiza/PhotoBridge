# PhotoBridge — Diseño técnico de la IMPORTACIÓN al carrete

Investigación a fondo de cómo escribir fotos/videos/Live Photos **de vuelta al
carrete (Camera Roll)** de un iPhone moderno desde Windows, con código abierto.

> Resumen ejecutivo: en iOS moderno **no** existe una forma directa por USB de
> "soltar archivos en el carrete". Hay exactamente dos rutas reales:
> (A) **inyección por backup/restore** (100% Windows, compleja, riesgosa) y
> (B) **app companion en el iPhone con PhotoKit** (estable, ideal para Live
> Photos, pero requiere un Mac una vez para compilar/firmar la app).
> 3uTools usa la ruta B — por eso te obliga a *abrir su app en el iPhone*.

---

## 1. Por qué no se puede "a lo bruto"

La app Fotos de iOS no muestra lo que haya en `/DCIM`; muestra lo que está
registrado en su base de datos interna (`Photos.sqlite`, dominio
`CameraRollDomain` / `PhotoData`). Colar archivos por AFC en `/DCIM`:

- **Sí** es técnicamente posible (AFC expone `set_file_contents`, `fwrite`,
  `makedirs`, verificado en `pymobiledevice3`).
- **No** dispara la ingestión a la biblioteca en iOS moderno. Apple cerró el
  auto-import desde `/DCIM` hace muchas versiones. Resultado: los archivos
  quedan "fantasma", invisibles en la app Fotos.

Conclusión: la ruta AFC directa queda **descartada** para el iPhone 17.

---

## 2. Ruta A — Inyección por backup/restore (`mobilebackup2`)

### Idea
El backup de iOS contiene el carrete dentro del `CameraRollDomain`, indexado por
`Manifest.db` (SQLite) y descrito en `Manifest.plist` / `Status.plist`. Si:

1. Generas un backup del iPhone (o uno mínimo).
2. **Inyectas** tus archivos en el `CameraRollDomain` del backup.
3. Recompones `Manifest.db` (rutas, dominios, hashes) y los plists.
4. Haces `restore` del backup modificado.

…iOS reconstruye la biblioteca de Fotos incluyendo lo inyectado.

### Viabilidad
- `pymobiledevice3` expone todo lo necesario: `backup`, `restore`, `unback`,
  `info`, manejo de Manifest (verificado).
- **100% en Windows**, sin hardware extra.

### Contras serios
- El `restore` **reinicia el iPhone** y sustituye estado; si se interrumpe, riesgo.
- En backups **cifrados** hay que respetar el cifrado (más complejidad).
- **Live Photos**: emparejar foto+video en `Photos.sqlite` a mano es lo más
  difícil de todo. El esquema de la DB cambia entre versiones de iOS y no está
  documentado. Alto riesgo de que entren como foto y video separados (justo lo
  que queremos evitar).
- Mantenimiento frágil: cada iOS mayor puede romper el formato.

### Veredicto
Útil como **plan B sin Mac**, pero **no recomendada para Live Photos**. Si se
implementa, conviene limitarla primero a fotos/videos normales y dejar las Live
Photos para la ruta B.

---

## 3. Ruta B — App companion + PhotoKit  ⭐ recomendada

### Idea (es lo que hace 3uTools)
Una pequeña **app iOS** instalada en el iPhone, con permiso de biblioteca de
fotos. El flujo:

1. **Desktop (Windows, Python):** vía `house_arrest` empuja los archivos al
   **sandbox** de la app companion (`Documents/inbox/...`).
   - Verificado: `HouseArrestService.push(local_path, remote_path)` y
     `set_file_contents(filename, data)` existen.
2. **iPhone (la app companion):** detecta los archivos en su `inbox` y los
   ingesta con **PhotoKit** (`PHPhotoLibrary` / `PHAssetCreationRequest`).
   - Para una Live Photo, añade dos *resources* al mismo asset:
     `.photo` (HEIC) + `.pairedVideo` (MOV) → iOS la recrea como Live Photo
     **nativa, con todos sus metadatos**. Cero duplicados, cero pérdida de EXIF.

### Por qué es la mejor
- **Estable entre versiones de iOS**: PhotoKit es API pública de Apple; no
  depende de formatos internos no documentados.
- **Live Photos perfectas**: es el único método que las reconstruye de forma
  nativa y correcta.
- **Metadatos intactos**: PhotoKit conserva el EXIF embebido del archivo.
- **Sin reinicios ni riesgo de brick** (a diferencia del restore).

### El costo real (honesto)
- Construir y **firmar** una app iOS necesita, una sola vez:
  - un **Mac con Xcode**, y
  - una **cuenta de Apple Developer** (gratuita sirve para 7 días de firma;
    de pago para firma de 1 año), **o**
  - sideloading vía **AltStore / SideStore** desde Windows (re-firma cada 7 días
    con cuenta gratuita).
- Es la barrera que justifica que iMazing/3uTools cobren o inviertan tanto.

### Componentes a construir
1. `companion_ios/` — app iOS mínima (SwiftUI) que vigila `inbox/` e ingesta con
   PhotoKit. (Ver `companion_ios/ImportService.swift`, código de referencia.)
2. `photobridge/importer.py` — lado desktop: localiza la app por su
   `bundle_identifier`, abre `house_arrest`, empuja los archivos, y notifica.
   (Prototipo incluido.)

---

## 4. Recomendación final

| Criterio                    | A) Backup/restore | B) App companion + PhotoKit |
|----------------------------|-------------------|-----------------------------|
| Solo Windows (sin Mac)      | ✅                | ❌ (Mac/AltStore una vez)   |
| Live Photos correctas       | ❌ muy difícil    | ✅ nativo                   |
| Metadatos EXIF/GPS          | ⚠️ frágil         | ✅ intacto                  |
| Riesgo para el dispositivo  | ⚠️ reinicio/restore| ✅ bajo                    |
| Estabilidad entre iOS       | ❌ frágil         | ✅ API pública              |
| Esfuerzo de mantenimiento   | Alto              | Medio                       |

**Plan sugerido:**
1. **Corto plazo (lo que ya tienes):** exportar + organizar con PhotoBridge, y
   reimportar el paso final con 3uTools (que internamente ya usa la ruta B).
2. **Mediano plazo:** implementar la **ruta B** como objetivo del proyecto.
   Empezar por la app companion (PhotoKit) + el `importer.py` por house_arrest.
   Es la única que cumple "igual a iMazing" para Live Photos de forma estable.
3. **Plan B sin Mac:** prototipar la inyección por backup **solo para
   fotos/videos normales**, dejando las Live Photos a la ruta B.

---

## 5. Referencias de API verificadas en `pymobiledevice3`

- `afc`: `set_file_contents`, `fwrite`, `makedirs`, `rename`, `rm` (escritura OK,
  pero sin ingestión a Fotos).
- `house_arrest`: `push(local, remote)`, `set_file_contents`, `makedirs`, `push`,
  `walk` → empujar archivos al sandbox de una app.
- `installation_proxy`: `get_apps(...)`, `install_from_local`, `lookup` →
  localizar/instalar la app companion.
- `mobilebackup2`: `backup`, `restore`, `unback`, `info` → ruta de inyección.
- `misagent`: `install`, `copy_all` → perfiles de aprovisionamiento (firma).
