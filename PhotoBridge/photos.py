"""
photos.py — Enumeración, clasificación y exportación de medios del iPhone.

Concepto clave de metadatos:
    Los datos EXIF (fecha de captura, GPS, modelo de cámara) viven DENTRO
    del archivo. Mientras copiemos los bytes originales sin recomprimir ni
    convertir, los metadatos se conservan automáticamente. Por eso esta
    herramienta NUNCA convierte HEIC->JPG: copia el archivo tal cual.

Concepto clave de Live Photos:
    Una Live Photo es UN elemento en la app Fotos, pero en disco son DOS
    archivos con el mismo nombre base:  IMG_1234.HEIC  +  IMG_1234.MOV
    Detectarlas correctamente es lo que evita los duplicados al reimportar.
"""

import os
import posixpath
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from pymobiledevice3.services.afc import AfcService

# Extensiones que pueden ser el componente "imagen" de una Live Photo
IMAGE_EXTS = {".heic", ".heif", ".jpg", ".jpeg", ".png"}
VIDEO_EXTS = {".mov", ".mp4", ".m4v"}

DCIM_ROOT = "/DCIM"


class MediaKind(Enum):
    LIVE_PHOTO = "live_photo"   # par imagen + .mov con el mismo nombre
    PHOTO = "photo"             # imagen suelta
    VIDEO = "video"             # video suelto


@dataclass
class MediaItem:
    kind: MediaKind
    base_name: str
    image_path: Optional[str] = None   # ruta en el dispositivo (AFC)
    video_path: Optional[str] = None
    size: int = 0

    def device_paths(self) -> list[str]:
        return [p for p in (self.image_path, self.video_path) if p]


@dataclass
class ScanResult:
    items: list[MediaItem] = field(default_factory=list)

    @property
    def live_photos(self):
        return [i for i in self.items if i.kind == MediaKind.LIVE_PHOTO]

    @property
    def photos(self):
        return [i for i in self.items if i.kind == MediaKind.PHOTO]

    @property
    def videos(self):
        return [i for i in self.items if i.kind == MediaKind.VIDEO]

    def summary(self) -> dict:
        return {
            "live_photos": len(self.live_photos),
            "photos": len(self.photos),
            "videos": len(self.videos),
            "total_items": len(self.items),
            "total_files": sum(len(i.device_paths()) for i in self.items),
        }


def _ext(name: str) -> str:
    return os.path.splitext(name)[1].lower()


def scan_dcim(afc: AfcService) -> ScanResult:
    """
    Recorre /DCIM en el iPhone y clasifica todo en Live Photos, fotos y
    videos. Agrupa por nombre base dentro de cada carpeta para emparejar
    correctamente las Live Photos (imagen + .mov gemelo).
    """
    result = ScanResult()

    # Carpetas tipo /DCIM/100APPLE, /DCIM/101APPLE, ...
    for entry in afc.listdir(DCIM_ROOT):
        sub = posixpath.join(DCIM_ROOT, entry)
        try:
            if not afc.isdir(sub):
                continue
        except Exception:
            continue

        # Agrupar archivos de esta carpeta por nombre base
        grupos: dict[str, dict] = {}
        for fname in afc.listdir(sub):
            fpath = posixpath.join(sub, fname)
            e = _ext(fname)
            if e not in IMAGE_EXTS and e not in VIDEO_EXTS:
                continue
            base = os.path.splitext(fname)[0]
            g = grupos.setdefault(base, {"img": None, "vid": None})
            if e in IMAGE_EXTS:
                g["img"] = fpath
            elif e in VIDEO_EXTS:
                g["vid"] = fpath

        # Clasificar cada grupo
        for base, g in grupos.items():
            img, vid = g["img"], g["vid"]
            size = 0
            for p in (img, vid):
                if p:
                    try:
                        size += int(afc.stat(p).get("st_size", 0))
                    except Exception:
                        pass

            if img and vid:
                kind = MediaKind.LIVE_PHOTO
            elif img:
                kind = MediaKind.PHOTO
            else:
                kind = MediaKind.VIDEO

            result.items.append(
                MediaItem(kind=kind, base_name=base,
                          image_path=img, video_path=vid, size=size)
            )

    return result


def export(
    afc: AfcService,
    scan: ScanResult,
    dest_root: str,
    separate_live: bool = True,
    progress: Optional[Callable[[int, int, str], None]] = None,
) -> dict:
    """
    Exporta los medios al disco local copiando los bytes originales
    (metadatos intactos).

    separate_live=True organiza la salida en dos carpetas:
        LivePhotos/  -> pares imagen+.mov (para 'Import Live Photos')
        Normales/    -> fotos sueltas, capturas y videos normales
    Esa separación es lo que evita duplicados al reimportar.
    """
    live_dir = os.path.join(dest_root, "LivePhotos")
    norm_dir = os.path.join(dest_root, "Normales")
    if separate_live:
        os.makedirs(live_dir, exist_ok=True)
        os.makedirs(norm_dir, exist_ok=True)
    else:
        os.makedirs(dest_root, exist_ok=True)

    total = sum(len(i.device_paths()) for i in scan.items)
    done = 0
    errors: list[str] = []

    for item in scan.items:
        if separate_live:
            target_dir = live_dir if item.kind == MediaKind.LIVE_PHOTO else norm_dir
        else:
            target_dir = dest_root

        for dev_path in item.device_paths():
            fname = posixpath.basename(dev_path)
            out_path = os.path.join(target_dir, fname)
            try:
                data = afc.get_file_contents(dev_path)  # bytes originales
                with open(out_path, "wb") as f:
                    f.write(data)
            except Exception as ex:
                errors.append(f"{dev_path}: {ex}")
            done += 1
            if progress:
                progress(done, total, fname)

    return {"exported": done, "total": total, "errors": errors}
