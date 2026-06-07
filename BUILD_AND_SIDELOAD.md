# PhotoBridge — Compilar el .ipa e instalar con Sideloadly

Esta guía cierra la **ruta B**: compilar la app companion en la nube y meterla
en tu iPhone desde Windows, sin poseer un Mac.

---

## Resumen del flujo completo

```
[iPhone origen]  --PhotoBridge (Exportar)-->  [carpeta en PC: LivePhotos/ + Normales/]
                                                        |
                                                        v
[PC] --importer.py / house_arrest push-->  [sandbox companion en iPhone destino]
                                                        |
                                                        v
[iPhone destino] --abres la app--> "Importar al carrete" --> CARRETE (Live Photos + EXIF)
```

---

## Parte 1 — Compilar el .ipa con GitHub Actions (gratis, sin Mac)

1. El repositorio ya incluye `.github/workflows/build-ipa.yml`.
2. Cualquier push que modifique `companion_ios/**` dispara el workflow
   automáticamente. También puedes lanzarlo a mano:
   - GitHub → pestaña **Actions** → **"Build unsigned IPA"** → **Run workflow**.
3. Cuando termine (✓ verde, ~3-5 min), entra al run → sección **Artifacts** →
   descarga **`PhotoBridgeCompanion-ipa`**. Dentro está `PhotoBridgeCompanion.ipa`.

> El .ipa sale **sin firma**. Es correcto: Sideloadly lo firma con tu Apple ID.

### ¿Qué hace el workflow?
- Levanta un runner **macOS** gratuito (repo público).
- Instala **XcodeGen** y genera el `.xcodeproj` desde `companion_ios/project.yml`.
- Compila con `xcodebuild` sin firma (`CODE_SIGNING_ALLOWED=NO`).
- Empaqueta el `.app` en `Payload/` y lo comprime como `.ipa`.

---

## Parte 2 — Instalar con Sideloadly

### Requisitos previos
- **Sideloadly** descargado desde [sideloadly.io](https://sideloadly.io)
- iTunes (versión de Apple, no Microsoft Store) instalado
- Apple ID (una cuenta secundaria gratuita funciona)

### Pasos
1. Conecta el iPhone al PC por USB. Desbloquéalo y pulsa **"Confiar"**.
2. Abre **Sideloadly**.
3. Arrastra `PhotoBridgeCompanion.ipa` a la ventana de Sideloadly.
4. Selecciona tu iPhone en la lista de dispositivos.
5. Introduce tu **Apple ID** (Sideloadly lo usa para firmar; no guarda contraseñas).
6. Clic en **Start**. La app se instalará en segundos.
7. En el iPhone: *Ajustes › General › VPN y gestión de dispositivos* →
   confía en tu Apple ID de desarrollador.

### Actualizar la app (sin perder datos)
Repite los mismos pasos arrastrando el nuevo `.ipa` sobre Sideloadly.
**No desinstales la app** — Sideloadly hace update in-place y los archivos en
`Documents/inbox/` se conservan.

### Límites con Apple ID gratuito
- La app caduca cada **7 días**. Re-instala con Sideloadly para renovarla.
- Máximo 3 apps sideloadeadas simultáneamente.
- Para una migración puntual, 7 días sobran de margen.

---

## Parte 3 — Empujar archivos e importar al carrete

### En el PC

1. Asegúrate de tener los archivos exportados con PhotoBridge
   (carpeta `LivePhotos/` y/o `Normales/`).
2. Conecta el iPhone **destino** por USB.
3. **Abre la app PhotoBridgeCompanion en el iPhone** y mantenla en primer plano.
   > iOS bloquea el acceso al sandbox cuando la app está suspendida.
4. En la GUI de PhotoBridge (PC):
   - Clic en **"Elegir carpeta a importar..."** y selecciona tu carpeta de fotos.
   - Clic en **"Empujar al iPhone"**.
   - La barra de progreso mostrará el avance archivo por archivo.

### En el iPhone

5. Cuando el push termine, la notificación en la app del PC lo indicará.
6. En la app PhotoBridgeCompanion, pulsa **"Refrescar"** si no aparecen los archivos.
7. Clic en **"Importar al carrete"**.
8. Si es la primera vez, iOS pedirá permiso para añadir fotos → **Permitir**.
9. PhotoKit ingesta todo: Live Photos reconstruidas, fecha, GPS y EXIF intactos.

---

## Notas técnicas importantes

### Por qué la app debe estar en primer plano
`HouseArrestService` (el protocolo AFC de house_arrest) requiere que la app
objetivo esté activa en iOS. Cuando iOS suspende la app en segundo plano,
el acceso al sandbox se revoca y las operaciones devuelven
`AFC_E_PERM_DENIED` (status 10).

### Cómo funciona el push internamente
`VendDocuments` monta AFC en la **raíz del contenedor** de la app, no
directamente en `Documents/`. Por esto `importer.py` usa el prefijo
`Documents/inbox/` para todas las rutas:

```python
INBOX_DIR = "Documents/inbox"
remote = f"Documents/inbox/{filename}"
ha.set_file_contents(remote, data)
```

### Live Photos
El emparejamiento `.photo + .pairedVideo` requiere que el `.HEIC` y el `.MOV`
conserven el *content identifier* original de iOS. PhotoBridge exporta originales
sin recomprimir, preservando ese identificador. Si usaras archivos reprocesados
por otra herramienta que lo borre, el par podría no formarse correctamente.

### Lectura del inbox por la app Swift
La app usa `FileManager.contentsOfDirectory(atPath:)` (variante de String,
más básica) en lugar de la variante URL. Esto garantiza la detección de archivos
escritos vía AFC que ocasionalmente la variante URL no lista.

### Sin riesgo para el dispositivo
A diferencia de la inyección por backup/restore, aquí no hay reinicio ni
sustitución de estado del iPhone. Es la API pública de Apple.
