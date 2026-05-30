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

# Ensure sibling imports work regardless of cwd
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

# ── Colour palette (Catppuccin Mocha — same as gui.py) ──────────────────────
BG       = "#1e1e2e"
BG2      = "#181825"
SURFACE  = "#313244"
SURFACE2 = "#45475a"
MUTED    = "#6c7086"
TEXT     = "#cdd6f4"
BLUE     = "#89b4fa"
GREEN    = "#a6e3a1"
RED      = "#f38ba8"
YELLOW   = "#f9e2af"
MAUVE    = "#cba6f7"
TEAL     = "#94e2d5"


# ── Installer GUI ──────────────────────────────────────────────────────────────

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

        # DPI awareness on Windows
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        self._step_labels: list[tk.Label] = []
        self._build_ui()

    # ── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        tk.Label(self.root, text="⚡ SSH Buddy — Setup",
                 bg=BG, fg=BLUE, font=("Consolas", 16, "bold")).pack(pady=(28, 4))
        tk.Label(self.root, text="One-click installer — sets up everything for you",
                 bg=BG, fg=MUTED, font=("Consolas", 10)).pack(pady=(0, 20))

        # Checklist frame
        self._checklist = tk.Frame(self.root, bg=BG)
        self._checklist.pack(fill="x", padx=50)

        for i, step_text in enumerate(self.STEPS):
            lbl = tk.Label(
                self._checklist,
                text=f"  ○  {step_text}",
                bg=BG, fg=MUTED,
                font=("Consolas", 11),
                anchor="w",
            )
            lbl.pack(fill="x", pady=4)
            self._step_labels.append(lbl)

        # Status message area
        self._status_var = tk.StringVar(value="")
        self._status_lbl = tk.Label(
            self.root, textvariable=self._status_var,
            bg=BG, fg=MUTED, font=("Consolas", 9),
            anchor="w", wraplength=460, justify="left",
        )
        self._status_lbl.pack(fill="x", padx=50, pady=(16, 0))

        # Button frame
        self._btn_frame = tk.Frame(self.root, bg=BG)
        self._btn_frame.pack(pady=24)

        self._install_btn = tk.Button(
            self._btn_frame, text="  ⚡ Install  ",
            command=self._start_install,
            bg=GREEN, fg=BG, relief="flat",
            font=("Consolas", 12, "bold"), padx=16, pady=6,
            cursor="hand2", activebackground=TEAL, activeforeground=BG,
        )
        self._install_btn.pack(side="left", padx=8)

        self._close_btn = tk.Button(
            self._btn_frame, text="  Close  ",
            command=self.root.destroy,
            bg=SURFACE, fg=TEXT, relief="flat",
            font=("Consolas", 11), padx=16, pady=6,
            cursor="hand2", activebackground=SURFACE2, activeforeground=TEXT,
        )
        self._close_btn.pack(side="left", padx=8)

    # ── Step rendering helpers ──────────────────────────────────────────────

    def _mark_step(self, index: int, status: str):
        """Update a checklist step. status: 'running' | 'done' | 'error'."""
        lbl = self._step_labels[index]
        text = self.STEPS[index]
        if status == "running":
            lbl.configure(text=f"  ⏳  {text} …", fg=YELLOW)
        elif status == "done":
            lbl.configure(text=f"  ✅  {text}", fg=GREEN)
        elif status == "error":
            lbl.configure(text=f"  ❌  {text}", fg=RED)

    def _set_status(self, msg: str, color: str = MUTED):
        self._status_var.set(msg)
        self._status_lbl.configure(fg=color)

    # ── Install logic (runs in background thread) ──────────────────────────

    def _start_install(self):
        self._install_btn.configure(state="disabled", bg=SURFACE2, fg=MUTED)
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

    # -- Step 1: pip install dependencies --------------------------------

    def _step_1_deps(self):
        self.root.after(0, lambda: self._mark_step(0, "running"))
        self.root.after(0, lambda: self._set_status("Installing pystray, Pillow, keyring …"))
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install",
                 "pystray", "Pillow", "keyring", "--quiet"],
                check=True,
                capture_output=True,
                timeout=120,
            )
            self.root.after(0, lambda: self._mark_step(0, "done"))
        except subprocess.CalledProcessError as e:
            self.root.after(0, lambda: self._mark_step(0, "error"))
            self.root.after(0, lambda: self._set_status(
                f"pip failed: {e.stderr.decode(errors='replace')[:200]}", RED))
            # continue anyway — deps might already be installed
        except FileNotFoundError:
            self.root.after(0, lambda: self._mark_step(0, "error"))
            self.root.after(0, lambda: self._set_status(
                "pip not found. Install packages manually: pip install pystray Pillow keyring", RED))

    # -- Step 2: autostart -----------------------------------------------

    def _step_2_autostart(self):
        self.root.after(0, lambda: self._mark_step(1, "running"))
        self.root.after(0, lambda: self._set_status("Registering auto-start on boot …"))
        try:
            from autostart import enable_autostart
            enable_autostart()
            self.root.after(0, lambda: self._mark_step(1, "done"))
        except Exception as exc:
            self.root.after(0, lambda: self._mark_step(1, "error"))
            self.root.after(0, lambda: self._set_status(f"Autostart error: {exc}", RED))

    # -- Step 3: SSH hook (wrapper alias) --------------------------------

    def _step_3_ssh_hook(self):
        self.root.after(0, lambda: self._mark_step(2, "running"))
        self.root.after(0, lambda: self._set_status("Installing SSH hook …"))
        try:
            from shell_setup import setup as shell_hook_setup
            msgs = shell_hook_setup()
            detail = "  |  ".join(m.strip() for m in msgs if m.strip())
            self.root.after(0, lambda: self._mark_step(2, "done"))
            self.root.after(0, lambda: self._set_status(detail))
        except Exception as exc:
            self.root.after(0, lambda: self._mark_step(2, "error"))
            self.root.after(0, lambda: self._set_status(f"SSH hook error: {exc}", RED))

    # -- Step 4: launch tray in background -------------------------------

    def _step_4_start_tray(self):
        self.root.after(0, lambda: self._mark_step(3, "running"))
        self.root.after(0, lambda: self._set_status("Starting tray app …"))
        try:
            tray_script = str(Path(_SCRIPT_DIR) / "tray.py")
            system = platform.system()

            if system == "Windows":
                # Use pythonw to avoid a console window
                pythonw = Path(sys.executable).parent / "pythonw.exe"
                exe = str(pythonw) if pythonw.exists() else sys.executable
                subprocess.Popen(
                    [exe, tray_script],
                    creationflags=subprocess.DETACHED_PROCESS
                    | subprocess.CREATE_NO_WINDOW,
                )
            else:
                # Linux: nohup + disown-style
                subprocess.Popen(
                    [sys.executable, tray_script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            self.root.after(0, lambda: self._mark_step(3, "done"))
        except Exception as exc:
            self.root.after(0, lambda: self._mark_step(3, "error"))
            self.root.after(0, lambda: self._set_status(f"Tray launch error: {exc}", RED))

    # ── Done screen ─────────────────────────────────────────────────────────

    def _show_done(self):
        self._set_status("")

        # Clear old status label
        self._status_lbl.pack_forget()

        # Completion message
        system = platform.system()
        if system == "Windows":
            reload_hint = "Windows: restart PowerShell"
        else:
            reload_hint = "Linux: run  source ~/.bashrc"

        done_text = (
            "SSH Buddy is installed and running!\n"
            "\n"
            "What happens now:\n"
            "  • Tray icon is in your taskbar / system tray\n"
            "  • Every time you SSH to a new server → save dialog appears\n"
            "  • Open GUI anytime from tray icon\n"
            "  • Starts automatically on every boot\n"
            "\n"
            f"To use SSH wrapper, reload your terminal:\n"
            f"  {reload_hint}"
        )
        done_lbl = tk.Label(
            self.root, text=done_text,
            bg=BG, fg=TEXT, font=("Consolas", 10),
            anchor="w", justify="left",
        )
        done_lbl.pack(fill="x", padx=50, pady=(10, 0))

        # Replace buttons
        for w in self._btn_frame.winfo_children():
            w.destroy()

        tk.Button(
            self._btn_frame, text="  ⚡ Open SSH Buddy Now  ",
            command=self._open_gui,
            bg=GREEN, fg=BG, relief="flat",
            font=("Consolas", 11, "bold"), padx=12, pady=5,
            cursor="hand2", activebackground=TEAL, activeforeground=BG,
        ).pack(side="left", padx=8)

        tk.Button(
            self._btn_frame, text="  Close  ",
            command=self.root.destroy,
            bg=SURFACE, fg=TEXT, relief="flat",
            font=("Consolas", 11), padx=16, pady=5,
            cursor="hand2", activebackground=SURFACE2, activeforeground=TEXT,
        ).pack(side="left", padx=8)

    def _open_gui(self):
        """Launch the main GUI and close the installer window."""
        def _run():
            from gui import run_gui
            run_gui()
        threading.Thread(target=_run, daemon=True).start()
        self.root.after(500, self.root.destroy)

    # ── Run ─────────────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


# ── Entry point ────────────────────────────────────────────────────────────────

def run_installer():
    app = InstallerApp()
    app.run()


if __name__ == "__main__":
    run_installer()
