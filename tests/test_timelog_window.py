import json
import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLabel, QMessageBox, QPushButton  # noqa: E402

from aw_qt import timelog  # noqa: E402
from aw_qt.timelog_window import TimelogWindow  # noqa: E402

KEY = "tl_" + "b" * 43


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def folder(tmp_path, monkeypatch):
    config = tmp_path / "cfg"
    (config / "gmail").mkdir(parents=True)
    monkeypatch.setattr(timelog, "config_path", lambda: str(config / "aw-timelog.toml"))
    monkeypatch.setattr(timelog.dirs, "get_config_dir", lambda name=None: str(config))
    return config


def _account(folder, address="a@gmail.com", **state):
    (folder / "gmail" / f"{address}.json").write_text(json.dumps({"refresh-token": "r"}), encoding="utf-8")
    if state:
        (folder / "gmail" / f"{address}.state").write_text(json.dumps(state), encoding="utf-8")


def _window(calls=None):
    calls = calls if calls is not None else []
    return TimelogWindow(*(lambda name=name: calls.append(name) for name in ("key", "homefund", "connect", "update", "open")))


def _texts(window):
    return [label.text() for label in window.findChildren(QLabel)]


def test_status_and_counters_are_read_from_the_files(app, folder):
    today = time.strftime("%Y-%m-%d")
    _account(folder, checked=int(time.time()), error="sin red", sent_total=7, sent_day={"date": today, "count": 2})
    (folder / "aw-timelog-status.json").write_text(json.dumps({"at": int(time.time()), "ok": True, "detail": ""}), encoding="utf-8")
    timelog.save_key(KEY)
    window = _window()
    texts = "\n".join(_texts(window))
    assert window.windowTitle() == "TimeLog y correos"
    assert "Llave: puesta ✓" in texts and "Llave de HomeFund: falta" in texts
    assert "Última subida:" in texts and "bien" in texts
    assert "a@gmail.com" in texts and "2 hoy, 7 en total" in texts and "Último error: sin red" in texts


def test_with_nothing_recorded_it_says_so(app, folder):
    texts = "\n".join(_texts(_window()))
    assert "Sin llave" in texts and "Última subida: todavía no" in texts and "Todavía no hay cuentas conectadas." in texts


def test_the_switches_write_the_toml(app, folder):
    window = _window()
    window.gmail_switch.setChecked(False)
    assert not timelog.read_enabled("gmail_enabled") and timelog.read_enabled("timelog_enabled")


def test_the_buttons_call_the_tray_handlers(app, folder):
    calls = []
    window = _window(calls)
    for button in window.findChildren(QPushButton):
        if button.text() != "Quitar":
            button.click()
    assert sorted(calls) == ["connect", "homefund", "key", "open", "update"]


def _wait_removed(window):
    deadline = time.time() + 5
    while window._removing and time.time() < deadline:
        app = QApplication.instance()
        app.processEvents()
        time.sleep(0.01)
    QApplication.instance().processEvents()


def test_quitar_asks_first_then_revokes_and_deletes(app, folder, monkeypatch):
    _account(folder, checked=1)
    revoked = []
    monkeypatch.setattr(timelog, "revoke_token", lambda token: revoked.append(token) or True)
    window = _window()
    quitar = next(b for b in window.findChildren(QPushButton) if b.text() == "Quitar")
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.No)
    quitar.click()
    assert (folder / "gmail" / "a@gmail.com.json").exists()
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    quitar.click()
    _wait_removed(window)
    assert revoked == ["r"]
    assert not (folder / "gmail" / "a@gmail.com.json").exists() and not (folder / "gmail" / "a@gmail.com.state").exists()
    assert "Todavía no hay cuentas conectadas." in _texts(window)


def test_removing_still_deletes_when_google_is_unreachable(folder):
    _account(folder, checked=1)
    path = str(folder / "gmail" / "a@gmail.com.json")
    timelog.remove_gmail_account(path, lambda token: False)
    assert not os.path.exists(path)
    assert timelog.list_gmail_accounts() == []


def test_the_version_is_dev_without_a_version_file(tmp_path):
    assert timelog.read_version(str(tmp_path)) == "dev"
    (tmp_path / "timelog-version.txt").write_text("0.2.4\n")
    assert timelog.read_version(str(tmp_path)) == "0.2.4"
