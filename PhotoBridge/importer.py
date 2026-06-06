"""
importer.py — Ruta B (app companion + PhotoKit), lado DESKTOP.

Empuja los archivos exportados al sandbox de la app companion vía house_arrest.
La ingestión real al carrete la hace la app en el iPhone con PhotoKit
(ver companion_ios/Sources/ImportService.swift).

Detalles técnicos verificados contra pymobiledevice3 9.16:
  - El constructor de HouseArrestService NO recibe bundle_id.
  - Se selecciona la app con `send_command(bundle_id, 'VendDocuments')`, que es
    ASÍNCRONO. Tras ello, el "root" AFC pasa a ser el Documents de la app, así
    que las rutas son relativas a Documents (usamos 'inbox' -> Documents/inbox).
  - Las operaciones de archivo (push, makedirs, set_file_contents) son síncronas.
"""

import asyncio
import os
import posixpath
from typing import Callable, Optional

from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.installation_proxy import InstallationProxyService
from pymobiledevice3.services.house_arrest import HouseArrestService

# Identificador de la app companion (coincide con companion_ios/project.yml)
COMPANION_BUNDLE_ID = "com.photobridge.companion"
# Carpeta dentro de Documents/ que la app vigila para ingerir:
INBOX_DIR = "inbox"

# Extensiones de medios que tiene sentido empujar
MEDIA_EXTS = {".heic", ".heif", ".jpg", ".jpeg", ".png",
              ".mov", ".mp4", ".m4v"}


def _run(coro):
    """Ejecuta una corrutina desde código síncrono (para send_command)."""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        # Ya hay un loop corriendo: usar uno nuevo aislado.
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def companion_installed(lockdown, bundle_id: str = COMPANION_BUNDLE_ID) -> bool:
    """¿Está instalada la app companion en el iPhone?"""
    ip = InstallationProxyService(lockdown)
    apps = ip.get_apps(application_type="User", bundle_identifiers=[bundle_id])
    return bundle_id in apps


def _open_documents(lockdown, bundle_id: str = COMPANION_BUNDLE_ID) -> HouseArrestService:
    """Abre house_arrest y vende el Documents de la app companion."""
    ha = HouseArrestService(lockdown)
    _run(ha.send_command(bundle_id, "VendDocuments"))
    return ha


def gather_media(folder: str, recursive: bool = True) -> list[str]:
    """Lista rutas locales de medios en una carpeta (y subcarpetas)."""
    out: list[str] = []
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


def push_files(
    lockdown,
    files: list[str],
    bundle_id: str = COMPANION_BUNDLE_ID,
    progress: Optional[Callable[[int, int, str], None]] = None,
) -> dict:
    """
    Empuja `files` (rutas locales) al inbox de la app companion usando una
    conexión lockdown ya existente (ideal para la GUI, que ya está conectada).
    """
    if not companion_installed(lockdown, bundle_id):
        raise RuntimeError(
            f"La app companion '{bundle_id}' no está instalada en el iPhone.\n"
            "Instálala con AltStore (ver BUILD_AND_SIDELOAD.md). Sin ella, iOS "
            "no permite escribir el carrete desde la PC."
        )

    ha = _open_documents(lockdown, bundle_id)
    try:
        ha.makedirs(INBOX_DIR)
    except Exception:
        pass  # ya existe

    total = len(files)
    done = 0
    errors: list[str] = []
    for local in files:
        name = os.path.basename(local)
        remote = posixpath.join(INBOX_DIR, name)
        try:
            ha.push(local, remote)
        except Exception as ex:
            errors.append(f"{name}: {ex}")
        done += 1
        if progress:
            progress(done, total, name)

    try:
        ha.close()
    except Exception:
        pass

    return {
        "pushed": done,
        "total": total,
        "errors": errors,
        "next_step": "Abre la app PhotoBridge en el iPhone y pulsa "
                     "'Importar al carrete'.",
    }


def push_for_import(
    udid: Optional[str],
    files: list[str],
    bundle_id: str = COMPANION_BUNDLE_ID,
    progress: Optional[Callable[[int, int, str], None]] = None,
) -> dict:
    """Variante CLI: crea su propia conexión a partir del UDID."""
    lockdown = create_using_usbmux(serial=udid)
    return push_files(lockdown, files, bundle_id, progress)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python -m photobridge.importer <carpeta_con_archivos>")
        sys.exit(1)
    files = gather_media(sys.argv[1])
    print(f"{len(files)} archivos de medios encontrados.")
    res = push_for_import(None, files,
                          progress=lambda d, t, n: print(f"  {d}/{t}  {n}"))
    print(res)
