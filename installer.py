"""
installer.py — One-click setup for SSH Buddy
Run once:  python installer.py
Sets up dependencies, autostart, shell hook, and starts the tray app.
"""

import sys
import os
import subprocess
import platform
import threading
import tkinter as tk
from pathlib import Path

# Ensure src is in sys.path
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.join(_SCRIPT_DIR, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

# ── Colour palette (Premium SaaS Dark Theme) ──────────────────────────────────
BG       = "#0A111E"
BG2      = "#060B14"
SURFACE  = "#111827"
SURFACE2 = "#161F32"
CARD     = "#111827"
BORDER   = "#1F2937"
MUTED    = "#CBD5E1"
TEXT     = "#F9FAFB"
BLUE     = "#3B82F6"
GREEN    = "#22C55E"
GREEN_H  = "#10B981"
RED      = "#EF4444"

FT_TITLE = ("Segoe UI", 16, "bold")
FT_TEXT  = ("Segoe UI", 11)
FT_BTN   = ("Segoe UI", 11, "bold")

class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, icon="", command=None, width=180, height=44, radius=8, btn_color=GREEN, fg_color="#0d1117", hover_color=GREEN_H, font=FT_BTN, **kwargs):
        super().__init__(parent, width=width, height=height, bg=parent["bg"], highlightthickness=0, **kwargs)
        self.command = command
        self.btn_color = btn_color
        self.hover_color = hover_color
        self.state = "normal"
        
        self.rect_id = self._create_rounded_rect(0, 0, width-1, height-1, radius, fill=btn_color)
        
        if icon:
            self.create_text(width/2 - 40, height/2, text=icon, fill=fg_color, font=("Segoe Fluent Icons", 13))
            self.create_text(width/2 + 10, height/2, text=text, fill=fg_color, font=font)
        else:
            self.create_text(width/2, height/2, text=text, fill=fg_color, font=font)
            
        for ev, handler in [("<Enter>", self.on_enter), ("<Leave>", self.on_leave), ("<ButtonRelease-1>", self.on_release)]:
            self.bind(ev, handler)
            
    def on_enter(self, e):
        if self.state == "normal":
            self.itemconfig(self.rect_id, fill=self.hover_color)
            self.config(cursor="hand2")
            
    def on_leave(self, e):
        if self.state == "normal":
            self.itemconfig(self.rect_id, fill=self.btn_color)
            self.config(cursor="")
            
    def on_release(self, e):
        if self.state == "normal" and self.command:
            self.command()
        return "break"

    def disable(self, disabled_bg=SURFACE2):
        self.state = "disabled"
        self.itemconfig(self.rect_id, fill=disabled_bg)
        self.config(cursor="")

    def _create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [x1+radius, y1, x2-radius, y1, x2, y1, x2, y1+radius, x2, y2-radius, x2, y2, x2-radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y1+radius, x1, y1]
        return self.create_polygon(points, **kwargs, smooth=True)

class InstallerApp:
    STEPS = [
        "Install Python dependencies",
        "Setup auto-start on boot",
        "Install SSH hook (wrapper alias)",
        "Start SSH Buddy tray app",
    ]

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("⚡ SSH Buddy — Setup")
        self.root.geometry("560x520")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        self._step_labels = []
        self._build_ui()

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self.root, bg=BG)
        hdr.pack(fill="x", pady=(32, 16))
        tk.Label(hdr, text="⚡ SSH Buddy — Setup", bg=BG, fg=BLUE, font=FT_TITLE).pack()
        tk.Label(hdr, text="One-click installer — sets up everything for you", bg=BG, fg=MUTED, font=FT_TEXT).pack(pady=(4,0))

        # Checklist frame
        self._checklist = tk.Frame(self.root, bg=BG)
        self._checklist.pack(fill="x", padx=60, pady=20)

        for i, step_text in enumerate(self.STEPS):
            f = tk.Frame(self._checklist, bg=BG)
            f.pack(fill="x", pady=6)
            icon = tk.Label(f, text="\uEA71", bg=BG, fg=MUTED, font=("Segoe Fluent Icons", 14))
            icon.pack(side="left", padx=(0, 10))
            lbl = tk.Label(f, text=step_text, bg=BG, fg=MUTED, font=FT_TEXT)
            lbl.pack(side="left")
            self._step_labels.append((icon, lbl))

        # Status
        self._status_var = tk.StringVar(value="")
        self._status_lbl = tk.Label(
            self.root, textvariable=self._status_var,
            bg=BG, fg=BLUE, font=FT_TEXT,
            anchor="center"
        )
        self._status_lbl.pack(fill="x", pady=(10, 20))

        # Buttons
        self._btn_frame = tk.Frame(self.root, bg=BG)
        self._btn_frame.pack(pady=10)

        self._install_btn = RoundedButton(
            self._btn_frame, text="Install", icon="\uE946", 
            command=self._start_install, width=180, btn_color="#0E9F6E", fg_color=TEXT
        )
        self._install_btn.pack(side="left", padx=10)

        self._close_btn = RoundedButton(
            self._btn_frame, text="Close", 
            command=self.root.destroy, width=120, btn_color=SURFACE2, fg_color=TEXT, hover_color=BORDER
        )
        self._close_btn.pack(side="left", padx=10)

    def _mark_step(self, idx, status):
        icon, lbl = self._step_labels[idx]
        if status == "running":
            icon.config(text="\uE896", fg=BLUE)
            lbl.config(fg=TEXT)
        elif status == "done":
            icon.config(text="\uE73E", fg=GREEN)
            lbl.config(fg=GREEN)
        elif status == "error":
            icon.config(text="\uEA39", fg=RED)
            lbl.config(fg=RED)

    def _set_status(self, text, color=BLUE):
        self._status_var.set(text)
        self._status_lbl.configure(fg=color)

    def _start_install(self):
        self._install_btn.disable()
        threading.Thread(target=self._run_install, daemon=True).start()

    def _run_install(self):
        try:
            self._step_1_deps()
            self._step_2_autostart()
            self._step_3_ssh_hook()
            self._step_4_start_tray()
            self.root.after(0, self._show_done)
        except Exception as exc:
            self.root.after(0, lambda: self._set_status(f"Error: {exc}", RED))

    def _step_1_deps(self):
        self.root.after(0, lambda: self._mark_step(0, "running"))
        self.root.after(0, lambda: self._set_status("Installing dependencies..."))
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pystray", "Pillow", "keyring", "keyrings.alt"], check=True)
            self.root.after(0, lambda: self._mark_step(0, "done"))
        except Exception:
            self.root.after(0, lambda: self._mark_step(0, "error"))

    def _step_2_autostart(self):
        self.root.after(0, lambda: self._mark_step(1, "running"))
        self.root.after(0, lambda: self._set_status("Setting up autostart..."))
        try:
            from ssh_buddy.autostart import enable_autostart
            enable_autostart()
            self.root.after(0, lambda: self._mark_step(1, "done"))
        except Exception:
            self.root.after(0, lambda: self._mark_step(1, "error"))

    def _step_3_ssh_hook(self):
        self.root.after(0, lambda: self._mark_step(2, "running"))
        self.root.after(0, lambda: self._set_status("Installing SSH hook..."))
        try:
            from ssh_buddy.shell_setup import setup as shell_hook_setup
            shell_hook_setup()
            self.root.after(0, lambda: self._mark_step(2, "done"))
        except Exception:
            self.root.after(0, lambda: self._mark_step(2, "error"))

    def _step_4_start_tray(self):
        self.root.after(0, lambda: self._mark_step(3, "running"))
        self.root.after(0, lambda: self._set_status("Starting tray app..."))
        try:
            tray_script = str(Path(_SRC_DIR) / "ssh_buddy" / "tray.py")
            system = platform.system()
            if system == "Windows":
                pythonw = Path(sys.executable).parent / "pythonw.exe"
                exe = str(pythonw) if pythonw.exists() else sys.executable
                subprocess.Popen([exe, tray_script], creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen([sys.executable, tray_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            self.root.after(0, lambda: self._mark_step(3, "done"))
        except Exception:
            self.root.after(0, lambda: self._mark_step(3, "error"))

    def _show_done(self):
        self._set_status("")
        self._status_lbl.pack_forget()

        done_text = (
            "SSH Buddy is installed and running!\n\n"
            "• Tray icon is in your taskbar / system tray\n"
            "• Every time you SSH to a new server → save dialog appears\n"
            "• Open GUI anytime from anywhere with: sshbuddy\n\n"
            "⚠️ IMPORTANT: Please CLOSE THIS TERMINAL and open a new one to start!"
        )
        done_lbl = tk.Label(self.root, text=done_text, bg=BG, fg=TEXT, font=("Segoe UI", 10), justify="left")
        done_lbl.pack(fill="x", padx=60, pady=(10, 0))

        for w in self._btn_frame.winfo_children():
            w.destroy()

        self._open_btn = RoundedButton(
            self._btn_frame, text="Open SSH Buddy", 
            command=self._open_gui, width=200, btn_color=BLUE, fg_color=TEXT, hover_color="#2563EB"
        )
        self._open_btn.pack(side="left", padx=10)

        self._close_btn2 = RoundedButton(
            self._btn_frame, text="Close", 
            command=self.root.destroy, width=120, btn_color=SURFACE2, fg_color=TEXT, hover_color=BORDER
        )
        self._close_btn2.pack(side="left", padx=10)

    def _open_gui(self):
        # FIX: Launch gui as a separate process using subprocess, instead of background thread
        script_path = str(Path(_SCRIPT_DIR) / "ssh_buddy.py")
        subprocess.Popen([sys.executable, script_path, "gui"], creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.root.destroy()

def run_installer():
    app = InstallerApp()
    app.root.mainloop()

if __name__ == "__main__":
    run_installer()
