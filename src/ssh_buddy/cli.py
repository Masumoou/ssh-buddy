"""
cli.py — Command-line interface for SSH Buddy
Commands: add | list | search | connect | delete | import | export
"""

import argparse
import getpass
import json
import sys
from pathlib import Path

from .db import (
    init_db, add_server, get_all_servers, get_server,
    search_servers, delete_server, update_server,
)
from .keystore import save_password, get_password, delete_password
from .connector import connect_ssh

# ── ANSI colours (work on Linux, Windows 10+) ──────────────────────────────
R  = "\033[91m"
G  = "\033[92m"
Y  = "\033[93m"
B  = "\033[94m"
C  = "\033[96m"
W  = "\033[97m"
DIM = "\033[2m"
RST = "\033[0m"

HEADER = f"""
{B}  ███████╗███████╗██╗  ██╗    ██████╗ ██╗   ██╗██████╗ ██████╗ ██╗   ██╗
  ██╔════╝██╔════╝██║  ██║    ██╔══██╗██║   ██║██╔══██╗██╔══██╗╚██╗ ██╔╝
  ███████╗███████╗███████║    ██████╔╝██║   ██║██║  ██║██║  ██║ ╚████╔╝
  ╚════██║╚════██║██╔══██║    ██╔══██╗██║   ██║██║  ██║██║  ██║  ╚██╔╝
  ███████║███████║██║  ██║    ██████╔╝╚██████╔╝██████╔╝██████╔╝   ██║
  ╚══════╝╚══════╝╚═╝  ╚═╝    ╚═════╝  ╚═════╝ ╚═════╝ ╚═════╝   ╚═╝{RST}
  {DIM}Your SSH Connection Manager{RST}
"""


def _print_table(servers):
    if not servers:
        print(f"  {Y}No servers found.{RST}")
        return
    w = [20, 18, 14, 6, 22, 30]
    hdr = ["ALIAS", "IP", "USERNAME", "PORT", "TAGS", "NOTES"]
    fmt = "  " + "  ".join(f"{{:<{n}}}" for n in w)
    sep = "  " + "  ".join("-" * n for n in w)
    print(f"\n{B}" + fmt.format(*hdr) + RST)
    print(DIM + sep + RST)
    for i, s in enumerate(servers, 1):
        notes = s.get("notes", "")
        if len(notes) > 28:
            notes = notes[:25] + "..."
        row = fmt.format(
            s["alias"], s["ip"], s["username"], s["port"],
            s.get("tags", ""), notes
        )
        colour = C if i % 2 == 0 else W
        print(colour + row + RST)
    print()


def _pick_server(results, query=""):
    if not results:
        print(f"{R}✗ No server found matching '{query}'{RST}")
        return None
    if len(results) == 1:
        return results[0]
    _print_table(results)
    try:
        choice = int(input(f"  {Y}Pick number [1-{len(results)}]: {RST}")) - 1
        return results[choice]
    except (ValueError, IndexError):
        print(f"{R}✗ Invalid choice.{RST}")
        return None


# ── Commands ───────────────────────────────────────────────────────────────

def cmd_add(_args):
    print(f"\n{B}=== Add New Server ==={RST}\n")
    alias    = input(f"  Alias       {DIM}(e.g. prod-web){RST}: ").strip()
    ip       = input(f"  IP Address  {DIM}(e.g. 10.10.207.31){RST}: ").strip()
    username = input(f"  Username    {DIM}(e.g. ubuntu){RST}: ").strip()
    port_raw = input(f"  Port        {DIM}[22]{RST}: ").strip() or "22"
    tags     = input(f"  Tags        {DIM}(comma-separated, e.g. oblak,wcf){RST}: ").strip()
    notes    = input(f"  Notes       {DIM}(what is this server for?){RST}: ").strip()

    if not alias or not ip or not username:
        print(f"\n{R}✗ Alias, IP, and Username are required.{RST}")
        return

    try:
        port = int(port_raw)
    except ValueError:
        port = 22

    ok, msg = add_server(alias, ip, username, port, tags, notes)
    if not ok:
        print(f"\n{R}✗ {msg}{RST}")
        return

    save_pass = input(f"\n  Save password in keychain? {DIM}(y/N){RST}: ").strip().lower()
    if save_pass == "y":
        pw = getpass.getpass("  Password: ")
        if pw:
            save_password(alias, pw)
            print(f"  {G}✓ Password saved{RST}")

    print(f"\n{G}✓ {msg} → {alias}{RST}")


def cmd_list(_args):
    servers = get_all_servers()
    print(f"\n{B}=== All Servers ({len(servers)}) ==={RST}")
    _print_table(servers)


def cmd_search(args):
    query = " ".join(args.query)
    results = search_servers(query)
    print(f"\n{B}=== Search: '{query}' → {len(results)} result(s) ==={RST}")
    _print_table(results)


def cmd_connect(args):
    query = " ".join(args.target) if args.target else ""

    if query:
        server = get_server(query)
        if not server:
            results = search_servers(query)
            server = _pick_server(results, query)
    else:
        servers = get_all_servers()
        if not servers:
            print(f"{Y}No servers saved. Add one with:  ssh-buddy add{RST}")
            return
        _print_table(servers)
        try:
            choice = int(input(f"  {Y}Pick number to connect: {RST}")) - 1
            server = servers[choice]
        except (ValueError, IndexError):
            print(f"{R}✗ Invalid choice.{RST}")
            return

    if not server:
        return

    print(f"\n{C}→ {server['alias']} — {server['username']}@{server['ip']}:{server['port']}{RST}")
    if server.get("tags"):
        print(f"  {DIM}tags: {server['tags']}{RST}")
    if server.get("notes"):
        print(f"  {DIM}notes: {server['notes']}{RST}")

    password = get_password(server["alias"])

    if not password:
        ask = input(f"\n  No saved password. Enter now? {DIM}(Y/n){RST}: ").strip().lower()
        if ask != "n":
            password = getpass.getpass("  Password (Enter = key-based auth): ")
            password = password or None

    print(f"\n{G}Launching SSH...{RST}\n")
    connect_ssh(server["ip"], server["username"], server["port"], password, from_gui=False)


def cmd_delete(args):
    server = get_server(args.alias)
    if not server:
        print(f"{R}✗ Server '{args.alias}' not found.{RST}")
        return
    confirm = input(
        f"  Delete {Y}{server['alias']}{RST} ({server['username']}@{server['ip']})? {DIM}(y/N){RST}: "
    ).strip().lower()
    if confirm == "y":
        delete_server(args.alias)
        delete_password(args.alias)
        print(f"{G}✓ Deleted '{args.alias}'{RST}")
    else:
        print("Cancelled.")


def cmd_export(args):
    servers = get_all_servers()
    out = Path(args.file)
    # Export without passwords
    out.write_text(json.dumps(servers, indent=2))
    print(f"{G}✓ Exported {len(servers)} servers → {out}{RST}")
    print(f"{Y}Note: Passwords are NOT exported (security).{RST}")


def cmd_import(args):
    src = Path(args.file)
    if not src.exists():
        print(f"{R}✗ File not found: {src}{RST}")
        return
    data = json.loads(src.read_text())
    added = 0
    for s in data:
        ok, _ = add_server(
            s["alias"], s["ip"], s["username"],
            s.get("port", 22), s.get("tags", ""), s.get("notes", "")
        )
        if ok:
            added += 1
    print(f"{G}✓ Imported {added}/{len(data)} servers{RST}")


# ── Main ───────────────────────────────────────────────────────────────────

def run_cli():
    import sys
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    init_db()

    parser = argparse.ArgumentParser(
        prog="ssh-buddy",
        description="SSH Buddy — never forget a server again"
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("add",    help="Add a new server (interactive)")
    sub.add_parser("list",   help="List all saved servers")

    sp = sub.add_parser("search",  help="Search servers (IP, alias, user, tags, notes)")
    sp.add_argument("query", nargs="+")

    cp = sub.add_parser("connect", help="Connect to a server")
    cp.add_argument("target", nargs="*", help="Alias, IP, username, or keyword")

    dp = sub.add_parser("delete",  help="Delete a saved server")
    dp.add_argument("alias")

    ep = sub.add_parser("export",  help="Export servers to JSON")
    ep.add_argument("file", nargs="?", default="ssh_buddy_export.json")

    ip = sub.add_parser("import",  help="Import servers from JSON")
    ip.add_argument("file")

    sub.add_parser("gui", help="Launch the GUI")

    args = parser.parse_args()

    if args.command == "add":
        cmd_add(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "connect":
        cmd_connect(args)
    elif args.command == "delete":
        cmd_delete(args)
    elif args.command == "export":
        cmd_export(args)
    elif args.command == "import":
        cmd_import(args)
    elif args.command == "gui":
        from .security import require_master_password
        if require_master_password():
            from .gui import run_gui
            run_gui()
        else:
            print("\n❌ Access Denied: Master password incorrect.\n")
    else:
        print(HEADER)
        parser.print_help()
