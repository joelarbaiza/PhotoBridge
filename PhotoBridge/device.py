"""
device.py — Detección y conexión con dispositivos iOS vía pymobiledevice3.

pymobiledevice3 es una implementación pura en Python de los protocolos
privados de Apple (lockdown, AFC). Es lo que nos permite hablar con el
iPhone desde Windows sin depender de iTunes para el acceso a archivos
(aunque iTunes/Apple Mobile Device Support sí debe estar instalado para
los drivers USB).
"""

from dataclasses import dataclass
from typing import Optional

from pymobiledevice3.usbmux import list_devices
from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.afc import AfcService


@dataclass
class DeviceInfo:
    """Datos básicos del dispositivo conectado."""
    udid: str
    name: str
    product_type: str
    ios_version: str
    serial: str


class IDevice:
    """
    Envuelve la conexión a un iPhone: lockdown (info + autenticación)
    y AFC (acceso al sistema de archivos de medios, incluido /DCIM).
    """

    def __init__(self, udid: Optional[str] = None):
        self.udid = udid
        self.lockdown = None
        self.afc: Optional[AfcService] = None

    # ---------- Descubrimiento ----------

    @staticmethod
    def list_connected() -> list[str]:
        """Devuelve los UDID de todos los iPhone conectados por USB."""
        return [d.serial for d in list_devices()]

    # ---------- Conexión ----------

    def connect(self) -> DeviceInfo:
        """
        Abre la sesión lockdown. Si el iPhone no ha confiado en esta PC,
        pymobiledevice3 lanzará un error pidiendo 'Confiar' en el teléfono.
        """
        self.lockdown = create_using_usbmux(serial=self.udid)
        v = self.lockdown.all_values
        return DeviceInfo(
            udid=self.lockdown.udid,
            name=v.get("DeviceName", "iPhone"),
            product_type=v.get("ProductType", "?"),
            ios_version=v.get("ProductVersion", "?"),
            serial=v.get("SerialNumber", "?"),
        )

    def open_media(self) -> AfcService:
        """
        Abre el servicio AFC, que da acceso de lectura al área de medios
        del iPhone (carpeta /DCIM, donde viven fotos, videos y Live Photos).
        """
        if self.lockdown is None:
            self.connect()
        self.afc = AfcService(self.lockdown)
        return self.afc

    def close(self):
        if self.afc is not None:
            try:
                self.afc.close()
            except Exception:
                pass
        self.afc = None
        self.lockdown = None
