"""The tray's side of TimeLog: the key goes into `aw-timelog.toml`, which the module reads before every upload."""

import os
import re
from typing import Optional

import tomlkit
from aw_core import dirs

MODULE_NAME = "aw-timelog"
TIMELOG_URL = "https://timelog-delta.vercel.app"
KEY_PATTERN = re.compile(r"tl_[A-Za-z0-9_-]{43}")
# aw-timelog looks for this file every 30 seconds and checks for a new release at once.
UPDATE_REQUEST = "aw-timelog-update-request"
# aw-timelog opens Google's consent page in the browser when it finds this file.
GMAIL_CONNECT_REQUEST = "aw-timelog-gmail-connect-request"
HOMEFUND_KEY_PATTERN = re.compile(r"whk_[A-Za-z0-9_-]{16,}")
# HomeFund's Ajustes shows «<client_id> <client_secret>» on one line.
GMAIL_CLIENT_ID_SUFFIX = ".apps.googleusercontent.com"
GMAIL_CLIENT_SECRET_PREFIX = "GOCSPX-"


def config_path() -> str:
    return os.path.join(dirs.get_config_dir(MODULE_NAME), f"{MODULE_NAME}.toml")


def _read(path: str) -> tomlkit.TOMLDocument:
    try:
        with open(path, encoding="utf-8") as file:
            return tomlkit.parse(file.read())
    except (OSError, tomlkit.exceptions.TOMLKitError):
        return tomlkit.document()


def read_key(path: Optional[str] = None) -> str:
    return str(_read(path or config_path()).get(MODULE_NAME, {}).get("key", ""))


def save_key(key: str, path: Optional[str] = None) -> bool:
    """False for anything TimeLog would not have minted; the file is left as it was."""
    key = key.strip()
    if not KEY_PATTERN.fullmatch(key):
        return False
    path = path or config_path()
    document = _read(path)
    document.setdefault(MODULE_NAME, tomlkit.table())["key"] = key
    with open(path, "w", encoding="utf-8") as file:
        file.write(tomlkit.dumps(document))
    return True


def read_homefund_key(path: Optional[str] = None) -> str:
    return str(_read(path or config_path()).get(MODULE_NAME, {}).get("homefund_key", ""))


def save_homefund_key(key: str, path: Optional[str] = None) -> bool:
    """False for anything HomeFund would not have minted; the file is left as it was."""
    key = key.strip()
    if not HOMEFUND_KEY_PATTERN.fullmatch(key):
        return False
    path = path or config_path()
    document = _read(path)
    document.setdefault(MODULE_NAME, tomlkit.table())["homefund_key"] = key
    with open(path, "w", encoding="utf-8") as file:
        file.write(tomlkit.dumps(document))
    return True


def read_gmail_client_set(path: Optional[str] = None) -> bool:
    section = _read(path or config_path()).get(MODULE_NAME, {})
    return bool(section.get("gmail_client_id")) and bool(section.get("gmail_client_secret"))


def save_gmail_client(line: str, path: Optional[str] = None) -> bool:
    """False for anything but «<client_id> <client_secret>»; the file is left as it was."""
    parts = line.split()
    if len(parts) != 2 or not parts[0].endswith(GMAIL_CLIENT_ID_SUFFIX) or not parts[1].startswith(GMAIL_CLIENT_SECRET_PREFIX):
        return False
    path = path or config_path()
    document = _read(path)
    section = document.setdefault(MODULE_NAME, tomlkit.table())
    section["gmail_client_id"], section["gmail_client_secret"] = parts
    with open(path, "w", encoding="utf-8") as file:
        file.write(tomlkit.dumps(document))
    return True


def read_enabled(name: str, path: Optional[str] = None) -> bool:
    """`timelog_enabled` or `gmail_enabled`; on unless the file says false."""
    return _read(path or config_path()).get(MODULE_NAME, {}).get(name, True) is not False


def save_enabled(name: str, enabled: bool, path: Optional[str] = None) -> None:
    path = path or config_path()
    document = _read(path)
    document.setdefault(MODULE_NAME, tomlkit.table())[name] = bool(enabled)
    with open(path, "w", encoding="utf-8") as file:
        file.write(tomlkit.dumps(document))


def request_gmail_connect(folder: Optional[str] = None) -> None:
    path = os.path.join(folder or dirs.get_config_dir(MODULE_NAME), GMAIL_CONNECT_REQUEST)
    with open(path, "w", encoding="utf-8"):
        pass


def request_update(folder: Optional[str] = None) -> None:
    path = os.path.join(folder or dirs.get_config_dir(MODULE_NAME), UPDATE_REQUEST)
    with open(path, "w", encoding="utf-8"):
        pass
