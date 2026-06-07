"""
photos.py — En pymobiledevice3 9.16 en Windows, TODOS los métodos de AfcService
son async. scan_dcim y export son async; los workers los llaman con asyncio.run().
"""

import os
import posixpath
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

IMAGE_EXTS = {".heic", ".heif", ".jpg", ".jpeg", ".png"}
VIDEO_EXTS = {".mov", ".mp4", ".m4v"}
DCIM_ROOT = "/DCIM"


class MediaKind(Enum):
    LIVE_PHOTO = "live_photo"
    PHOTO = "photo"
    VIDEO = "video"


@dataclass
class MediaItem:
    kind: MediaKind
    base_name: str
    image_path: Optional[str] = None
    video_path: Optional[str] = None
    size: int = 0

    def device_paths(self) -> list:
        return [p for p in (self.image_path, self.video_path) if p]


@dataclass
class ScanResult:
    items: list = field(default_factory=list)

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


async def scan_dcim(afc) -> ScanResult:
    """Escanea /DCIM de forma async. Todos los métodos de AFC son async en Windows."""
    result = ScanResult()

    try:
        top_entries = await afc.listdir(DCIM_ROOT)
    except Exception:
        return result

    for entry in top_entries:
        sub = posixpath.join(DCIM_ROOT, entry)
        try:
            if not await afc.isdir(sub):
                continue
        except Exception:
            continue

        try:
            sub_files = await afc.listdir(sub)
        except Exception:
            continue

        grupos: dict = {}
        for fname in sub_files:
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

        for base, g in grupos.items():
            img, vid = g["img"], g["vid"]
            size = 0
            for p in (img, vid):
                if p:
                    try:
                        st = await afc.stat(p)
                        size += int(st.get("st_size", 0))
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


async def export(afc, scan: ScanResult, dest_root: str,
                 separate_live: bool = True,
                 progress: Optional[Callable] = None) -> dict:
    """Exporta medios al disco local copiando bytes originales (async)."""
    live_dir = os.path.join(dest_root, "LivePhotos")
    norm_dir = os.path.join(dest_root, "Normales")
    if separate_live:
        os.makedirs(live_dir, exist_ok=True)
        os.makedirs(norm_dir, exist_ok=True)
    else:
        os.makedirs(dest_root, exist_ok=True)

    total = sum(len(i.device_paths()) for i in scan.items)
    done = 0
    errors = []

    for item in scan.items:
        if separate_live:
            target_dir = live_dir if item.kind == MediaKind.LIVE_PHOTO else norm_dir
        else:
            target_dir = dest_root

        for dev_path in item.device_paths():
            fname = posixpath.basename(dev_path)
            out_path = os.path.join(target_dir, fname)
            try:
                data = await afc.get_file_contents(dev_path)
                with open(out_path, "wb") as f:
                    f.write(data)
            except Exception as ex:
                errors.append(f"{dev_path}: {ex}")
            done += 1
            if progress:
                progress(done, total, fname)

    return {"exported": done, "total": total, "errors": errors}
