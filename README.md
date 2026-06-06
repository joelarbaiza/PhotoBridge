# PhotoBridge

Herramienta **open source** para exportar fotos y videos de un iPhone a una PC con
Windows **conservando los metadatos** (fecha de captura, GPS) y **emparejando
correctamente las Live Photos** para evitar duplicados al reimportar.

Es un MVP estilo iMazing construido sobre [`pymobiledevice3`](https://github.com/doronz88/pymobiledevice3)
(implementación pura en Python de los protocolos de Apple) con GUI en PySide6 (Qt).

---

## Qué hace hoy (v0.1)

- Detecta el iPhone conectado por USB y muestra nombre / modelo / versión de iOS.
- Escanea `/DCIM` y clasifica todo en **Live Photos**, **fotos** y **videos**.
- Exporta a una carpeta local **copiando los bytes originales** — nunca convierte
  HEIC→JPG, así que los metadatos EXIF/GPS viajan intactos dentro del archivo.
- **Importar al iPhone** (sección en la GUI): empuja una carpeta de
  medios a la app companion vía house_arrest, con barra de progreso.
  La ingestión al carrete la hace la app en el teléfono (ver ruta B).
- Opción "Separar Live Photos": deja la salida en dos carpetas
  - `LivePhotos/` → pares `imagen + .mov` (para reimportar con *Import Live Photos*)
  - `Normales/`   → fotos sueltas, capturas y videos normales
  Esto es lo que **elimina el problema de duplicados** al volver a importar.

## Qué NO hace (y por qué, con honestidad)

- **No reimporta al carrete del iPhone nuevo.** Apple no expone un servicio
  público y estable para *escribir* en la app Fotos vía USB; ese servicio cambia
  entre versiones de iOS y es justo el "secreto" por el que iMazing/3uTools cobran
  o invierten años de mantenimiento. Por ahora, para el paso final de *importar*,
  usa **3uTools → Import Live Photos** sobre `LivePhotos/` y **Import Photos**
  sobre `Normales/`. Con las carpetas ya separadas, no hay duplicados posibles.

El roadmap más abajo apunta a cerrar también la importación, pero requiere I+D.

---

## Requisitos

- Windows 10/11 con **Python 3.10+**.
- **iTunes** o *Apple Mobile Device Support* instalado (para los drivers USB de Apple).
- Cable USB y pulsar **"Confiar"** en el iPhone (desbloqueado) la primera vez.

## Instalación

```bash
git clone <tu-repo>/PhotoBridge.git
cd PhotoBridge
python -m venv .venv
.venv\Scripts\activate        # PowerShell / CMD en Windows
pip install -r requirements.txt
```

## Uso

```bash
python app.py
```

1. **Detectar iPhone** → confirma "Confiar" en el teléfono si lo pide.
2. **Escanear biblioteca** → verás el conteo por categoría (Live / Fotos / Videos).
3. Marca **Separar Live Photos** (recomendado), elige **carpeta destino**.
4. **Exportar**. Al terminar tendrás `LivePhotos/` y `Normales/` listas.
5. Reimporta al iPhone nuevo con 3uTools (dos pases, sin duplicados).

---

## Arquitectura

```
PhotoBridge/
├── app.py                 # GUI PySide6 (hilos QThread para no congelar la UI)
├── requirements.txt
└── photobridge/
    ├── __init__.py
    ├── device.py          # conexión: usbmux + lockdown + AFC
    └── photos.py          # escaneo /DCIM, clasificación y exportación
```

- `device.py` abre **lockdown** (info/autenticación) y **AFC** (acceso a `/DCIM`).
- `photos.py` agrupa por nombre base dentro de cada carpeta `NNNAPPLE` para
  emparejar Live Photos (`IMG_1234.HEIC` + `IMG_1234.MOV`) y exporta por bytes.

## Roadmap

- [ ] Filtros por fecha / tipo (capturas, retrato) en la GUI.
- [ ] Vista previa de miniaturas.
- [ ] Reanudar exportaciones y verificación por hash.
- [ ] **Investigación de importación** vía servicios de sincronización de fotos
      de iOS (la parte difícil). Documentar qué es viable por versión de iOS.
- [ ] Soporte macOS/Linux (pymobiledevice3 ya es multiplataforma).

## Licencia

MIT (sugerida). Depende de `pymobiledevice3` (LGPL-3.0) y `PySide6` (LGPL-3.0);
revísalas si vas a distribuir binarios.

## Aviso

Úsalo solo con dispositivos propios. No elude protecciones de Apple ni bypassea
activación; solo lee el área de medios accesible vía AFC en un dispositivo en el
que ya confiaste.
