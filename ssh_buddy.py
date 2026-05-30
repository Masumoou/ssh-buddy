#!/usr/bin/env python3
"""
ssh_buddy.py — SSH Buddy entry point
Usage:
  python ssh_buddy.py              → CLI help
  python ssh_buddy.py gui          → GUI
  python ssh_buddy.py install      → one-click installer
  python ssh_buddy.py tray         → start system tray app
  python ssh_buddy.py wrapper u@ip → SSH wrapper (intercept mode)
  python ssh_buddy.py add          → add a server
  python ssh_buddy.py connect      → pick & connect
  python ssh_buddy.py connect web  → search 'web' then connect
  python ssh_buddy.py list         → list all
  python ssh_buddy.py search 207   → search by IP fragment
  python ssh_buddy.py delete alias → delete a server
  python ssh_buddy.py export       → export to JSON
  python ssh_buddy.py import f.json→ import from JSON
"""

import sys


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""

    # GUI
    if cmd in ("gui", "--gui", "-g"):
        from gui import run_gui
        run_gui()

    # One-click installer
    elif cmd in ("install", "setup"):
        from installer import run_installer
        run_installer()

    # System tray app
    elif cmd == "tray":
        from tray import run_tray
        run_tray()

    # SSH wrapper (forward remaining args as if they were ssh args)
    elif cmd == "wrapper":
        from wrapper import main as wrapper_main
        # Rebuild sys.argv so wrapper sees: wrapper.py [user@host ...]
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        wrapper_main()

    # Everything else → CLI
    else:
        from cli import run_cli
        run_cli()


if __name__ == "__main__":
    main()
