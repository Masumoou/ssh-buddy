r"""
autostart.py — Manage "Start on Boot" for SSH Buddy
  Windows : HKCU\Software\Microsoft\Windows\CurrentVersion\Run
  Linux   : ~/.config/autostart/ssh-buddy.desktop
"""

import platform
import sys
import os
from pathlib import Path

APP_NAME = "SSHBuddy"
_TRAY_SCRIPT = Path(__file__).resolve().parent / "tray.py"


# ── Public API ──────────────────────────────────────────────────────────────────

def enable_autostart():
    """Register SSH Buddy tray to start on login."""
    system = platform.system()
    if system == "Windows":
        _win_enable()
    else:
        _linux_enable()


def disable_autostart():
    """Remove SSH Buddy from login startup."""
    system = platform.system()
    if system == "Windows":
        _win_disable()
    else:
        _linux_disable()


def is_autostart_enabled() -> bool:
    """Return True if SSH Buddy is registered to start on login."""
    system = platform.system()
    if system == "Windows":
        return _win_is_enabled()
    else:
        return _linux_is_enabled()


# ── Windows (Registry) ─────────────────────────────────────────────────────────

def _win_get_pythonw() -> str:
    """Return the path to pythonw.exe alongside the current interpreter."""
    base = Path(sys.executable).parent
    pythonw = base / "pythonw.exe"
    if pythonw.exists():
        return str(pythonw)
    # Fallback: use python.exe itself
    return sys.executable


def _win_enable():
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    pythonw = _win_get_pythonw()
    value = f'"{pythonw}" "{_TRAY_SCRIPT}"'
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                             winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, value)
        winreg.CloseKey(key)
    except OSError as e:
        print(f"⚠  Could not set autostart registry key: {e}")


def _win_disable():
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                             winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
    except FileNotFoundError:
        pass  # Already removed
    except OSError as e:
        print(f"⚠  Could not remove autostart registry key: {e}")


def _win_is_enabled() -> bool:
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                             winreg.KEY_QUERY_VALUE)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except (FileNotFoundError, OSError):
        return False


# ── Linux (.desktop file) ──────────────────────────────────────────────────────

_DESKTOP_DIR = Path.home() / ".config" / "autostart"
_DESKTOP_FILE = _DESKTOP_DIR / "ssh-buddy.desktop"

_DESKTOP_CONTENT = f"""[Desktop Entry]
Type=Application
Name=SSH Buddy
Comment=SSH Buddy system tray
Exec={sys.executable} {_TRAY_SCRIPT}
Icon=utilities-terminal
Terminal=false
Categories=Network;Utility;
StartupNotify=false
X-GNOME-Autostart-enabled=true
"""


def _linux_enable():
    try:
        _DESKTOP_DIR.mkdir(parents=True, exist_ok=True)
        _DESKTOP_FILE.write_text(_DESKTOP_CONTENT.strip() + "\n")
        _DESKTOP_FILE.chmod(0o755)
    except OSError as e:
        print(f"⚠  Could not create autostart desktop file: {e}")


def _linux_disable():
    try:
        _DESKTOP_FILE.unlink(missing_ok=True)
    except OSError as e:
        print(f"⚠  Could not remove autostart desktop file: {e}")


def _linux_is_enabled() -> bool:
    return _DESKTOP_FILE.exists()
