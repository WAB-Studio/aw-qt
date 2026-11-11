"""«TimeLog y correos»: one window with the two jobs of aw-timelog, each with its switch, its keys and its status."""

import threading
from typing import Callable, Dict, List, Optional

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import timelog

REFRESH_MS = 5000
TITLE = "TimeLog y correos"


class TimelogWindow(QWidget):
    # Quitar revokes over the network on a thread; this brings the result back to the UI thread.
    _removed = pyqtSignal()

    def __init__(
        self,
        on_timelog_key: Callable[[], None],
        on_homefund_key: Callable[[], None],
        on_connect: Callable[[], None],
        on_update: Callable[[], None],
        on_open_timelog: Callable[[], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(TITLE)
        self.setMinimumWidth(460)
        self._accounts_key: object = None
        self._removing = False

        layout = QVBoxLayout(self)

        box = QGroupBox("TimeLog")
        inner = QVBoxLayout(box)
        self.timelog_switch = QCheckBox("Subir mi tiempo")
        self.timelog_switch.toggled.connect(lambda on: timelog.save_enabled("timelog_enabled", on))
        self.key_label = QLabel()
        key_button = QPushButton("Pegar llave…")
        key_button.clicked.connect(lambda: self._then_refresh(on_timelog_key))
        key_row = QHBoxLayout()
        key_row.addWidget(self.key_label, 1)
        key_row.addWidget(key_button)
        self.upload_label = QLabel()
        self.upload_label.setWordWrap(True)
        open_button = QPushButton("Abrir TimeLog")
        open_button.clicked.connect(lambda: on_open_timelog())
        inner.addWidget(self.timelog_switch)
        inner.addLayout(key_row)
        inner.addWidget(self.upload_label)
        inner.addWidget(open_button)
        layout.addWidget(box)

        box = QGroupBox("Correos del banco → HomeFund")
        inner = QVBoxLayout(box)
        self.gmail_switch = QCheckBox("Reenviar correos del banco")
        self.gmail_switch.toggled.connect(lambda on: timelog.save_enabled("gmail_enabled", on))
        self.homefund_label = QLabel()
        homefund_button = QPushButton("Pegar llave…")
        homefund_button.clicked.connect(lambda: self._then_refresh(on_homefund_key))
        homefund_row = QHBoxLayout()
        homefund_row.addWidget(self.homefund_label, 1)
        homefund_row.addWidget(homefund_button)
        inner.addWidget(self.gmail_switch)
        inner.addLayout(homefund_row)
        inner.addWidget(QLabel("Cuentas de Gmail conectadas:"))
        self.accounts = QVBoxLayout()
        inner.addLayout(self.accounts)
        connect_button = QPushButton("Conectar otra cuenta…")
        connect_button.clicked.connect(lambda: on_connect())
        inner.addWidget(connect_button)
        layout.addWidget(box)

        footer = QHBoxLayout()
        self.version_label = QLabel(f"Versión {timelog.read_version()}")
        update_button = QPushButton("Buscar actualización")
        update_button.clicked.connect(lambda: on_update())
        footer.addWidget(self.version_label, 1)
        footer.addWidget(update_button)
        layout.addLayout(footer)

        self._removed.connect(self._after_remove)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(REFRESH_MS)
        self.refresh()

    def _then_refresh(self, action: Callable[[], None]) -> None:
        action()
        self.refresh()

    def refresh(self) -> None:
        """Reads the local files only (the loop writes them); never touches the network."""
        if self._removing:
            return
        for switch, name in ((self.timelog_switch, "timelog_enabled"), (self.gmail_switch, "gmail_enabled")):
            switch.blockSignals(True)
            switch.setChecked(timelog.read_enabled(name))
            switch.blockSignals(False)
        self.key_label.setText("Llave: puesta ✓" if timelog.read_key() else "Sin llave")
        self.homefund_label.setText("Llave de HomeFund: puesta ✓" if timelog.read_homefund_key() else "Llave de HomeFund: falta")
        self.upload_label.setText(timelog.describe_upload(timelog.read_upload_status()))
        infos = [timelog.account_status(path) for path in timelog.list_gmail_accounts()]
        # Rebuild only on a change, so a click on «Quitar» is never swallowed by a refresh.
        key = [timelog.describe_account(info) for info in infos]
        if key != self._accounts_key:
            self._accounts_key = key
            self._rebuild_accounts(infos)

    def _rebuild_accounts(self, infos: List[Dict]) -> None:
        while self.accounts.count():
            item = self.accounts.takeAt(0)
            if item is not None and item.widget() is not None:
                item.widget().deleteLater()
        if not infos:
            self.accounts.addWidget(QLabel("Todavía no hay cuentas conectadas."))
            return
        for info in infos:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            text = QLabel(timelog.describe_account(info))
            text.setWordWrap(True)
            button = QPushButton("Quitar")
            button.clicked.connect(lambda _checked=False, path=info["path"], address=info["address"]: self._remove(path, address))
            row_layout.addWidget(text, 1)
            row_layout.addWidget(button)
            self.accounts.addWidget(row)

    def _remove(self, path: str, address: str) -> None:
        answer = QMessageBox.question(
            self,
            TITLE,
            f"¿Quitar {address}? Se borra su acceso de este computador y se le pide a Google que lo cancele.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._removing = True

        def work() -> None:
            try:
                timelog.remove_gmail_account(path)
            finally:
                self._removed.emit()

        threading.Thread(target=work, daemon=True).start()

    def _after_remove(self) -> None:
        self._removing = False
        self.refresh()
