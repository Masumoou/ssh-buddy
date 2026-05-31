import os
import sys
import json
import getpass
import hashlib
import string
import tkinter as tk
from pathlib import Path

MASTER_FILE = Path.home() / ".ssh_buddy" / "master.json"

# UI Colors for GUI Prompt
BG       = "#0A111E"
BG2      = "#060B14"
SURFACE  = "#111827"
BORDER   = "#1F2937"
TEXT     = "#F9FAFB"
MUTED    = "#CBD5E1"
BLUE     = "#3B82F6"
GREEN    = "#22C55E"
RED      = "#EF4444"

def _get_master_data() -> dict | None:
    if MASTER_FILE.exists():
        try:
            return json.loads(MASTER_FILE.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None

def _save_master_data(salt: bytes, key: bytes):
    MASTER_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "salt": salt.hex(),
        "hash": key.hex()
    }
    MASTER_FILE.write_text(json.dumps(data), encoding="utf-8")

def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)

def is_master_password_set() -> bool:
    return _get_master_data() is not None

def validate_password_strength(pwd: str) -> tuple[bool, str]:
    if len(pwd) < 12 or len(pwd) > 16:
        return False, "Password must be 12 to 16 characters long."
    if not any(c.isupper() for c in pwd):
        return False, "Password must contain at least one UPPERCASE letter."
    if not any(c.islower() for c in pwd):
        return False, "Password must contain at least one LOWERCASE letter."
    if not any(c.isdigit() for c in pwd):
        return False, "Password must contain at least one NUMBER."
    if not any(c in string.punctuation for c in pwd):
        return False, "Password must contain at least one SPECIAL character."
    return True, ""

# ── CLI Prompts ────────────────────────────────────────────────────────────

def _setup_master_password_cli():
    print("\n🔒 SSH Buddy - Security Setup")
    print("Please set a Master Password to protect your saved servers.")
    print("Requirements: 12-16 chars, 1 uppercase, 1 lowercase, 1 number, 1 special char.\n")
    while True:
        pwd = getpass.getpass("Enter new Master Password: ")
        is_valid, msg = validate_password_strength(pwd)
        if not is_valid:
            print(f"❌ {msg}\n")
            continue
        
        pwd_confirm = getpass.getpass("Confirm Master Password: ")
        if pwd != pwd_confirm:
            print("❌ Passwords do not match. Try again.\n")
            continue
            
        salt = os.urandom(16)
        key = _hash_password(pwd, salt)
        _save_master_data(salt, key)
        print("✅ Master Password set successfully!\n")
        break

def verify_master_password(pwd: str) -> bool:
    data = _get_master_data()
    if not data:
        return False
    salt = bytes.fromhex(data["salt"])
    stored_hash = bytes.fromhex(data["hash"])
    return _hash_password(pwd, salt) == stored_hash

def prompt_master_password_cli() -> bool:
    """Prompt for master password in the terminal."""
    if not is_master_password_set():
        _setup_master_password_cli()
        return True
    
    for _ in range(3):
        pwd = getpass.getpass("🔑 Enter Master Password: ")
        if verify_master_password(pwd):
            return True
        print("❌ Incorrect password.")
    return False

# ── GUI Prompts ────────────────────────────────────────────────────────────

class MasterPasswordDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("SSH Buddy Security")
        self.is_setup = not is_master_password_set()
        
        height = 360 if self.is_setup else 220
        self.geometry(f"400x{height}")
        self.configure(bg=BG)
        self.resizable(False, False)
        
        # Do NOT use transient if parent is withdrawn, otherwise it won't show in taskbar
        # self.transient(parent)
        self.grab_set()
        
        # Force window to the front
        self.attributes('-topmost', True)
        self.focus_force()
        self.after(100, lambda: self.attributes('-topmost', False))
        
        self.result = False
        
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
        
        self._build_ui()
        
    def _build_ui(self):
        title = "Create Master Password" if self.is_setup else "Enter Master Password"
        tk.Label(self, text="🔒 " + title, bg=BG, fg=BLUE, font=("Segoe UI", 14, "bold")).pack(pady=(20, 10))
        
        if self.is_setup:
            lbl = "Requirements: 12-16 chars, 1 uppercase,\n1 lowercase, 1 number, 1 special char."
            tk.Label(self, text=lbl, bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(pady=(0, 10))
        
        # Password entry
        f1 = tk.Frame(self, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        f1.pack(padx=30, pady=(10, 5), fill="x")
        self.entry_pwd = tk.Entry(f1, bg=SURFACE, fg=TEXT, insertbackground=TEXT, font=("Segoe UI", 12), bd=0, show="•")
        self.entry_pwd.pack(padx=10, pady=8, fill="x")
        self.entry_pwd.focus()
        self.entry_pwd.bind("<Return>", lambda e: self._submit())
        
        if self.is_setup:
            tk.Label(self, text="Confirm Password", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=30, pady=(10, 0))
            f2 = tk.Frame(self, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
            f2.pack(padx=30, pady=(5, 5), fill="x")
            self.entry_confirm = tk.Entry(f2, bg=SURFACE, fg=TEXT, insertbackground=TEXT, font=("Segoe UI", 12), bd=0, show="•")
            self.entry_confirm.pack(padx=10, pady=8, fill="x")
            self.entry_confirm.bind("<Return>", lambda e: self._submit())
        
        self.error_lbl = tk.Label(self, text="", bg=BG, fg=MUTED, font=("Segoe UI", 9))
        self.error_lbl.pack(pady=5)
        
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=(10, 20))
        
        submit_btn = tk.Button(btn_frame, text="Submit", bg=BLUE, fg=TEXT, font=("Segoe UI", 10, "bold"), bd=0, command=self._submit, width=12)
        submit_btn.pack(side="left", padx=5)
        
        cancel_btn = tk.Button(btn_frame, text="Cancel", bg=SURFACE, fg=TEXT, font=("Segoe UI", 10), bd=0, command=self._cancel, width=12)
        cancel_btn.pack(side="left", padx=5)
        
    def _submit(self):
        pwd = self.entry_pwd.get()
        if self.is_setup:
            confirm = self.entry_confirm.get()
            is_valid, msg = validate_password_strength(pwd)
            if not is_valid:
                self._show_error(msg)
                return
            if pwd != confirm:
                self._show_error("Passwords do not match.")
                return
            
            salt = os.urandom(16)
            key = _hash_password(pwd, salt)
            _save_master_data(salt, key)
            self.result = True
            self.destroy()
        else:
            if verify_master_password(pwd):
                self.result = True
                self.destroy()
            else:
                self._show_error("Incorrect password.")
                self.entry_pwd.delete(0, 'end')

    def _show_error(self, msg):
        self.error_lbl.config(text=msg, fg=RED)
        
    def _cancel(self):
        self.result = False
        self.destroy()

def prompt_master_password_gui() -> bool:
    """Prompt for master password using a Tkinter dialog. Returns True if authorized."""
    root = tk.Tk()
    root.withdraw()
    dlg = MasterPasswordDialog(root)
    root.wait_window(dlg)
    res = dlg.result
    root.destroy()
    return res

def require_master_password(force_gui: bool = False) -> bool:
    """Smart router: uses CLI if attached to a terminal, otherwise GUI."""
    if force_gui:
        return prompt_master_password_gui()
    if sys.stdout and sys.stdout.isatty():
        return prompt_master_password_cli()
    else:
        return prompt_master_password_gui()

def change_master_password(old_pwd: str, new_pwd: str, confirm_pwd: str) -> tuple[bool, str]:
    """Verify old password, validate new one, and save the new hash."""
    if not verify_master_password(old_pwd):
        return False, "Incorrect old password."
    if old_pwd == new_pwd:
        return False, "This is your old password. Please write a different password."
    if new_pwd != confirm_pwd:
        return False, "New passwords do not match."
    
    is_valid, msg = validate_password_strength(new_pwd)
    if not is_valid:
        return False, msg
        
    salt = os.urandom(16)
    key = _hash_password(new_pwd, salt)
    _save_master_data(salt, key)
    return True, "Password changed successfully."
