"""
connector.py — SSH execution engine
  Linux   : sshpass (if available) + ssh
  Windows : plink (-pw) → auto-type helper (WriteConsoleInput) → fallback
  GUI mode: opens SSH in a NEW terminal window
  CLI mode: runs SSH in the current terminal
"""

import subprocess
import platform
import shutil
import sys
import os
import tempfile
import time
import base64


def connect_ssh(ip: str, username: str, port: int = 22,
                password: str | None = None, from_gui: bool = False, try_key_first: bool = False):
    system = platform.system()
    ssh_args = ["-p", str(port), "-o", "StrictHostKeyChecking=accept-new"]
    
    if try_key_first:
        password = None
    elif password:
        # User explicitly wants password auth. Prevent SSH from auto-using local keys.
        ssh_args.extend(["-o", "PubkeyAuthentication=no"])
        
    ssh_args.append(f"{username}@{ip}")

    if system == "Windows":
        _connect_windows(ssh_args, password, from_gui)
    else:
        _connect_linux(ssh_args, password, from_gui)

def check_key_auth(ip: str, username: str, port: int = 22) -> bool:
    """Test if we can connect without a password (using SSH key)."""
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", 
           "-o", "StrictHostKeyChecking=accept-new",
           "-p", str(port), f"{username}@{ip}", "echo ok"]
    try:
        kwargs = {}
        if platform.system() == "Windows":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
        return res.returncode == 0
    except Exception:
        return False

def copy_ssh_key(ip: str, username: str, port: int, password: str, pubkey: str) -> bool:
    """Copies the public key to the remote server using the provided password."""
    system = platform.system()
    remote_cmd = f"mkdir -p ~/.ssh && echo {pubkey.strip()} >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
    
    if system == "Linux" and shutil.which("sshpass"):
        cmd = ["sshpass", "-p", password, "ssh", "-p", str(port), "-o", "StrictHostKeyChecking=accept-new",
               f"{username}@{ip}", remote_cmd]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return res.returncode == 0
    else:
        if shutil.which("plink"):
            plink_cmd = ["plink", "-ssh", "-P", str(port), "-pw", password, f"{username}@{ip}", remote_cmd]
            kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if system == "Windows" else {}
            res = subprocess.run(plink_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
            return res.returncode == 0
        else:
            ssh_args = ["-p", str(port), "-o", "StrictHostKeyChecking=accept-new", f"{username}@{ip}", f'"{remote_cmd}"']
            helper = _create_helper_script(ssh_args, password)
            python_exe = sys.executable or "python"
            kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if system == "Windows" else {}
            subprocess.run([python_exe, helper], stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
            return True

def remove_ssh_key(ip: str, username: str, port: int, password: str, pubkey: str) -> bool:
    """Removes the specified public key from the remote server's authorized_keys."""
    system = platform.system()
    
    # Extract just the base64 part to avoid issues with comments
    parts = pubkey.strip().split()
    if len(parts) >= 2:
        search_str = parts[1]
    else:
        search_str = pubkey.strip()
        
    remote_cmd = f"grep -vF '{search_str}' ~/.ssh/authorized_keys > ~/.ssh/authorized_keys.tmp && mv ~/.ssh/authorized_keys.tmp ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
    
    if system == "Linux" and shutil.which("sshpass"):
        cmd = ["sshpass", "-p", password, "ssh", "-p", str(port), "-o", "StrictHostKeyChecking=accept-new",
               f"{username}@{ip}", remote_cmd]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return res.returncode == 0
    else:
        if shutil.which("plink"):
            plink_cmd = ["plink", "-ssh", "-P", str(port), "-pw", password, f"{username}@{ip}", remote_cmd]
            kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if system == "Windows" else {}
            res = subprocess.run(plink_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
            return res.returncode == 0
        else:
            ssh_args = ["-p", str(port), "-o", "StrictHostKeyChecking=accept-new", f"{username}@{ip}", f'"{remote_cmd}"']
            helper = _create_helper_script(ssh_args, password)
            python_exe = sys.executable or "python"
            kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if system == "Windows" else {}
            subprocess.run([python_exe, helper], stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
            return True


# ── Linux ───────────────────────────────────────────────────────────────────

def _connect_linux(ssh_args, password, from_gui):
    if password and shutil.which("sshpass"):
        full_cmd = ["sshpass", "-p", password, "ssh"] + ssh_args
    else:
        if password and not shutil.which("sshpass"):
            print("⚠  sshpass not found → password won't be auto-filled.")
            print("   Install: sudo apt install sshpass")
            print(f"   Password to enter manually: {password}")
        full_cmd = ["ssh"] + ssh_args

    if from_gui:
        _open_linux_terminal(full_cmd)
    else:
        subprocess.run(full_cmd)


def _open_linux_terminal(cmd: list):
    cmd_str = " ".join(cmd)
    candidates = [
        ["gnome-terminal", "--"] + cmd,
        ["xfce4-terminal", "--command", cmd_str],
        ["konsole", "--noclose", "-e"] + cmd,
        ["mate-terminal", "-e", cmd_str],
        ["tilix", "-e"] + cmd,
        ["xterm", "-e", cmd_str],
        ["lxterminal", "-e", cmd_str],
    ]
    for c in candidates:
        if shutil.which(c[0]):
            subprocess.Popen(c)
            return
    subprocess.Popen(cmd)


# ── Windows ─────────────────────────────────────────────────────────────────

def _connect_windows(ssh_args, password, from_gui):
    # Method 1: plink supports -pw flag natively (best)
    if password and shutil.which("plink"):
        host_part = ssh_args[-1]
        port = ssh_args[1]
        plink_cmd = ["plink", "-ssh", "-P", port, "-pw", password, host_part]
        _launch_windows_simple(plink_cmd, from_gui)
        return

    # Method 2: auto-type password using helper script
    if password:
        _launch_with_auto_type(ssh_args, password, from_gui)
        return

    # Method 3: No password (key-based auth)
    _launch_windows_simple(["ssh"] + ssh_args, from_gui)


def _launch_with_auto_type(ssh_args, password, from_gui):
    """
    Launch SSH and auto-type the saved password using a helper Python
    script that uses WriteConsoleInput (Windows API) to inject keystrokes
    directly into the console buffer — this is what ssh.exe reads from.
    """
    helper = _create_helper_script(ssh_args, password)
    python_exe = sys.executable or "python"

    if from_gui:
        # Open helper in a NEW cmd window
        cmd = f'start "SSH Buddy" "{python_exe}" "{helper}"'
        try:
            os.system(cmd)
        except Exception:
            # fallback
            _copy_to_clipboard(password)
            os.system(f'start "SSH Buddy" cmd /k "ssh {" ".join(ssh_args)}"')
    else:
        # CLI mode: run helper in current console
        try:
            subprocess.run([python_exe, helper])
        except Exception:
            _copy_to_clipboard(password)
            print("[SSH Buddy] Password copied to clipboard — Ctrl+V to paste.")
            subprocess.run(["ssh"] + ssh_args)


def _create_helper_script(ssh_args: list, password: str) -> str:
    """
    Create a temp Python script that:
      1. Starts SSH via os.system (inherits console)
      2. A background thread waits ~4s then types the password
         into the console input buffer using WriteConsoleInput
    """
    b64pw = base64.b64encode(password.encode()).decode()
    ssh_cmd_str = "ssh " + " ".join(ssh_args)
    # Escape backslashes and quotes for embedding in the script
    ssh_cmd_safe = ssh_cmd_str.replace("\\", "\\\\").replace('"', '\\"')

    script = f'''# SSH Buddy auto-connect helper — auto-deletes after use
import os, sys, time, threading, base64, ctypes, ctypes.wintypes

PASSWORD = base64.b64decode("{b64pw}").decode()
SSH_CMD = "{ssh_cmd_safe}"

def _write_to_console(text):
    """Type text into the console input buffer via Windows API."""
    STD_INPUT_HANDLE = -10
    hnd = ctypes.windll.kernel32.GetStdHandle(STD_INPUT_HANDLE)
    KEY_EVENT = 0x0001

    class KEV(ctypes.Structure):
        _fields_ = [
            ("bKeyDown", ctypes.wintypes.BOOL),
            ("wRepeatCount", ctypes.wintypes.WORD),
            ("wVirtualKeyCode", ctypes.wintypes.WORD),
            ("wVirtualScanCode", ctypes.wintypes.WORD),
            ("uChar", ctypes.c_wchar),
            ("dwControlKeyState", ctypes.wintypes.DWORD),
        ]

    class EVT_U(ctypes.Union):
        _fields_ = [("KeyEvent", KEV)]

    class INPUT_RECORD(ctypes.Structure):
        _fields_ = [("EventType", ctypes.wintypes.WORD), ("Event", EVT_U)]

    written = ctypes.wintypes.DWORD(0)
    for ch in text:
        for down in (True, False):
            rec = INPUT_RECORD()
            rec.EventType = KEY_EVENT
            rec.Event.KeyEvent.bKeyDown = down
            rec.Event.KeyEvent.wRepeatCount = 1
            rec.Event.KeyEvent.wVirtualKeyCode = 0
            rec.Event.KeyEvent.wVirtualScanCode = 0
            rec.Event.KeyEvent.uChar = ch
            rec.Event.KeyEvent.dwControlKeyState = 0
            ctypes.windll.kernel32.WriteConsoleInputW(
                hnd, ctypes.byref(rec), 1, ctypes.byref(written))

def _auto_type():
    time.sleep(4)
    _write_to_console(PASSWORD + "\\r")

threading.Thread(target=_auto_type, daemon=True).start()
os.system(SSH_CMD)

# cleanup
try:
    os.remove(sys.argv[0])
except Exception:
    pass
'''

    script_dir = os.path.join(tempfile.gettempdir(), "ssh_buddy")
    os.makedirs(script_dir, exist_ok=True)
    path = os.path.join(script_dir, f"auto_{int(time.time())}.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(script)
    return path


def _launch_windows_simple(cmd: list, from_gui: bool):
    """Launch a command on Windows (no password handling)."""
    if not from_gui:
        subprocess.run(cmd)
        return

    cmd_str = " ".join(cmd)
    try:
        os.system(f'start "SSH Buddy" cmd /k "{cmd_str}"')
        return
    except Exception:
        pass
    try:
        subprocess.Popen(
            f'Start-Process cmd -ArgumentList \'/k {cmd_str}\' -WindowStyle Normal',
            shell=True)
        return
    except Exception:
        pass
    subprocess.Popen(cmd, shell=True)


def _copy_to_clipboard(password: str):
    """Copy password to Windows clipboard silently."""
    try:
        subprocess.run(["clip"], input=password.encode(),
                       check=True, capture_output=True)
    except Exception:
        pass
