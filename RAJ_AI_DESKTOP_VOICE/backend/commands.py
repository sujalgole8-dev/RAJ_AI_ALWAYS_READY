"""Safe, explicit command routing for RAJ AI.

This module intentionally never evaluates or executes raw user input. Every
action is selected by a parser and an allow-list of known operations.
"""

from __future__ import annotations

import ctypes
import datetime as dt
import os
import platform
import re
import shutil
import subprocess
import threading
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Callable

try:
    import psutil
except ImportError:  # pragma: no cover - the launcher installs requirements.
    psutil = None

try:
    import pyautogui
except ImportError:  # pragma: no cover - the launcher installs requirements.
    pyautogui = None

try:
    from PIL import ImageGrab
except ImportError:  # pragma: no cover - the launcher installs requirements.
    ImageGrab = None


_pending_lock = threading.Lock()
_pending_confirmation: dict | None = None

YES_WORDS = {"yes", "y", "confirm", "confirmed", "do it", "proceed", "sure"}
NO_WORDS = {"no", "n", "cancel", "stop", "don't", "dont", "never mind", "nevermind"}
KEYS = {
    "enter": "enter",
    "escape": "esc",
    "esc": "esc",
    "tab": "tab",
    "space": "space",
    "backspace": "backspace",
    "copy": "hotkey:ctrl,c",
    "paste": "hotkey:ctrl,v",
    "select all": "hotkey:ctrl,a",
    "undo": "hotkey:ctrl,z",
    "save": "hotkey:ctrl,s",
    "refresh": "hotkey:ctrl,r",
}
MEDIA_KEYS = {
    "play": "playpause",
    "pause": "playpause",
    "next song": "nexttrack",
    "previous song": "prevtrack",
    "stop music": "stop",
}


def normalize_command(command: str) -> str:
    """Normalize wake words, punctuation, and common Hinglish phrasing."""
    text = str(command or "").strip().lower()
    text = text.replace("’", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"[.!?,;:]+$", "", text)
    text = re.sub(r"^(?:(?:hey|okay|ok)\s+)?raj\b[\s,:-]*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    replacements = (
        (r"^(.+?)\s+open\s+kar$", r"open \1"),
        (r"^window\s+close\s+kar$", "close window"),
        (r"^volume\s+badha$", "volume up"),
        (r"^volume\s+kam\s+kar$", "volume down"),
        (r"^screenshot\s+le$", "take a screenshot"),
        (r"^laptop\s+lock\s+kar$", "lock laptop"),
        (r"^calculator\s+open\s+kar$", "open calculator"),
    )
    for pattern, replacement in replacements:
        candidate = re.sub(pattern, replacement, text)
        if candidate != text:
            text = candidate
            break
    return text.strip()


def _is_windows() -> bool:
    return platform.system().lower() == "windows"


def _pyautogui_required() -> tuple[bool, str | None]:
    if pyautogui is None:
        return False, "PyAutoGUI is not available. Run start_raj.bat again to install requirements."
    if not _is_windows():
        return False, "This Windows action is available when RAJ runs on Windows."
    return True, None


def _press(*keys: str) -> tuple[bool, str | None]:
    ready, error = _pyautogui_required()
    if not ready:
        return False, error
    try:
        pyautogui.press(list(keys))
        return True, None
    except Exception as exc:  # PyAutoGUI can fail when Windows blocks input.
        return False, f"Keyboard action failed: {exc}"


def _hotkey(*keys: str) -> tuple[bool, str | None]:
    ready, error = _pyautogui_required()
    if not ready:
        return False, error
    try:
        pyautogui.hotkey(*keys)
        return True, None
    except Exception as exc:
        return False, f"Keyboard action failed: {exc}"


def _find_executable(names: list[str], paths: list[Path] | None = None) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    for path in paths or []:
        if path.exists():
            return str(path)
    return None


def _program_files() -> list[Path]:
    roots = [os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")]
    return [Path(root) for root in roots if root]


def _launch_app(app: str) -> tuple[bool, str]:
    if not _is_windows():
        return False, "Application controls are available when RAJ runs on Windows."
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    program_files = _program_files()
    candidates: dict[str, tuple[list[str], list[Path]]] = {
        "chrome": (["chrome.exe", "chrome"], [p / "Google/Chrome/Application/chrome.exe" for p in program_files]),
        "edge": (["msedge.exe", "msedge"], [p / "Microsoft/Edge/Application/msedge.exe" for p in program_files]),
        "firefox": (["firefox.exe", "firefox"], [p / "Mozilla Firefox/firefox.exe" for p in program_files]),
        "vs code": (["code.exe", "code"], [p / "Programs/Microsoft VS Code/Code.exe" for p in [local]] + [p / "Microsoft VS Code/Code.exe" for p in program_files]),
        "visual studio code": (["code.exe", "code"], [p / "Programs/Microsoft VS Code/Code.exe" for p in [local]]),
        "notepad": (["notepad.exe"], []),
        "calculator": (["calc.exe"], []),
        "paint": (["mspaint.exe"], []),
        "file explorer": (["explorer.exe"], []),
        "settings": (["ms-settings:"], []),
        "control panel": (["control.exe"], []),
        "task manager": (["taskmgr.exe"], []),
        "command prompt": (["cmd.exe"], []),
        "powershell": (["powershell.exe"], []),
        "word": (["winword.exe"], []),
        "excel": (["excel.exe"], []),
        "powerpoint": (["powerpnt.exe"], []),
    }
    names, paths = candidates[app]
    executable = "ms-settings:" if app == "settings" else _find_executable(names, paths)
    if not executable:
        return False, f"I couldn't find {app.title()} on this computer."
    try:
        if executable.endswith(":"):
            os.startfile(executable)
        else:
            subprocess.Popen([executable], shell=False)
        return True, f"Opening {app.title()}."
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"I couldn't open {app.title()}: {exc}"


def _open_url(url: str, message: str) -> tuple[bool, str]:
    try:
        opened = webbrowser.open(url, new=2)
        return (True, message) if opened else (False, "I couldn't open that website.")
    except Exception as exc:
        return False, f"I couldn't open that website: {exc}"


def _open_folder(name: str) -> tuple[bool, str]:
    if not _is_windows():
        return False, "Folder controls are available when RAJ runs on Windows."
    paths = {
        "downloads": Path.home() / "Downloads",
        "documents": Path.home() / "Documents",
        "desktop": Path.home() / "Desktop",
        "pictures": Path.home() / "Pictures",
        "videos": Path.home() / "Videos",
        "music": Path.home() / "Music",
    }
    folder = paths[name]
    try:
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(str(folder))
        return True, f"Opening {name.title()}."
    except OSError as exc:
        return False, f"I couldn't open {name.title()}: {exc}"


def _screenshot() -> tuple[bool, str]:
    if not _is_windows() or ImageGrab is None:
        return False, "Screenshots are available when RAJ runs on Windows with Pillow installed."
    destination = Path.home() / "Pictures" / "Screenshots"
    destination.mkdir(parents=True, exist_ok=True)
    filename = destination / f"RAJ_{dt.datetime.now():%Y%m%d_%H%M%S}.png"
    try:
        image = ImageGrab.grab()
        image.save(filename)
        return True, "Screenshot saved."
    except Exception as exc:
        return False, f"I couldn't capture the screen: {exc}"


def _system_info(kind: str) -> tuple[bool, str]:
    if psutil is None:
        return False, "System information is unavailable because psutil is not installed."
    try:
        if kind == "battery":
            battery = psutil.sensors_battery()
            if battery is None:
                return True, "A battery was not detected."
            charging = " and it is charging" if battery.power_plugged else ""
            return True, f"Battery is {round(battery.percent)} percent{charging}."
        if kind == "cpu":
            return True, f"CPU usage is {round(psutil.cpu_percent(interval=0.15))} percent."
        if kind == "ram":
            return True, f"RAM usage is {round(psutil.virtual_memory().percent)} percent."
        return True, f"CPU usage is {round(psutil.cpu_percent(interval=0.15))} percent and RAM usage is {round(psutil.virtual_memory().percent)} percent."
    except Exception as exc:
        return False, f"I couldn't read system information: {exc}"


def _lock() -> tuple[bool, str]:
    if not _is_windows():
        return False, "Locking is available when RAJ runs on Windows."
    try:
        ctypes.windll.user32.LockWorkStation()
        return True, "Locking the laptop."
    except Exception as exc:
        return False, f"I couldn't lock the laptop: {exc}"


def _power_action(action: str) -> tuple[bool, str]:
    if not _is_windows():
        return False, "Power controls are available when RAJ runs on Windows."
    commands = {
        "shutdown": ["shutdown", "/s", "/t", "0"],
        "restart": ["shutdown", "/r", "/t", "0"],
        "sign out": ["shutdown", "/l"],
    }
    try:
        subprocess.Popen(commands[action], shell=False)
        return True, f"{action.title()} initiated."
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"I couldn't {action}: {exc}"


def _sleep() -> tuple[bool, str]:
    if not _is_windows():
        return False, "Sleep is available when RAJ runs on Windows."
    try:
        ctypes.windll.powrprof.SetSuspendState(False, True, False)
        return True, "Putting the laptop to sleep."
    except Exception as exc:
        return False, f"I couldn't put the laptop to sleep: {exc}"


def _safe_path(raw: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(raw.strip().strip('"')))).resolve()


def _open_user_path(raw: str, label: str) -> tuple[bool, str]:
    if not _is_windows():
        return False, "File controls are available when RAJ runs on Windows."
    path = _safe_path(raw)
    if not path.exists():
        return False, f"I couldn't find {label}."
    try:
        os.startfile(str(path))
        return True, f"Opening {path.name}."
    except OSError as exc:
        return False, f"I couldn't open {label}: {exc}"


def _create_folder(raw: str) -> tuple[bool, str]:
    path = _safe_path(raw)
    try:
        path.mkdir(parents=True, exist_ok=False)
        return True, f"Created folder {path.name}."
    except FileExistsError:
        return False, f"That folder already exists: {path.name}."
    except OSError as exc:
        return False, f"I couldn't create that folder: {exc}"


def _delete_path(path: Path) -> tuple[bool, str]:
    if not _is_windows():
        return False, "File controls are available when RAJ runs on Windows."
    try:
        if path.is_dir():
            return False, "For safety, RAJ only deletes files, not folders."
        path.unlink()
        return True, "File deleted."
    except OSError as exc:
        return False, f"I couldn't delete that file: {exc}"


def _queue_confirmation(prompt: str, action: Callable[[], tuple[bool, str]]) -> dict:
    global _pending_confirmation
    with _pending_lock:
        _pending_confirmation = {"prompt": prompt, "action": action}
    return {"success": True, "confirmation_required": True, "message": prompt, "action": "awaiting_confirmation"}


def _resolve_confirmation(text: str) -> dict | None:
    global _pending_confirmation
    with _pending_lock:
        pending = _pending_confirmation
        if not pending:
            return None
        if text in NO_WORDS:
            _pending_confirmation = None
            return {"success": True, "message": "Cancelled.", "action": "cancelled"}
        if text not in YES_WORDS:
            return {"success": False, "confirmation_required": True, "message": "Please say yes to confirm or no to cancel.", "action": "awaiting_confirmation"}
        _pending_confirmation = None
    success, message = pending["action"]()
    return {"success": success, "message": message, "action": "confirmed_action"}


def execute_command(raw_command: str) -> dict:
    """Route one natural-language command to a safe predefined action."""
    command = normalize_command(raw_command)
    if not command:
        return {"success": False, "message": "Please tell me what you would like to do.", "action": "empty"}

    confirmation = _resolve_confirmation(command)
    if confirmation is not None:
        return confirmation

    app_aliases = {
        "open chrome": "chrome", "launch chrome": "chrome",
        "open edge": "edge", "launch edge": "edge",
        "open firefox": "firefox", "launch firefox": "firefox",
        "open vs code": "vs code", "open visual studio code": "visual studio code",
        "open notepad": "notepad", "open calculator": "calculator",
        "open paint": "paint", "open file explorer": "file explorer",
        "open settings": "settings", "open control panel": "control panel",
        "open task manager": "task manager", "open command prompt": "command prompt",
        "open powershell": "powershell", "open word": "word", "open excel": "excel",
        "open powerpoint": "powerpoint",
    }
    if command in app_aliases:
        success, message = _launch_app(app_aliases[command])
        return {"success": success, "message": message, "action": f"open_{app_aliases[command].replace(' ', '_')}"}

    sites = {
        "open google": ("https://www.google.com", "Opening Google."),
        "open youtube": ("https://www.youtube.com", "Opening YouTube."),
        "open gmail": ("https://mail.google.com", "Opening Gmail."),
        "open github": ("https://github.com", "Opening GitHub."),
        "open chatgpt": ("https://chatgpt.com", "Opening ChatGPT."),
    }
    if command in sites:
        success, message = _open_url(*sites[command])
        return {"success": success, "message": message, "action": command.replace(" ", "_")}
    search = re.match(r"search (google|youtube) for (.+)$", command)
    if search:
        site, query = search.groups()
        base = "https://www.google.com/search?q=" if site == "google" else "https://www.youtube.com/results?search_query="
        success, message = _open_url(base + urllib.parse.quote_plus(query), f"Searching {site.title()} for {query}.")
        return {"success": success, "message": message, "action": f"search_{site}"}

    folders = {"open downloads": "downloads", "open documents": "documents", "open desktop": "desktop", "open pictures": "pictures", "open videos": "videos", "open music": "music"}
    if command in folders:
        success, message = _open_folder(folders[command])
        return {"success": success, "message": message, "action": f"open_{folders[command]}"}

    window_actions = {
        "close window": ("hotkey", ("alt", "f4"), "Closing the current window.", "close_window"),
        "close this window": ("hotkey", ("alt", "f4"), "Closing the current window.", "close_window"),
        "close current window": ("hotkey", ("alt", "f4"), "Closing the current window.", "close_window"),
        "minimize window": ("hotkey", ("win", "down"), "Minimizing the current window.", "minimize_window"),
        "minimize this": ("hotkey", ("win", "down"), "Minimizing the current window.", "minimize_window"),
        "maximize window": ("hotkey", ("win", "up"), "Maximizing the current window.", "maximize_window"),
        "maximize this": ("hotkey", ("win", "up"), "Maximizing the current window.", "maximize_window"),
        "restore window": ("hotkey", ("win", "down"), "Restoring the current window.", "restore_window"),
        "switch window": ("hotkey", ("alt", "tab"), "Switching windows.", "switch_window"),
        "next window": ("hotkey", ("alt", "tab"), "Switching windows.", "switch_window"),
        "show desktop": ("hotkey", ("win", "d"), "Showing the desktop.", "show_desktop"),
    }
    if command in window_actions:
        _, keys, message, action = window_actions[command]
        success, error = _hotkey(*keys)
        return {"success": success, "message": message if success else error, "action": action}

    volume_actions = {
        "volume up": ("volumeup", "Increasing volume.", "volume_up"),
        "increase volume": ("volumeup", "Increasing volume.", "volume_up"),
        "volume down": ("volumedown", "Decreasing volume.", "volume_down"),
        "decrease volume": ("volumedown", "Decreasing volume.", "volume_down"),
        "mute": ("volumemute", "Muting volume.", "mute"),
        "unmute": ("volumemute", "Toggling mute.", "unmute"),
    }
    if command in volume_actions:
        key, message, action = volume_actions[command]
        success, error = _press(key)
        return {"success": success, "message": message if success else error, "action": action}

    if command in MEDIA_KEYS:
        success, error = _press(MEDIA_KEYS[command])
        return {"success": success, "message": f"{command.title()}. " if success else error, "action": command.replace(" ", "_")}

    if command in {"screenshot", "take a screenshot", "capture screen"}:
        success, message = _screenshot()
        return {"success": success, "message": message, "action": "screenshot"}

    info_commands = {"battery status": "battery", "battery": "battery", "cpu usage": "cpu", "cpu": "cpu", "ram usage": "ram", "ram": "ram", "system information": "system"}
    if command in info_commands:
        success, message = _system_info(info_commands[command])
        return {"success": success, "message": message, "action": "system_info"}

    now = dt.datetime.now()
    if command in {"what time is it", "tell me the time", "current time"}:
        return {"success": True, "message": f"It is {now.strftime('%I:%M %p').lstrip('0')}.", "action": "time"}
    if command in {"what is today's date", "what is todays date", "what day is today"}:
        return {"success": True, "message": f"Today is {now.strftime('%A, %B %d, %Y')}.", "action": "date"}

    for phrase, key in KEYS.items():
        if command == f"press {phrase}" or command == phrase:
            if key.startswith("hotkey:"):
                success, error = _hotkey(*key[7:].split(","))
            else:
                success, error = _press(key)
            return {"success": success, "message": f"Pressed {phrase}." if success else error, "action": "keyboard"}

    if command.startswith("type "):
        text = command[5:].strip()
        if not text:
            return {"success": False, "message": "Tell me what you would like me to type.", "action": "type"}
        if len(text) > 240:
            return _queue_confirmation("That is a long message. Are you sure you want me to type it?", lambda: _type_text(text))
        success, message = _type_text(text)
        return {"success": success, "message": message, "action": "type"}

    if command in {"lock laptop", "lock computer"}:
        success, message = _lock()
        return {"success": success, "message": message, "action": "lock"}
    if command == "sleep laptop":
        success, message = _sleep()
        return {"success": success, "message": message, "action": "sleep"}

    power_commands = {
        "shutdown laptop": "shutdown", "shutdown computer": "shutdown",
        "restart laptop": "restart", "restart computer": "restart",
        "sign out": "sign out",
    }
    if command in power_commands:
        action = power_commands[command]
        return _queue_confirmation(f"Are you sure you want to {action} the laptop?", lambda: _power_action(action))

    if command.startswith("open file "):
        success, message = _open_user_path(command[10:], "that file")
        return {"success": success, "message": message, "action": "open_file"}
    if command.startswith("open folder "):
        success, message = _open_user_path(command[12:], "that folder")
        return {"success": success, "message": message, "action": "open_folder"}
    if command.startswith("create folder "):
        success, message = _create_folder(command[14:])
        return {"success": success, "message": message, "action": "create_folder"}
    if command.startswith("delete file "):
        path = _safe_path(command[12:])
        if not path.exists() or not path.is_file():
            return {"success": False, "message": "I couldn't find that file.", "action": "delete_file"}
        return _queue_confirmation("Are you sure you want me to delete this file?", lambda: _delete_path(path))

    return {"success": False, "message": "Sorry, I don't know how to do that yet.", "action": "unknown"}


def _type_text(text: str) -> tuple[bool, str]:
    ready, error = _pyautogui_required()
    if not ready:
        return False, error
    try:
        pyautogui.write(text, interval=0.01)
        return True, "Done."
    except Exception as exc:
        return False, f"I couldn't type that: {exc}"