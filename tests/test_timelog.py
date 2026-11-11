from aw_qt import timelog
from aw_qt.config import default_config

KEY = "tl_" + "b" * 43


def test_aw_timelog_starts_with_activitywatch_by_default():
    assert '"aw-timelog"' in default_config.split("[aw-qt-testing]")[0]


def test_a_saved_key_is_read_back_and_keeps_the_other_settings(tmp_path):
    path = tmp_path / "aw-timelog.toml"
    path.write_text("[aw-timelog]\ninterval_minutes = 15\n", encoding="utf-8")
    assert timelog.save_key(f" {KEY}\n", str(path))
    assert timelog.read_key(str(path)) == KEY
    assert "interval_minutes = 15" in path.read_text(encoding="utf-8")


def test_a_key_timelog_never_minted_is_refused_and_nothing_is_written(tmp_path):
    path = tmp_path / "aw-timelog.toml"
    for wrong in ("", "tl_short", "sk_" + "b" * 43, KEY + "x"):
        assert not timelog.save_key(wrong, str(path))
    assert not path.exists()
    assert timelog.read_key(str(path)) == ""


def _tray():
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    return SimpleNamespace(_parent=None, manager=MagicMock(), showMessage=MagicMock())


def test_the_tray_saves_a_pasted_key_and_starts_the_module(tmp_path, monkeypatch):
    from aw_qt import trayicon

    path = tmp_path / "aw-timelog.toml"
    monkeypatch.setattr(timelog, "config_path", lambda: str(path))
    monkeypatch.setattr(trayicon.QInputDialog, "getText", lambda *args: (KEY, True))
    tray = _tray()
    trayicon.TrayIcon._on_timelog_key(tray)
    assert timelog.read_key(str(path)) == KEY
    tray.manager.start.assert_called_once_with("aw-timelog")


def test_the_tray_refuses_a_wrong_key_and_starts_nothing(tmp_path, monkeypatch):
    from aw_qt import trayicon

    path = tmp_path / "aw-timelog.toml"
    monkeypatch.setattr(timelog, "config_path", lambda: str(path))
    monkeypatch.setattr(trayicon.QInputDialog, "getText", lambda *args: ("sk_nope", True))
    warned = []
    monkeypatch.setattr(trayicon.QMessageBox, "warning", lambda *args: warned.append(args))
    tray = _tray()
    trayicon.TrayIcon._on_timelog_key(tray)
    assert warned and not path.exists()
    tray.manager.start.assert_not_called()


def test_aw_timelog_is_found_inside_the_bundled_aw_client_folder(tmp_path):
    from aw_qt import manager

    folder = tmp_path / "aw-client"
    folder.mkdir()
    for name in ("aw-timelog", "aw-client"):
        (folder / name).write_text("")
        (folder / name).chmod(0o755)
    names = {m.name for m in manager.filter_modules(manager._discover_modules_in_directory(str(tmp_path)))}
    assert names == {"aw-timelog"}


def test_the_tray_leaves_the_request_aw_timelog_looks_for(tmp_path):
    timelog.request_update(str(tmp_path))
    assert (tmp_path / "aw-timelog-update-request").exists()
    assert timelog.UPDATE_REQUEST == "aw-timelog-update-request"


HOMEFUND_KEY = "whk_" + "c" * 32


def test_the_tray_saves_a_pasted_homefund_key_and_refuses_a_wrong_one(tmp_path, monkeypatch):
    from aw_qt import trayicon

    path = tmp_path / "aw-timelog.toml"
    monkeypatch.setattr(timelog, "config_path", lambda: str(path))
    warned = []
    monkeypatch.setattr(trayicon.QMessageBox, "warning", lambda *args: warned.append(args))
    monkeypatch.setattr(trayicon.QInputDialog, "getText", lambda *args: (KEY, True))
    tray = _tray()
    trayicon.TrayIcon._on_homefund_key(tray)
    assert warned and not path.exists()
    monkeypatch.setattr(trayicon.QInputDialog, "getText", lambda *args: (f" {HOMEFUND_KEY}\n", True))
    trayicon.TrayIcon._on_homefund_key(tray)
    assert timelog.read_homefund_key(str(path)) == HOMEFUND_KEY
    tray.manager.start.assert_called_once_with("aw-timelog")


def test_the_tray_leaves_the_gmail_request_aw_timelog_looks_for(tmp_path):
    timelog.request_gmail_connect(str(tmp_path))
    assert (tmp_path / "aw-timelog-gmail-connect-request").exists()
