"""
shell_setup.py — Shell integration for SSH Buddy wrapper
Installs (or removes) an ssh alias/function so that every `ssh user@host`
command is transparently routed through wrapper.py.

Linux  : alias ssh='python /path/to/wrapper.py'   → ~/.bashrc, ~/.zshrc
Windows: function ssh { python C:\\path\\to\\wrapper.py $args }  → $PROFILE
"""

import os
import sys
import platform
from pathlib import Path

# Absolute path to scripts
_WRAPPER = str(Path(__file__).resolve().parent / "wrapper.py")
_GUI_SCRIPT = str(Path(__file__).resolve().parent.parent.parent / "ssh_buddy.py")

# Markers used to find our lines inside rc / profile files
_MARKER_BEGIN = "# >>> ssh-buddy hook >>>"
_MARKER_END   = "# <<< ssh-buddy hook <<<"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _read_file(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


def _has_hook(text: str) -> bool:
    return _MARKER_BEGIN in text


def _remove_hook(text: str) -> str:
    """Remove the ssh-buddy block (inclusive of markers) from text."""
    lines = text.splitlines(keepends=True)
    out = []
    inside = False
    for line in lines:
        if _MARKER_BEGIN in line:
            inside = True
            continue
        if _MARKER_END in line:
            inside = False
            continue
        if not inside:
            out.append(line)
    return "".join(out)


def _inject_hook(text: str, block: str) -> str:
    """Append the ssh-buddy block to text (remove existing first)."""
    cleaned = _remove_hook(text)
    # Ensure trailing newline before our block
    if cleaned and not cleaned.endswith("\n"):
        cleaned += "\n"
    return cleaned + block


# ── Linux ──────────────────────────────────────────────────────────────────────

def _setup_linux() -> list[str]:
    """Install the ssh alias into bash/zsh rc files. Returns list of messages."""
    python = sys.executable or "python3"
    alias_line = f"alias ssh='{python} {_WRAPPER}'"
    gui_alias = f"alias sshbuddy='{python} {_GUI_SCRIPT} gui'"
    block = f"\n{_MARKER_BEGIN}\n{alias_line}\n{gui_alias}\n{_MARKER_END}\n"

    messages = []
    rc_files = [Path.home() / ".bashrc", Path.home() / ".zshrc"]

    for rc in rc_files:
        content = _read_file(rc)
        if _has_hook(content):
            messages.append(f"  ✓ Already installed in {rc}")
            continue
        new_content = _inject_hook(content, block)
        rc.write_text(new_content, encoding="utf-8")
        messages.append(f"  ✓ Added ssh alias to {rc}")

    messages.append("")
    messages.append("  To activate NOW, run:")
    messages.append("    source ~/.bashrc")
    messages.append("  (or restart your terminal)")
    return messages


def _remove_linux() -> list[str]:
    """Remove the ssh alias from bash/zsh rc files."""
    messages = []
    rc_files = [Path.home() / ".bashrc", Path.home() / ".zshrc"]

    for rc in rc_files:
        content = _read_file(rc)
        if not _has_hook(content):
            continue
        new_content = _remove_hook(content)
        rc.write_text(new_content, encoding="utf-8")
        messages.append(f"  ✓ Removed ssh hook from {rc}")

    if not messages:
        messages.append("  (no hook found to remove)")
    messages.append("")
    messages.append("  Run:  source ~/.bashrc   to apply changes.")
    return messages


# ── Windows ────────────────────────────────────────────────────────────────────

def _get_ps_profiles() -> list[Path]:
    """Return the paths to the current-user PowerShell profiles (both v5 and v7)."""
    docs = Path.home() / "Documents"
    profiles = []
    for sub in ["WindowsPowerShell", "PowerShell"]:
        p = docs / sub / "Microsoft.PowerShell_profile.ps1"
        p.parent.mkdir(parents=True, exist_ok=True)
        profiles.append(p)
    return profiles


def _setup_windows() -> list[str]:
    """Install the ssh function into the PowerShell profiles."""
    python = sys.executable or "python"
    wrapper_win = _WRAPPER.replace("/", "\\")
    gui_win = _GUI_SCRIPT.replace("/", "\\")
    func = f'function ssh {{ & "{python}" "{wrapper_win}" @args }}'
    gui_func = f'function sshbuddy {{ & "{python}" "{gui_win}" gui @args }}'
    block = f"\n{_MARKER_BEGIN}\n{func}\n{gui_func}\n{_MARKER_END}\n"

    messages = []
    
    profiles = _get_ps_profiles()
    for profile in profiles:
        content = _read_file(profile)
        if _has_hook(content):
            content = _remove_hook(content)
        new_content = _inject_hook(content, block)
        profile.write_text(new_content, encoding="utf-8")
        messages.append(f"  ✓ SSH function written to {profile}")

    # Reload the profile and verify
    import subprocess
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f". '{profile}'"],
            check=True, capture_output=True, timeout=10,
        )
        messages.append("  ✓ Profile reloaded")
    except Exception as exc:
        messages.append(f"  ⚠ Could not auto-reload profile: {exc}")

    try:
        result = subprocess.run(
            ["powershell", "-Command",
             f". '{profile}'; Get-Command ssh | Format-List CommandType"],
            check=True, capture_output=True, text=True, timeout=10,
        )
        if "Function" in result.stdout:
            messages.append("  ✓ Verified: ssh is now a PowerShell Function")
        else:
            messages.append(f"  ⚠ ssh command type: {result.stdout.strip()}")
    except Exception as exc:
        messages.append(f"  ⚠ Could not verify ssh function: {exc}")

    messages.append("")
    messages.append("  To activate in current session, run:")
    messages.append(f"    . '{profile}'")
    messages.append("  (or restart your terminal)")
    return messages


def _remove_windows() -> list[str]:
    """Remove the ssh function from the PowerShell profiles."""
    profiles = _get_ps_profiles()
    messages = []
    
    for profile in profiles:
        content = _read_file(profile)
        if not _has_hook(content):
            continue
        new_content = _remove_hook(content)
        profile.write_text(new_content, encoding="utf-8")
        messages.append(f"  ✓ Removed ssh hook from {profile}")

    if not messages:
        messages.append("  (no hook found to remove)")
    messages.append("")
    messages.append("  Restart your terminal to apply changes.")
    return messages


# ── Public API ─────────────────────────────────────────────────────────────────

def is_hook_installed() -> bool:
    """Check whether the ssh hook is currently installed."""
    system = platform.system()
    if system == "Windows":
        for profile in _get_ps_profiles():
            if _has_hook(_read_file(profile)):
                return True
        return False
    else:
        for rc in [Path.home() / ".bashrc", Path.home() / ".zshrc"]:
            if _has_hook(_read_file(rc)):
                return True
        return False


def setup() -> list[str]:
    """Install the ssh hook. Returns list of user-facing messages."""
    system = platform.system()
    if system == "Windows":
        return _setup_windows()
    else:
        return _setup_linux()


def remove() -> list[str]:
    """Remove the ssh hook. Returns list of user-facing messages."""
    system = platform.system()
    if system == "Windows":
        return _remove_windows()
    else:
        return _remove_linux()


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import io

    def _safe_print(text: str):
        """Print text, replacing chars the console can't encode."""
        try:
            print(text)
        except UnicodeEncodeError:
            safe = text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
                sys.stdout.encoding or "utf-8", errors="replace"
            )
            print(safe)

    args = sys.argv[1:]
    if args and args[0] in ("remove", "uninstall", "disable"):
        _safe_print("[*] Removing SSH Buddy hook ...")
        for line in remove():
            _safe_print(line)
    else:
        _safe_print("[*] Installing SSH Buddy hook ...")
        for line in setup():
            _safe_print(line)

