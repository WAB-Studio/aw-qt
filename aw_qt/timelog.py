"""The tray's side of TimeLog: the key goes into `aw-timelog.toml`, which the module reads before every upload."""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from typing import Callable, Dict, List, Optional

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
# aw-timelog writes the last upload here; the window only reads it.
STATUS_FILE = "aw-timelog-status.json"
GMAIL_FOLDER = "gmail"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
VERSION_FILE = "timelog-version.txt"
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


def _read_json(path: str) -> Optional[dict]:
    try:
        with open(path, encoding="utf-8") as file:
            value = json.load(file)
        return value if isinstance(value, dict) else None
    except (OSError, ValueError):
        return None


def read_upload_status(folder: Optional[str] = None) -> Optional[dict]:
    """`{at, ok, detail}` of the last upload, or None before the first one."""
    value = _read_json(os.path.join(folder or dirs.get_config_dir(MODULE_NAME), STATUS_FILE))
    return value if value and isinstance(value.get("at"), int) else None


def list_gmail_accounts(folder: Optional[str] = None) -> List[str]:
    gmail = os.path.join(folder or dirs.get_config_dir(MODULE_NAME), GMAIL_FOLDER)
    try:
        return sorted(os.path.join(gmail, name) for name in os.listdir(gmail) if name.endswith(".json"))
    except OSError:
        return []


def _state_path(account_path: str) -> str:
    return account_path[: -len(".json")] + ".state"


def account_status(path: str, now: Optional[float] = None) -> dict:
    """Address, last check, emails sent today and in total, last error; read from the account's state file."""
    now = time.time() if now is None else now
    state = _read_json(_state_path(path)) or {}
    day = state.get("sent_day")
    today = time.strftime("%Y-%m-%d", time.localtime(now))
    return {
        "path": path,
        "address": os.path.basename(path)[: -len(".json")],
        "checked": state.get("checked"),
        "error": str(state.get("error") or ""),
        "sent_today": int(day.get("count", 0)) if isinstance(day, dict) and day.get("date") == today else 0,
        "sent_total": int(state.get("sent_total", 0)),
    }


def revoke_token(refresh_token: str) -> bool:
    """Best effort: False when Google could not be reached or refused."""
    request = urllib.request.Request(
        REVOKE_URL,
        data=urllib.parse.urlencode({"token": refresh_token}).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status == 200
    except Exception:
        return False


def remove_gmail_account(path: str, revoke: Optional[Callable[[str], bool]] = None) -> None:
    """Revokes the token, then deletes the token and state files. Blocks on the network: call it off the UI thread."""
    token = (_read_json(path) or {}).get("refresh-token")
    if token:
        (revoke or revoke_token)(str(token))
    for name in (path, _state_path(path)):
        try:
            os.remove(name)
        except OSError:
            pass


def read_version(root: Optional[str] = None) -> str:
    """The installer's version, or «dev» outside an installed bundle."""
    if root is None:
        if not getattr(sys, "frozen", False):
            return "dev"
        root = os.path.dirname(os.path.dirname(os.path.abspath(sys.executable)))
    try:
        with open(os.path.join(root, VERSION_FILE), encoding="utf-8") as file:
            return file.read().strip() or "dev"
    except OSError:
        return "dev"


def format_moment(epoch: Optional[float]) -> str:
    """Local time, «dd/mm/aaaa HH:MM»."""
    if not epoch:
        return "todavía no"
    return time.strftime("%d/%m/%Y %H:%M", time.localtime(epoch))


def describe_upload(status: Optional[dict]) -> str:
    if not status:
        return "Última subida: todavía no"
    outcome = "bien" if status.get("ok") else f"falló ({status.get('detail', '')})"
    return f"Última subida: {format_moment(status['at'])}, {outcome}"


def describe_account(info: Dict) -> str:
    lines = [
        info["address"],
        f"Última revisión: {format_moment(info['checked'])}",
        f"Correos enviados: {info['sent_today']} hoy, {info['sent_total']} en total",
    ]
    if info["error"]:
        lines.append(f"Último error: {info['error']}")
    return "\n".join(lines)
