"""
app.py — GUI de PhotoBridge (estilo iMazing) con PySide6.

Flujo:
  1) Detectar / conectar iPhone
  2) Escanear /DCIM y mostrar resumen (Live Photos, fotos, videos)
  3) Elegir carpeta destino + opción de separar Live Photos
  4) Exportar con barra de progreso (bytes originales, metadatos intactos)

La exportación corre en un hilo aparte (QThread) para no congelar la UI.
"""

import sys
import asyncio
import traceback

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QCheckBox, QProgressBar,
    QFrame, QGridLayout, QMessageBox, QSizePolicy,
)

from photobridge.device import IDevice
from photobridge.photos import scan_dcim, export, ScanResult
from photobridge.importer import push_files, gather_media
from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.afc import AfcService


# ----------------------------- Hilos de trabajo -----------------------------

class ScanWorker(QThread):
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, device: IDevice):
        super().__init__()
        self.device = device

    def run(self):
        async def _do():
            lockdown = await create_using_usbmux(serial=self.device.udid)
            try:
                afc = AfcService(lockdown)
                try:
                    return await scan_dcim(afc)
                finally:
                    try: await afc.close()
                    except Exception: pass
            finally:
                try: await lockdown.close()
                except Exception: pass
        try:
            result = asyncio.run(_do())
            self.finished_ok.emit(result)
        except Exception:
            self.failed.emit(traceback.format_exc())


class ExportWorker(QThread):
    progress = Signal(int, int, str)
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, device: IDevice, scan: ScanResult,
                 dest: str, separate_live: bool):
        super().__init__()
        self.device = device
        self.scan = scan
        self.dest = dest
        self.separate_live = separate_live

    def run(self):
        async def _do():
            lockdown = await create_using_usbmux(serial=self.device.udid)
            try:
                afc = AfcService(lockdown)
                try:
                    return await export(
                        afc, self.scan, self.dest,
                        separate_live=self.separate_live,
                        progress=lambda d, t, n: self.progress.emit(d, t, n),
                    )
                finally:
                    try: await afc.close()
                    except Exception: pass
            finally:
                try: await lockdown.close()
                except Exception: pass
        try:
            res = asyncio.run(_do())
            self.finished_ok.emit(res)
        except Exception:
            self.failed.emit(traceback.format_exc())


class ImportWorker(QThread):
    progress = Signal(int, int, str)
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, device: IDevice, files: list):
        super().__init__()
        self.device = device
        self.files = files

    def run(self):
        try:
            res = push_files(
                self.device.udid, self.files,
                progress=lambda d, t, n: self.progress.emit(d, t, n),
            )
            self.finished_ok.emit(res)
        except Exception:
            self.failed.emit(traceback.format_exc())


# ----------------------------- Widgets de UI -----------------------------

class StatCard(QFrame):
    """Tarjeta con un número grande y una etiqueta (resumen por categoría)."""
    def __init__(self, label: str):
        super().__init__()
        self.setObjectName("statCard")
        self.setFrameShape(QFrame.StyledPanel)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)

        self.value = QLabel("—")
        f = QFont(); f.setPointSize(22); f.setBold(True)
        self.value.setFont(f)
        self.value.setAlignment(Qt.AlignCenter)

        self.name = QLabel(label)
        self.name.setAlignment(Qt.AlignCenter)
        self.name.setStyleSheet("color:#6b7280;")

        lay.addWidget(self.value)
        lay.addWidget(self.name)

    def set_value(self, v):
        self.value.setText(str(v))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PhotoBridge — Exportar fotos de iPhone (open source)")
        self.resize(820, 560)

        self.device: IDevice | None = None
        self.scan: ScanResult | None = None
        self.dest_dir: str | None = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # --- Encabezado / dispositivo ---
        header = QHBoxLayout()
        title = QLabel("PhotoBridge")
        tf = QFont(); tf.setPointSize(18); tf.setBold(True)
        title.setFont(tf)
        header.addWidget(title)
        header.addStretch()
        self.btn_detect = QPushButton("Detectar iPhone")
        self.btn_detect.clicked.connect(self.on_detect)
        header.addWidget(self.btn_detect)
        root.addLayout(header)

        self.lbl_device = QLabel("Ningún dispositivo conectado.")
        self.lbl_device.setStyleSheet("color:#374151;")
        root.addWidget(self.lbl_device)

        # --- Tarjetas de resumen ---
        cards = QGridLayout()
        self.card_live = StatCard("Live Photos")
        self.card_photos = StatCard("Fotos")
        self.card_videos = StatCard("Videos")
        self.card_total = StatCard("Total elementos")
        for i, c in enumerate(
            [self.card_live, self.card_photos, self.card_videos, self.card_total]
        ):
            cards.addWidget(c, 0, i)
        root.addLayout(cards)

        self.btn_scan = QPushButton("Escanear biblioteca")
        self.btn_scan.setEnabled(False)
        self.btn_scan.clicked.connect(self.on_scan)
        root.addWidget(self.btn_scan)

        # --- Opciones de exportación ---
        opts = QFrame(); opts.setObjectName("optsBox")
        ol = QVBoxLayout(opts)
        self.chk_separate = QCheckBox(
            "Separar Live Photos en carpetas (LivePhotos / Normales) — evita duplicados al reimportar"
        )
        self.chk_separate.setChecked(True)
        ol.addWidget(self.chk_separate)
        info = QLabel(
            "Los archivos se copian originales (sin convertir HEIC→JPG), "
            "por lo que fecha de captura y GPS se conservan dentro de cada archivo."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#6b7280;")
        ol.addWidget(info)
        root.addWidget(opts)

        # --- Destino + exportar ---
        destrow = QHBoxLayout()
        self.btn_dest = QPushButton("Elegir carpeta destino…")
        self.btn_dest.clicked.connect(self.on_choose_dest)
        self.lbl_dest = QLabel("(sin carpeta)")
        self.lbl_dest.setStyleSheet("color:#6b7280;")
        self.lbl_dest.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        destrow.addWidget(self.btn_dest)
        destrow.addWidget(self.lbl_dest)
        root.addLayout(destrow)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        root.addWidget(self.progress)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color:#374151;")
        root.addWidget(self.lbl_status)

        self.btn_export = QPushButton("Exportar")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.on_export)
        root.addWidget(self.btn_export)

        # ===================== IMPORTAR AL iPHONE (ruta B) =====================
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#e5e7eb;")
        root.addWidget(sep)

        imp_title = QLabel("Importar al iPhone (app companion)")
        itf = QFont(); itf.setPointSize(13); itf.setBold(True)
        imp_title.setFont(itf)
        root.addWidget(imp_title)

        imp_help = QLabel(
            "IMPORTANTE: Abre la app PhotoBridge en el iPhone y "
            "mantenla en pantalla (primer plano) DURANTE toda la transferencia. "
            "iOS bloquea el acceso al sandbox cuando la app está suspendida.\n"
            "Tras empujar, pulsa 'Importar al carrete' en la app del iPhone."
        )
        imp_help.setWordWrap(True)
        imp_help.setStyleSheet("color:#6b7280;")
        root.addWidget(imp_help)

        improw = QHBoxLayout()
        self.btn_import_src = QPushButton("Elegir carpeta a importar…")
        self.btn_import_src.clicked.connect(self.on_choose_import)
        self.lbl_import_src = QLabel("(sin carpeta)")
        self.lbl_import_src.setStyleSheet("color:#6b7280;")
        self.lbl_import_src.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        improw.addWidget(self.btn_import_src)
        improw.addWidget(self.lbl_import_src)
        root.addLayout(improw)

        self.progress_imp = QProgressBar()
        self.progress_imp.setValue(0)
        root.addWidget(self.progress_imp)

        self.lbl_import_status = QLabel("")
        self.lbl_import_status.setStyleSheet("color:#374151;")
        root.addWidget(self.lbl_import_status)

        self.btn_import = QPushButton("Empujar al iPhone")
        self.btn_import.setEnabled(False)
        self.btn_import.clicked.connect(self.on_push_import)
        root.addWidget(self.btn_import)

        self.import_files: list[str] = []

        root.addStretch()
        self._apply_style()

    # ----------------------------- Acciones -----------------------------

    def on_detect(self):
        try:
            udids = IDevice.list_connected()
            if not udids:
                self.lbl_device.setText(
                    "No se detectó ningún iPhone. Conéctalo por USB, "
                    "desbloquéalo y pulsa 'Confiar'."
                )
                return
            self.device = IDevice(udid=udids[0])
            info = self.device.connect()
            self.lbl_device.setText(
                f"Conectado: {info.name} · {info.product_type} · iOS {info.ios_version}"
            )
            self.btn_scan.setEnabled(True)
            self.btn_import.setEnabled(bool(self.import_files))
        except Exception as ex:
            QMessageBox.warning(
                self, "Conexión",
                "No se pudo conectar. Si el iPhone pide 'Confiar', acéptalo "
                f"y reintenta.\n\nDetalle:\n{ex}"
            )

    def on_scan(self):
        self.btn_scan.setEnabled(False)
        self.lbl_status.setText("Escaneando /DCIM…")
        self.worker = ScanWorker(self.device)
        self.worker.finished_ok.connect(self._scan_done)
        self.worker.failed.connect(self._worker_error)
        self.worker.start()

    def _scan_done(self, result: ScanResult):
        self.scan = result
        s = result.summary()
        self.card_live.set_value(s["live_photos"])
        self.card_photos.set_value(s["photos"])
        self.card_videos.set_value(s["videos"])
        self.card_total.set_value(s["total_items"])
        self.lbl_status.setText(
            f"{s['total_items']} elementos · {s['total_files']} archivos en disco."
        )
        self.btn_scan.setEnabled(True)
        self._maybe_enable_export()

    def on_choose_dest(self):
        d = QFileDialog.getExistingDirectory(self, "Carpeta destino")
        if d:
            self.dest_dir = d
            self.lbl_dest.setText(d)
            self._maybe_enable_export()

    def _maybe_enable_export(self):
        self.btn_export.setEnabled(bool(self.scan) and bool(self.dest_dir))

    def on_export(self):
        self.btn_export.setEnabled(False)
        self.progress.setValue(0)
        self.exw = ExportWorker(
            self.device, self.scan, self.dest_dir, self.chk_separate.isChecked()
        )
        self.exw.progress.connect(self._on_progress)
        self.exw.finished_ok.connect(self._export_done)
        self.exw.failed.connect(self._worker_error)
        self.exw.start()

    def _on_progress(self, done, total, name):
        pct = int(done * 100 / total) if total else 0
        self.progress.setValue(pct)
        self.lbl_status.setText(f"Exportando {done}/{total}: {name}")

    def _export_done(self, res: dict):
        self.progress.setValue(100)
        msg = f"Listo. {res['exported']}/{res['total']} archivos exportados."
        if res["errors"]:
            msg += f"\n{len(res['errors'])} con error (ver consola)."
            for e in res["errors"]:
                print("ERROR:", e)
        self.lbl_status.setText(msg)
        QMessageBox.information(self, "Exportación completa", msg)
        self.btn_export.setEnabled(True)

    def _worker_error(self, tb: str):
        print(tb)
        QMessageBox.critical(self, "Error", tb.splitlines()[-1])
        self.btn_scan.setEnabled(True)
        self.btn_export.setEnabled(True)
        self.btn_import.setEnabled(bool(self.import_files))

    # ----------------------------- Importación (ruta B) -----------------------------

    def on_choose_import(self):
        d = QFileDialog.getExistingDirectory(self, "Carpeta a importar al iPhone")
        if not d:
            return
        self.import_files = gather_media(d, recursive=True)
        n = len(self.import_files)
        self.lbl_import_src.setText(f"{d}  ·  {n} archivos")
        self.btn_import.setEnabled(n > 0 and self.device is not None)
        if self.device is None:
            self.lbl_import_status.setText(
                "Primero conecta el iPhone (Detectar iPhone)."
            )

    def on_push_import(self):
        if not self.import_files or self.device is None:
            return

        # Advertencia: iOS requiere que la app esté en primer plano
        reply = QMessageBox.question(
            self, "¿App abierta en el iPhone?",
            "Antes de continuar:\n\n"
            "1. Abre la app PhotoBridge en el iPhone.\n"
            "2. Déjala visible en pantalla (NO en segundo plano).\n"
            "3. Pulsa OK aquí para iniciar la transferencia.\n\n"
            "iOS bloquea el acceso al sandbox si la app no está en primer plano.",
            QMessageBox.Ok | QMessageBox.Cancel,
        )
        if reply != QMessageBox.Ok:
            return

        self.btn_import.setEnabled(False)
        self.progress_imp.setValue(0)
        self.imw = ImportWorker(self.device, self.import_files)
        self.imw.progress.connect(self._on_import_progress)
        self.imw.finished_ok.connect(self._import_done)
        self.imw.failed.connect(self._worker_error)
        self.imw.start()

    def _on_import_progress(self, done, total, name):
        pct = int(done * 100 / total) if total else 0
        self.progress_imp.setValue(pct)
        self.lbl_import_status.setText(f"Empujando {done}/{total}: {name}")

    def _import_done(self, res: dict):
        self.progress_imp.setValue(100)
        msg = (f"Empujados {res['pushed']}/{res['total']} archivos al iPhone.\n"
               f"{res.get('next_step', '')}")
        if res["errors"]:
            msg += f"\n{len(res['errors'])} con error (ver consola)."
            for e in res["errors"]:
                print("ERROR:", e)
        self.lbl_import_status.setText(msg)
        QMessageBox.information(self, "Listo para ingerir", msg)
        self.btn_import.setEnabled(True)

    # ----------------------------- Estilo -----------------------------

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background: #f8fafc; }
            QPushButton {
                background: #2563eb; color: white; border: none;
                padding: 9px 16px; border-radius: 8px; font-weight: 600;
            }
            QPushButton:hover { background: #1d4ed8; }
            QPushButton:disabled { background: #cbd5e1; color: #64748b; }
            #statCard, #optsBox {
                background: white; border: 1px solid #e5e7eb; border-radius: 12px;
            }
            QProgressBar {
                border: 1px solid #e5e7eb; border-radius: 8px; height: 18px;
                text-align: center; background: white;
            }
            QProgressBar::chunk { background: #22c55e; border-radius: 7px; }
        """)


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
