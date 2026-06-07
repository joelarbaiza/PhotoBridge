"""
device.py — pymobiledevice3 9.16 en Windows: todo es async.
Los workers de la GUI llaman asyncio.run() directamente con sus propias
funciones async que incluyen lockdown + AFC + operación.
"""

import asyncio
from dataclasses import dataclass
from typing import Optional

from pymobiledevice3.usbmux import list_devices
from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.afc import AfcService


def _run(coro):
    """Ejecuta una corrutina desde código síncrono."""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


@dataclass
class DeviceInfo:
    udid: str
    name: str
    product_type: str
    ios_version: str
    serial: str


class IDevice:
    def __init__(self, udid: Optional[str] = None):
        self.udid = udid

    @staticmethod
    def list_connected() -> list:
        async def _list():
            devices = await list_devices()
            return [d.serial for d in devices]
        return _run(_list())

    def connect(self) -> DeviceInfo:
        """Conecta y obtiene info del dispositivo."""
        async def _info():
            lockdown = await create_using_usbmux(serial=self.udid)
            try:
                self.udid = lockdown.udid
                v = lockdown.all_values
                return DeviceInfo(
                    udid=lockdown.udid,
                    name=v.get("DeviceName", "iPhone"),
                    product_type=v.get("ProductType", "?"),
                    ios_version=v.get("ProductVersion", "?"),
                    serial=v.get("SerialNumber", "?"),
                )
            finally:
                try:
                    await lockdown.close()
                except Exception:
                    pass
        return _run(_info())

    def companion_installed(self, bundle_id: str) -> bool:
        """Verifica si la app companion está instalada."""
        from pymobiledevice3.services.installation_proxy import InstallationProxyService
        async def _check():
            lockdown = await create_using_usbmux(serial=self.udid)
            try:
                ip = InstallationProxyService(lockdown)
                apps = await ip.get_apps(
                    application_type="User",
                    bundle_identifiers=[bundle_id]
                )
                return bundle_id in apps
            finally:
                try:
                    await lockdown.close()
                except Exception:
                    pass
        return _run(_check())
