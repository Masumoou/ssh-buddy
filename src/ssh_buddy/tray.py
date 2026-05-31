"""
tray.py — System tray application for SSH Buddy
Uses pystray + Pillow to show a tray icon with quick-access menu.
Run directly:  python tray.py   OR   pythonw tray.py (background)
"""

import sys
import threading
import platform

# ── Graceful import guard ───────────────────────────────────────────────────────
try:
    import pystray
    from pystray import MenuItem, Menu
except ImportError:
    print("⚠  pystray is not installed. System tray requires it.")
    print("   Install:  pip install pystray Pillow")
    sys.exit(1)

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("⚠  Pillow is not installed. System tray requires it.")
    print("   Install:  pip install Pillow")
    sys.exit(1)

from .db import init_db, get_all_servers, get_server
from .keystore import get_password
from .connector import connect_ssh
from .autostart import enable_autostart, disable_autostart, is_autostart_enabled
from .shell_setup import setup as shell_hook_setup, remove as shell_hook_remove, is_hook_installed


# ── Icon generation ─────────────────────────────────────────────────────────────

def _create_icon_image(size: int = 64) -> Image.Image:
    """Draw a lightning bolt ⚡ icon with Pillow."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Dark circle background
    pad = 2
    draw.ellipse([pad, pad, size - pad, size - pad],
                 fill=(30, 30, 46, 255))       # #1e1e2e  (Catppuccin base)

    # Lightning bolt polygon — scaled to icon size
    s = size / 64.0
    bolt = [
        (28 * s,  8 * s),
        (18 * s, 30 * s),
        (28 * s, 30 * s),
        (22 * s, 56 * s),
        (46 * s, 24 * s),
        (34 * s, 24 * s),
        (40 * s,  8 * s),
    ]
    draw.polygon(bolt, fill=(249, 226, 175, 255))   # #f9e2af  (Catppuccin yellow)

    # Thin bright outline for the bolt
    draw.line(bolt + [bolt[0]], fill=(205, 214, 244, 200), width=max(1, int(s)))

    return img


# ── Recent servers helper ───────────────────────────────────────────────────────

def _get_recent_servers(limit: int = 5) -> list:
    """Return up to `limit` most recently added servers."""
    all_srv = get_all_servers()
    # Sort by id descending (most recently added first)
    all_srv.sort(key=lambda s: s.get("id", 0), reverse=True)
    return all_srv[:limit]


# ── Actions ─────────────────────────────────────────────────────────────────────

def _open_gui(icon=None, item=None):
    """Open the SSH Buddy GUI in a separate thread (non-blocking)."""
    def _run():
        from .security import require_master_password
        if not require_master_password(force_gui=True):
            return
        from .gui import run_gui
        run_gui()
    threading.Thread(target=_run, daemon=True).start()


def _open_add_server(icon=None, item=None):
    """Open a Tkinter window with the Add Server dialog."""
    def _run():
        from .security import require_master_password
        if not require_master_password(force_gui=True):
            return
        import tkinter as tk
        from .gui import SSHBuddyApp
        init_db()
        root = tk.Tk()
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        app = SSHBuddyApp(root)
        # Trigger add-server dialog after the window is ready
        root.after(300, app._add_server)
        root.mainloop()
    threading.Thread(target=_run, daemon=True).start()


def _connect_recent(alias: str):
    """Connect to a server by alias (runs in background thread)."""
    def _run():
        server = get_server(alias)
        if not server:
            return
        password = get_password(alias)
        connect_ssh(server["ip"], server["username"],
                    server["port"], password, from_gui=True)
    threading.Thread(target=_run, daemon=True).start()


def _toggle_autostart(icon, item):
    """Toggle the Start on Boot setting."""
    if is_autostart_enabled():
        disable_autostart()
    else:
        enable_autostart()
    # Rebuild menu to reflect new state
    icon.update_menu()


def _toggle_ssh_hook(icon, item):
    """Toggle the ssh → wrapper.py shell hook."""
    if is_hook_installed():
        msgs = shell_hook_remove()
    else:
        msgs = shell_hook_setup()
    # Print feedback to console (useful when tray is run from terminal)
    for m in msgs:
        print(m)
    icon.update_menu()


def _quit(icon, item):
    """Stop the tray icon and exit."""
    icon.stop()


# ── Menu builder ────────────────────────────────────────────────────────────────

def _build_menu() -> Menu:
    """Build the right-click context menu."""
    init_db()
    recent = _get_recent_servers(5)

    # Recent servers sub-items
    recent_items = []
    if recent:
        for srv in recent:
            label = f"{srv['alias']}  ({srv['username']}@{srv['ip']})"
            alias = srv["alias"]
            recent_items.append(
                MenuItem(label, lambda icon, item, a=alias: _connect_recent(a))
            )
    else:
        recent_items.append(MenuItem("(no servers yet)", None, enabled=False))

    menu = Menu(
        MenuItem("⚡ Open SSH Buddy", _open_gui, default=True),
        MenuItem("➕ Add Server", _open_add_server),
        Menu.SEPARATOR,
        MenuItem("Recent Servers", Menu(*recent_items)),
        Menu.SEPARATOR,
        MenuItem(
            "🚀 Start on Boot",
            _toggle_autostart,
            checked=lambda item: is_autostart_enabled(),
        ),
        MenuItem(
            "🔗 Setup SSH Hook",
            _toggle_ssh_hook,
            checked=lambda item: is_hook_installed(),
        ),
        Menu.SEPARATOR,
        MenuItem("Exit", _quit),
    )
    return menu


# ── Tray app ────────────────────────────────────────────────────────────────────

def run_tray():
    """Create and run the system tray icon (blocking)."""
    init_db()
    icon_image = _create_icon_image(64)

    icon = pystray.Icon(
        name="ssh-buddy",
        icon=icon_image,
        title="SSH Buddy",
        menu=_build_menu(),
    )

    # Left-click → open GUI  (pystray supports this via on_activate on some backends)
    icon.on_activate = _open_gui

    icon.run()


# ── Entry point ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_tray()
