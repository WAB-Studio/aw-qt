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


def request_gmail_connect(folder: Optional[str] = None) -> None:
    path = os.path.join(folder or dirs.get_config_dir(MODULE_NAME), GMAIL_CONNECT_REQUEST)
    with open(path, "w", encoding="utf-8"):
        pass


def request_update(folder: Optional[str] = None) -> None:
    path = os.path.join(folder or dirs.get_config_dir(MODULE_NAME), UPDATE_REQUEST)
    with open(path, "w", encoding="utf-8"):
        pass
