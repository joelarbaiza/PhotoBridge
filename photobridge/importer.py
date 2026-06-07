"""
importer.py — Ruta B: empuja archivos al sandbox de la app companion.
TODOS los métodos de pymobiledevice3 son async en Windows 9.x.
"""

import asyncio
import os
import posixpath
from typing import Callable, Optional

from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.house_arrest import HouseArrestService

COMPANION_BUNDLE_ID = "com.photobridge.companion.772A437WN8"
INBOX_DIR = ""   # Escribimos en la raíz de Documents (siempre existe)
MEDIA_EXTS = {".heic", ".heif", ".jpg", ".jpeg", ".png",
              ".mov", ".mp4", ".m4v"}


async def _call(method, *args):
    """Llama a un método que puede ser sync o async."""
    result = method(*args)
    if asyncio.iscoroutine(result):
        return await result
    return result


async def _push_async(udid, files, bundle_id, progress):
    lockdown = await create_using_usbmux(serial=udid)
    try:
        ha = HouseArrestService(lockdown)

        # send_command siempre es async; lanzará AppNotInstalledError
        # si el bundle ID no coincide — ese error llegará al usuario.
        await ha.send_command(bundle_id, "VendDocuments")

        # Crear carpeta inbox dentro de Documents de la app
        # (ya no necesario — escribimos en Documents root directamente)

        total = len(files)
        done = 0
        errors = []
        for local in files:
            name = os.path.basename(local)
            remote = name   # directo en Documents root, sin subdirectorio
            try:
                # Leer bytes locales y escribir directo (sin stat previo)
                with open(local, "rb") as f:
                    data = f.read()
                await _call(ha.set_file_contents, remote, data)
            except Exception as ex:
                errors.append(f"{name}: {ex}")
            done += 1
            if progress:
                progress(done, total, name)

        try:
            await _call(ha.close)
        except Exception:
            pass

        return {"pushed": done, "total": total, "errors": errors,
                "next_step": "Abre la app PhotoBridge en el iPhone y pulsa "
                             "'Importar al carrete'."}
    finally:
        try:
            result = lockdown.close()
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            pass


def push_files(udid, files, bundle_id=COMPANION_BUNDLE_ID,
               progress: Optional[Callable] = None) -> dict:
    # asyncio.run() simple: en QThread no hay loop corriendo, no necesita fallback.
    return asyncio.run(_push_async(udid, files, bundle_id, progress))


def gather_media(folder: str, recursive: bool = True) -> list:
    out = []
    if recursive:
        for root, _dirs, files in os.walk(folder):
            for f in files:
                if os.path.splitext(f)[1].lower() in MEDIA_EXTS:
                    out.append(os.path.join(root, f))
    else:
        for f in os.listdir(folder):
            p = os.path.join(folder, f)
            if os.path.isfile(p) and os.path.splitext(f)[1].lower() in MEDIA_EXTS:
                out.append(p)
    return out


def list_installed_apps(udid: Optional[str] = None) -> dict:
    """Utilidad de diagnóstico: lista las apps instaladas en el iPhone."""
    from pymobiledevice3.services.installation_proxy import InstallationProxyService
    async def _list():
        lockdown = await create_using_usbmux(serial=udid)
        try:
            ip = InstallationProxyService(lockdown)
            return await ip.get_apps(application_type="User")
        finally:
            try:
                result = lockdown.close()
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass
    return asyncio.run(_list())
