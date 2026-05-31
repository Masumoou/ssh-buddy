"""
wrapper.py — SSH interceptor / wrapper for SSH Buddy
Intercepts `ssh user@host` commands, checks the local DB,
optionally saves new servers, and connects via connector.py.

Usage:
    python wrapper.py user@host
    python wrapper.py -p 2222 user@host
    python wrapper.py user@host -p 2222
"""

import sys
import re
import os

# Ensure the 'src' directory is on sys.path so package imports work
# regardless of where the user invokes the wrapper from.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.dirname(_SCRIPT_DIR)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from ssh_buddy.db import init_db, get_all_servers, add_server, update_server
from ssh_buddy.keystore import save_password, get_password
from ssh_buddy.connector import connect_ssh

# ── Colour palette — 2026 Premium SaaS Dark Theme ────────────────────────────
BG       = "#0A111E"       # Deep dark background (Window)
BG2      = "#060B14"       # Darker input field background
SURFACE  = "#111827"       # Card container background
SURFACE2 = "#161F32"       # Left icon box background
CARD     = "#111827"       # Card container background
BORDER   = "#1F2937"       # Subtle borders
MUTED    = "#CBD5E1"       # Brighter slate gray for much better readability
TEXT     = "#F9FAFB"       # Primary text — bright white
BLUE     = "#3B82F6"       # Electric Blue — focus glow & accents
GREEN    = "#22C55E"       # Neon Green — primary action & radar
GREEN_H  = "#10B981"       # Green hover
RED      = "#EF4444"       # Error / danger
YELLOW   = "#F59E0B"       # Warning / badge accent
MAUVE    = "#8B5CF6"       # Purple accent
TEAL     = "#14B8A6"       # Teal accent

# ── Fonts ───────────────────────────────────────────────────────────────────
_FONT_FAMILY = "Segoe UI"
_FONT_TEXT   = "Segoe UI"
FT_TITLE  = (_FONT_FAMILY, 16, "bold")    # Dialog title
FT_SUB    = (_FONT_FAMILY, 13, "bold")    # Subtitle (user@host)
FT_LABEL  = (_FONT_TEXT, 10, "bold")      # Form labels — clear & readable
FT_INPUT  = (_FONT_FAMILY, 11)            # Input text
FT_MONO   = ("Consolas", 12, "bold")      # Monospace (IP, port) - high contrast
FT_BTN    = (_FONT_FAMILY, 11, "bold")    # Button text
FT_SMALL  = (_FONT_TEXT, 11)              # Small hints & checkbox


# ── Argument parsing ───────────────────────────────────────────────────────────

def parse_ssh_args(argv: list[str]) -> dict | None:
    """
    Parse ssh-style arguments and return {ip, username, port}.
    Supports:
        wrapper.py user@host
        wrapper.py -p 22 user@host
        wrapper.py user@host -p 2222
    Returns None on failure.
    """
    args = argv[1:]  # skip script name
    port = 22
    target = None

    i = 0
    while i < len(args):
        if args[i] == "-p" and i + 1 < len(args):
            try:
                port = int(args[i + 1])
            except ValueError:
                pass
            i += 2
            continue
        # Skip other dash-flags (forward compatibility)
        if args[i].startswith("-"):
            i += 1
            continue
        # Must be user@host
        target = args[i]
        i += 1

    if not target:
        return None

    m = re.match(r"^([^@]+)@(.+)$", target)
    if not m:
        return None

    return {"username": m.group(1), "ip": m.group(2), "port": port}


# ── DB lookup ──────────────────────────────────────────────────────────────────

def find_server_by_ip_user(ip: str, username: str) -> dict | None:
    """Return the first server whose ip AND username match, or None."""
    for srv in get_all_servers():
        if srv["ip"] == ip and srv["username"] == username:
            return srv
    return None


# ── Tkinter Modern UI Helpers ───────────────────────────────────────────────────

import tkinter as tk
from tkinter import messagebox

class RoundedCard(tk.Canvas):
    def __init__(self, parent, radius=12, bg_color=CARD, parent_bg=BG, left_glow=False, **kwargs):
        super().__init__(parent, bg=parent_bg, highlightthickness=0, **kwargs)
        self.radius = radius
        self.bg_color = bg_color
        self.left_glow = left_glow
        self.rect_id = None
        self.glow_id = None
        self.inner = tk.Frame(self, bg=bg_color)
        self.win_id = self.create_window(radius, radius, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_inner_config)
        
    def _on_inner_config(self, event):
        w = event.width + 2 * self.radius
        h = event.height + 2 * self.radius
        self.config(width=w, height=h)
        if self.rect_id: self.delete(self.rect_id)
        if hasattr(self, 'highlight_id') and self.highlight_id: self.delete(self.highlight_id)
        if self.glow_id: self.delete(self.glow_id)
        
        # Outer dark shadow border and inner highlight (Glassmorphism Bevel)
        self.rect_id = self._create_rounded_rect(0, 0, w-1, h-1, self.radius, fill=self.bg_color, outline="#05080E", width=1)
        self.highlight_id = self._create_rounded_rect(1, 1, w-2, h-2, max(1, self.radius-1), fill="", outline="#1F2937", width=1)
        
        if self.left_glow:
            self.glow_id = self._create_rounded_rect(0, 16, 4, h-16, 2, fill=BLUE, outline="")
            self.tag_lower(self.glow_id)
            
        self.tag_lower(self.highlight_id)
        self.tag_lower(self.rect_id)

    def _create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [x1+radius, y1, x2-radius, y1, x2, y1, x2, y1+radius, x2, y2-radius, x2, y2, x2-radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y1+radius, x1, y1]
        return self.create_polygon(points, **kwargs, smooth=True)

class RoundedIconEntry(tk.Canvas):
    def __init__(self, parent, icon="\uE77B", textvariable=None, show="", width=400, height=38, radius=6, bg_color=BG2, fg_color=TEXT, font=FT_INPUT, placeholder="", **kwargs):
        super().__init__(parent, width=width, height=height, bg=parent["bg"], highlightthickness=0, **kwargs)
        
        # Overall bounding box
        self.rect_id = self._create_rounded_rect(1, 1, width-2, height-2, radius, fill=bg_color, outline=BORDER, width=1)
        
        # Left Icon box
        icon_w = 38
        self._create_rounded_rect(1, 1, icon_w, height-2, radius, fill=SURFACE2)
        self.create_text(icon_w/2 + 1, height/2, text=icon, fill=MUTED, font=("Segoe Fluent Icons", 12))
        
        kwargs_entry = {"show": show, "bg": bg_color, "fg": fg_color, "font": font, "relief": "flat", "insertbackground": BLUE, "highlightthickness": 0}
        if textvariable is not None:
            kwargs_entry["textvariable"] = textvariable
        self.entry = tk.Entry(self, **kwargs_entry)
        
        self.placeholder = placeholder
        self.fg_color = fg_color
        self.textvariable = textvariable
        self.show = show
        
        if self.placeholder and self.textvariable and not self.textvariable.get():
            self.entry.insert(0, self.placeholder)
            self.entry.config(fg=MUTED)
            if self.show: self.entry.config(show="")

        def on_focus_in(e):
            self.itemconfig(self.rect_id, outline=BLUE, width=1)
            if self.placeholder and self.entry.get() == self.placeholder:
                self.entry.delete(0, tk.END)
                self.entry.config(fg=self.fg_color)
                if self.show: self.entry.config(show=self.show)

        def on_focus_out(e):
            self.itemconfig(self.rect_id, outline=BORDER, width=1)
            if self.placeholder and not self.entry.get():
                self.entry.insert(0, self.placeholder)
                self.entry.config(fg=MUTED)
                if self.show: self.entry.config(show="")
                
        self.entry.bind("<FocusIn>", on_focus_in)
        self.entry.bind("<FocusOut>", on_focus_out)
        
        self.bind("<Button-1>", lambda e: self.entry.focus_set())
        
        # Create eye icon for password if needed
        self.eye_id = None
        self.is_password = bool(show)
        entry_end = width - 12
        if self.is_password:
            self.eye_id = self.create_text(width - 20, height/2, text="\uE890", fill=MUTED, font=("Segoe Fluent Icons", 12))
            self.tag_bind(self.eye_id, "<Button-1>", self._toggle_visibility)
            self.tag_bind(self.eye_id, "<Enter>", lambda e: self.config(cursor="hand2"))
            self.tag_bind(self.eye_id, "<Leave>", lambda e: self.config(cursor=""))
            entry_end -= 24
            
        self.create_window(icon_w + 12, height/2, window=self.entry, width=entry_end - icon_w - 12, anchor="w")
        
    def _toggle_visibility(self, e):
        current_show = self.entry.cget("show")
        if self.eye_id is not None:
            if current_show:
                self.entry.config(show="")
                self.itemconfig(self.eye_id, text="\uED1A") # Eye with strike
            else:
                self.entry.config(show="●")
                self.itemconfig(self.eye_id, text="\uE890") # Eye
            
    def _create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [x1+radius, y1, x2-radius, y1, x2, y1, x2, y1+radius, x2, y2-radius, x2, y2, x2-radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y1+radius, x1, y1]
        return self.create_polygon(points, **kwargs, smooth=True)
        
    def focus_set(self):
        self.entry.focus_set()
        self.entry.icursor(tk.END)
        self.entry.xview_moveto(1)

class RoundedBadge(tk.Canvas):
    def __init__(self, parent, text, icon="\uE945", width=220, height=36, radius=18, bg_color=BG2, fg_color=GREEN, border_color=GREEN, font=FT_BTN, **kwargs):
        super().__init__(parent, width=width, height=height, bg=parent["bg"], highlightthickness=0, **kwargs)
        self._create_rounded_rect(1, 1, width-1, height-1, radius, fill=bg_color, outline=border_color, width=1)
        # Inner circle for icon
        self.create_oval(10, 8, 30, 28, fill="#132A1F", outline="")
        self.create_text(20, 18, text=icon, fill=fg_color, font=("Segoe Fluent Icons", 11))
        self.create_text(width/2 + 10, height/2, text=text, fill=fg_color, font=font, justify="center")

    def _create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [x1+radius, y1, x2-radius, y1, x2, y1, x2, y1+radius, x2, y2-radius, x2, y2, x2-radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y1+radius, x1, y1]
        return self.create_polygon(points, **kwargs, smooth=True)

class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, icon="", command=None, width=160, height=44, radius=8, btn_color=GREEN, fg_color="#0d1117", hover_color=GREEN_H, font=FT_BTN, outline_color="", outline_width=0, **kwargs):
        super().__init__(parent, width=width, height=height, bg=parent["bg"], highlightthickness=0, **kwargs)
        self.command = command
        self.btn_color = btn_color
        self.hover_color = hover_color
        
        kwargs_rect = {
            "fill": btn_color,
            "outline": outline_color if outline_color else "#05080E",
            "width": outline_width if outline_width else 1
        }
            
        # Outer dark shadow border
        self.rect_id = self._create_rounded_rect(0, 0, width-1, height-1, radius, **kwargs_rect)
        # Inner highlight (Bevel)
        hl_color = "#34D399" if btn_color == "#0E9F6E" else "#1F2937"
        self.highlight_id = self._create_rounded_rect(1, 1, width-2, height-2, max(1, radius-1), fill="", outline=hl_color, width=1)
        
        if icon and text:
            self.icon_id = self.create_text(width/2 - 44, height/2, text=icon, fill=fg_color, font=("Segoe Fluent Icons", 13))
            self.text_id = self.create_text(width/2 + 12, height/2, text=text, fill=fg_color, font=font)
        elif icon:
            self.icon_id = self.create_text(width/2, height/2, text=icon, fill=fg_color, font=("Segoe Fluent Icons", 14))
        else:
            self.text_id = self.create_text(width/2, height/2, text=text, fill=fg_color, font=font)
        
        for ev, handler in [("<Enter>", self.on_enter), ("<Leave>", self.on_leave), 
                            ("<Button-1>", self.on_press), ("<ButtonRelease-1>", self.on_release)]:
            self.bind(ev, handler)
            
    def on_enter(self, e): self.itemconfig(self.rect_id, fill=self.hover_color); self.config(cursor="hand2")
    def on_leave(self, e): self.itemconfig(self.rect_id, fill=self.btn_color); self.config(cursor="")
    def on_press(self, e): self.itemconfig(self.rect_id, fill=self.btn_color)
    def on_release(self, e): 
        self.itemconfig(self.rect_id, fill=self.hover_color)
        import time
        now = time.time()
        if hasattr(self, '_last_click') and now - self._last_click < 0.5:
            return "break"
        self._last_click = now
        if self.command: self.command()
        return "break"

    def _create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [x1+radius, y1, x2-radius, y1, x2, y1, x2, y1+radius, x2, y2-radius, x2, y2, x2-radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y1+radius, x1, y1]
        return self.create_polygon(points, **kwargs, smooth=True)

# ── Tkinter dialogs ───────────────────────────────────────────────────────────

def _show_new_server_dialog(ip: str, username: str, port: int) -> dict | None:
    result = {}

    root = tk.Tk()
    root.title("SSH Buddy - New Server")
    root.configure(bg=BG)
    root.resizable(False, False)
    root.minsize(600, 10)  # Wider for the new layout

    # DPI awareness on Windows
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    # ── Header section (Premium Detection Banner) ──
    hdr_frame = tk.Frame(root, bg=BG)
    hdr_frame.pack(fill="x", padx=16, pady=(12, 8))
    
    hdr = tk.Canvas(hdr_frame, height=100, bg=CARD, highlightthickness=0)
    hdr.pack(fill="x")
    
    # Draw radar rings and text on the banner
    def _draw_radar(w, h):
        hdr.delete("all")
        # Base glassmorphism card background
        hdr.create_polygon([0,0, w-1,0, w-1,h-1, 0,h-1], fill=CARD, outline="#05080E", width=1, smooth=True)
        hdr.create_polygon([1,1, w-2,1, w-2,h-2, 1,h-2], fill="", outline="#1F2937", width=1, smooth=True)
        
        cx, cy = w/2, h/2
        
        # Ambient Background Glow
        hdr.create_oval(cx-300, cy-150, cx+300, cy+150, fill="#081A12", outline="")
        
        # Radar circles
        hdr.create_oval(cx-150, cy-150, cx+150, cy+150, outline="#0A2216", width=1)
        hdr.create_oval(cx-250, cy-250, cx+250, cy+250, outline="#071810", width=1)
        # Small dots
        hdr.create_oval(cx+148, cy-2, cx+152, cy+2, fill=GREEN, outline="")
        hdr.create_oval(cx-252, cy-2, cx-248, cy+2, fill="#082A1B", outline="")
        
        # Bolder Server Address drawn directly on canvas for clean background
        hdr.create_text(cx, h * 0.75, text=f"{username}@{ip}:{port}", fill=TEXT, font=FT_SUB)
    
    hdr.bind("<Configure>", lambda e: _draw_radar(e.width, e.height))
    
    # Modern Pill Badge for title inside the Canvas
    badge_f = tk.Frame(hdr, bg="#081A12")
    badge_f.place(relx=0.5, rely=0.35, anchor="center")
    RoundedBadge(badge_f, text="New Server Detected", icon="\uE945", width=220, height=32, radius=16, bg_color="#061510", fg_color=GREEN, border_color="#103F25", font=FT_BTN).pack()

    # ── Scrollable form area ──
    form_outer = tk.Frame(root, bg=BG)
    form_outer.pack(fill="both", expand=True, padx=16, pady=(8, 0))

    # Server info section (read-only)
    info_card = RoundedCard(form_outer, radius=8, bg_color=CARD, parent_bg=BG, left_glow=True)
    info_card.pack(fill="x", pady=(0, 16))
    
    info_title = tk.Frame(info_card.inner, bg=CARD)
    info_title.pack(fill="x", padx=24, pady=(20, 8))
    tk.Label(info_title, text="\uE7F4", bg=CARD, fg=MUTED, font=("Segoe Fluent Icons", 14)).pack(side="left")
    tk.Label(info_title, text="SERVER DETAILS", bg=CARD, fg=MUTED, font=FT_LABEL).pack(side="left", padx=(10,0))

    # 3-column layout using grid for strict spacing
    col_frame = tk.Frame(info_card.inner, bg=CARD)
    col_frame.pack(fill="x", padx=24, pady=(8, 20))
    col_frame.columnconfigure(0, weight=4)
    col_frame.columnconfigure(1, weight=3)
    col_frame.columnconfigure(2, weight=2)
    
    cols = [
        ("\uE7F4", "IP Address", ip),
        ("\uE77B", "Username", username),
        ("\uE17D", "Port", str(port))
    ]
    
    for i, (icon, lbl, val) in enumerate(cols):
        subf = tk.Frame(col_frame, bg=CARD)
        # Add strong explicit horizontal spacing between columns
        subf.grid(row=0, column=i, sticky="w", padx=(0, 32) if i < 2 else 0)
        
        # Icon box
        icon_lbl = tk.Label(subf, text=icon, bg=SURFACE2, fg=BLUE, font=("Segoe Fluent Icons", 12))
        icon_lbl.pack(side="left", ipadx=10, ipady=10)
        
        # Text
        textf = tk.Frame(subf, bg=CARD)
        textf.pack(side="left", padx=(16, 0))  # Force gap between icon and text
        tk.Label(textf, text=lbl, bg=CARD, fg=MUTED, font=FT_SMALL).pack(anchor="w", pady=(0, 2))
        tk.Label(textf, text=val, bg=CARD, fg=TEXT, font=FT_MONO).pack(anchor="w")

    # Editable fields section
    edit_card = RoundedCard(form_outer, radius=8, bg_color=CARD, parent_bg=BG, left_glow=True)
    edit_card.pack(fill="x", pady=(0, 16))

    edit_title = tk.Frame(edit_card.inner, bg=CARD)
    edit_title.pack(fill="x", padx=24, pady=(20, 8))
    tk.Label(edit_title, text="\uE8A4", bg=CARD, fg=BLUE, font=("Segoe Fluent Icons", 14)).pack(side="left")
    tk.Label(edit_title, text="SAVE DETAILS", bg=CARD, fg=MUTED, font=FT_LABEL).pack(side="left", padx=(10,0))

    editable_fields = [
        ("alias", "Alias * (required)",            f"{username}@{ip}",  "",                 "\uE77B"),
        ("tags",  "Tags (comma-separated)", "",  "e.g. prod, web",   "\uE8EC"),
        ("notes", "Notes",                  "",  "Optional notes...", "\uE8A5"),
    ]
    
    vars_ = {}
    entries_ = {}
    first_entry = None
    
    for key, lbl, default, placeholder, icon in editable_fields:
        f = tk.Frame(edit_card.inner, bg=CARD)
        f.pack(fill="x", padx=16, pady=(12, 4))
        # Label offset to match the input field start (after the 44px icon box + 12px gap = 56px)
        lbl_f = tk.Frame(f, bg=CARD)
        lbl_f.pack(fill="x", padx=(56, 0), pady=(0, 4))
        tk.Label(lbl_f, text=lbl, bg=CARD, fg=MUTED, font=FT_LABEL, anchor="w").pack(side="left")
        
        var = tk.StringVar(value=default)
        e = RoundedIconEntry(f, icon=icon, textvariable=var, width=540, height=44, radius=8, bg_color=BG2, fg_color=TEXT, font=FT_INPUT, placeholder=placeholder)
        e.pack(fill="x")
        vars_[key] = var
        entries_[key] = e
        if first_entry is None:
            first_entry = e

    # Password field
    pf = tk.Frame(edit_card.inner, bg=CARD)
    pf.pack(fill="x", padx=16, pady=(12, 24))
    lbl_f = tk.Frame(pf, bg=CARD)
    lbl_f.pack(fill="x", padx=(56, 0), pady=(0, 4))
    tk.Label(lbl_f, text="Password (optional, saved securely)", bg=CARD, fg=MUTED, font=FT_LABEL, anchor="w").pack(side="left")
    
    pw_var = tk.StringVar()
    RoundedIconEntry(pf, icon="\uE72E", textvariable=pw_var, show="●", width=540, height=44, radius=8, bg_color=BG2, fg_color=TEXT, font=FT_INPUT, placeholder="Leave empty if not required").pack(fill="x")
    
    use_key_var = tk.BooleanVar(value=False)
    
    cb_f = tk.Frame(edit_card.inner, bg=CARD, cursor="hand2")
    cb_f.pack(padx=24, pady=(0, 20), anchor="w")
    
    cb_icon = tk.Label(cb_f, text="\uE739", bg=CARD, fg=MUTED, font=("Segoe Fluent Icons", 14))
    cb_icon.pack(side="left")
    
    cb_text = tk.Label(cb_f, text="  Try key auth (I have my SSH key on this server)", bg=CARD, fg=TEXT, font=FT_SMALL)
    cb_text.pack(side="left")
    
    def _toggle_cb(*_):
        val = not use_key_var.get()
        use_key_var.set(val)
        
    cb_icon.bind("<Button-1>", _toggle_cb)
    cb_text.bind("<Button-1>", _toggle_cb)
    
    use_key_var.trace_add("write", lambda *_: cb_icon.config(text="\uE73A" if use_key_var.get() else "\uE739", fg=GREEN if use_key_var.get() else MUTED))
    
    key_status_lbl = tk.Label(edit_card.inner, text="", bg=CARD, fg=GREEN, font=FT_SMALL)
    key_status_lbl.pack(padx=24, pady=(0, 20), anchor="w")
    
    def _check_bg():
        from ssh_buddy.connector import check_key_auth
        if check_key_auth(ip, username, port):
            root.after(0, lambda: use_key_var.set(True))
            root.after(0, lambda: key_status_lbl.config(text="✅ SSH key detected on this server"))
            
    import threading
    threading.Thread(target=_check_bg, daemon=True).start()

    if first_entry:
        first_entry.focus_set()

    # ── Bottom Buttons ──
    def _save_and_connect():
        alias = vars_["alias"].get().strip()
        if not alias:
            alias_entry = entries_["alias"]
            alias_entry.itemconfig(alias_entry.rect_id, outline=RED, width=2)
            alias_entry.entry.focus_set()
            return
        result["action"]   = "save"
        result["alias"]    = alias
        tags_val = vars_["tags"].get().strip()
        result["tags"]     = "" if tags_val == "e.g. prod, web" else tags_val
        notes_val = vars_["notes"].get().strip()
        result["notes"]    = "" if notes_val == "Optional notes..." else notes_val
        
        pw_val = pw_var.get()
        result["password"] = None if pw_val == "Leave empty if not required" or not pw_val else pw_val
        result["use_key"]  = 1 if use_key_var.get() else 0
        root.quit()

    def _just_connect():
        result["action"]   = "connect"
        pw_val = pw_var.get()
        result["password"] = None if pw_val == "Leave empty if not required" or not pw_val else pw_val
        result["use_key"]  = 1 if use_key_var.get() else 0
        root.quit()

    bf = tk.Frame(root, bg=BG)
    bf.pack(fill="x", padx=16, pady=(8, 24))

    save_btn = RoundedButton(bf, text="Save & Connect", icon="\uE74E", command=_save_and_connect,
                             width=260, height=48, radius=8,
                             btn_color="#0E9F6E", fg_color=TEXT, hover_color=GREEN, font=FT_BTN)
    save_btn.pack(side="left", expand=True)

    just_btn = RoundedButton(bf, text="Just Connect", icon="\uE945", command=_just_connect,
                             width=260, height=48, radius=8,
                             btn_color=CARD, fg_color=TEXT, hover_color=SURFACE2, font=FT_BTN, outline_color=BORDER, outline_width=1)
    just_btn.pack(side="right", expand=True)

    root.protocol("WM_DELETE_WINDOW", root.quit)
    root.mainloop()
    root.destroy()
    return result if result else None


def _show_password_dialog(server: dict) -> dict | None:
    """
    Professional password prompt dialog with 'Remember?' checkbox.
    Returns {password, save} or None if cancelled.
    """
    import tkinter as tk

    result = {}

    root = tk.Tk()
    root.title("SSH Buddy — Password Required")
    root.configure(bg=BG)
    root.resizable(False, False)

    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    # ── Header ──
    hdr = tk.Frame(root, bg=BG2)
    hdr.pack(fill="x", ipady=4)
    tk.Label(hdr, text=f"⚡  {server['alias']}",
             bg=BG2, fg=BLUE, font=FT_TITLE).pack(pady=(8, 2))
    tk.Label(hdr, text=f"{server['username']}@{server['ip']}:{server['port']}",
             bg=BG2, fg=MUTED, font=FT_SUB).pack(pady=(0, 4))

    tk.Frame(root, bg=BORDER, height=1).pack(fill="x")

    # ── Password card ──
    card = RoundedCard(root, radius=8, bg_color=CARD, parent_bg=BG, left_glow=True)
    card.pack(fill="x", padx=16, pady=24)

    pf = tk.Frame(card.inner, bg=CARD)
    pf.pack(fill="x", padx=16, pady=(16, 8))
    
    # Label offset to match the input field start (after the 44px icon box + 12px gap = 56px)
    lbl_f = tk.Frame(pf, bg=CARD)
    lbl_f.pack(fill="x", padx=(56, 0), pady=(0, 4))
    tk.Label(lbl_f, text="Password", bg=CARD, fg=MUTED, font=FT_LABEL, anchor="w").pack(side="left")
    
    pw_var = tk.StringVar()
    pw_entry = RoundedIconEntry(pf, icon="\uE72E", textvariable=pw_var, show="●", width=420, height=44, radius=8, bg_color=BG2, fg_color=TEXT, font=FT_INPUT)
    pw_entry.pack(fill="x")
    pw_entry.focus_set()

    save_var = tk.BooleanVar(value=True)
    tk.Checkbutton(card.inner, text="  Remember this password",
                   variable=save_var,
                   bg=CARD, fg=TEXT, selectcolor=SURFACE,
                   activebackground=CARD, activeforeground=TEXT,
                   font=FT_SMALL,
                   highlightthickness=0).pack(padx=20, pady=(0, 16), anchor="w")

    # ── Buttons ──
    def _ok(event=None):
        result["password"] = pw_var.get() or None
        result["save"]     = save_var.get()
        root.quit()

    pw_entry.entry.bind("<Return>", _ok)

    bf = tk.Frame(root, bg=BG)
    bf.pack(fill="x", padx=16, pady=(8, 24))
    def _try_key(event=None):
        from ssh_buddy.connector import check_key_auth
        root.config(cursor="wait")
        root.update()
        if check_key_auth(server["ip"], server["username"], server["port"]):
            result["force_key"] = True
            root.quit()
        else:
            root.config(cursor="")
            messagebox.showerror("Key Not Found", "Your SSH key was not found on this server. Please enter the password to connect.", parent=root)
        
    ok_btn = RoundedButton(bf, text="Connect", icon="\uE945", command=_ok,
                           width=140, height=48, radius=8,
                           btn_color="#0E9F6E", fg_color=TEXT, hover_color=GREEN, font=FT_BTN)
    ok_btn.pack(side="left", padx=(0, 4), expand=True)
    
    key_btn = RoundedButton(bf, text="Try Key Auth", icon="\uE8D7", command=_try_key,
                            width=160, height=48, radius=8, btn_color=SURFACE2, fg_color=BLUE, hover_color=CARD, font=FT_BTN, outline_color=BLUE, outline_width=1)
    key_btn.pack(side="left", padx=4, expand=True)
    
    cancel_btn = RoundedButton(bf, text="Cancel", command=root.quit,
                               width=110, height=48, radius=8,
                               btn_color=CARD, fg_color=TEXT, hover_color=SURFACE2, font=FT_BTN, outline_color=BORDER, outline_width=1)
    cancel_btn.pack(side="right", padx=(4, 0), expand=True)

    root.protocol("WM_DELETE_WINDOW", root.quit)
    root.mainloop()
    root.destroy()
    return result if result else None


# ── Main ───────────────────────────────────────────────────────────────────────

def _safe_print(text: str):
    """Print text, replacing chars the console can't encode (fixes Windows CP1252 issues)."""
    try:
        print(text)
    except UnicodeEncodeError:
        safe = text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
            sys.stdout.encoding or "utf-8", errors="replace"
        )
        print(safe)


def main():
    parsed = parse_ssh_args(sys.argv)
    if not parsed:
        _safe_print("Usage:  python wrapper.py [options] user@host")
        _safe_print("        python wrapper.py -p 2222 user@host")
        sys.exit(1)

    ip       = parsed["ip"]
    username = parsed["username"]
    port     = parsed["port"]

    init_db()
    server = find_server_by_ip_user(ip, username)

    if server is None:
        # ── New server ─────────────────────────────────────────────────────
        _safe_print(f"[*] SSH Buddy — new server: {username}@{ip}:{port}")
        dlg = _show_new_server_dialog(ip, username, port)

        if dlg and dlg.get("action") == "save":
            import socket
            try:
                with socket.create_connection((ip, port), timeout=3):
                    ok, msg = add_server(
                        dlg["alias"], ip, username, port,
                        dlg.get("tags", ""), dlg.get("notes", ""),
                        dlg.get("use_key", 0)
                    )
                    if ok:
                        _safe_print(f"[*] Server saved as '{dlg['alias']}'")
                        if dlg.get("password"):
                            save_password(dlg["alias"], dlg["password"])
                    else:
                        _safe_print(f"[*] Could not save: {msg}")
            except OSError:
                _safe_print(f"[*] Connection to {ip}:{port} failed. Server was not saved.")
            password = dlg.get("password")
            use_key = bool(dlg.get("use_key", 0))
        elif dlg and dlg.get("action") == "connect":
            password = dlg.get("password")
            use_key = bool(dlg.get("use_key", 0))
        else:
            # Dialog closed / cancelled
            _safe_print("Cancelled.")
            sys.exit(0)

        if use_key:
            from ssh_buddy.connector import check_key_auth
            import tkinter as tk
            from tkinter import messagebox
            
            _safe_print(f"[*] SSH Buddy — Verifying SSH key for {username}@{ip}...")
            if check_key_auth(ip, username, port):
                _safe_print("[*] SSH Buddy — SSH key verified, connecting...")
            else:
                _safe_print("[*] SSH Buddy — SSH key NOT found on server.")
                
                # Revert the database if we just saved it
                if dlg.get("action") == "save":
                    update_server(dlg["alias"], use_key=0)
                    
                # Show error message
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("Key Not Found", f"Your SSH key was not found on {ip}.\n\nPlease enter the password to connect.")
                root.destroy()
                
                # Show password dialog
                temp_server = {"alias": dlg.get("alias", ip), "username": username, "ip": ip, "port": port}
                pw_dlg = _show_password_dialog(temp_server)
                
                if pw_dlg is None:
                    _safe_print("Cancelled.")
                    sys.exit(0)
                    
                use_key = bool(pw_dlg.get("force_key"))
                if not use_key:
                    password = pw_dlg.get("password")
                    if pw_dlg.get("save") and password and dlg.get("action") == "save":
                        save_password(dlg["alias"], password)

        connect_ssh(ip, username, port, password, from_gui=False, try_key_first=use_key)

    else:
        # ── Known server ───────────────────────────────────────────────────
        alias    = server["alias"]
        from ssh_buddy.connector import check_key_auth
        
        if server.get("use_key", 0):
            # User wants key auth, verify it works
            key_works = check_key_auth(ip, username, port)
            if key_works:
                _safe_print(f"[*] SSH Buddy — {alias}: SSH key detected, connecting...")
                connect_ssh(ip, username, port, None, from_gui=False, try_key_first=True)
                return
            
            # Key auth failed. Correct DB and show error
            update_server(alias, use_key=0)
            _safe_print(f"[!] SSH Buddy — SSH key NOT found on {username}@{ip}.")
            _safe_print(f"[!] This server does not have your SSH key configured.")
            _safe_print(f"[!] Falling back to password authentication.")
            
            # Show GUI error if possible
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showwarning(
                    "SSH Key Not Found",
                    f"SSH key was not found on {username}@{ip}.\n\n"
                    f"This server does not have your SSH key configured.\n"
                    f"Falling back to password authentication."
                )
                root.destroy()
            except Exception:
                pass
            
        # 3. Only if both above fail -> ask for password
        password = get_password(alias)
        if password:
            _safe_print(f"[*] SSH Buddy — connecting to {alias} ({username}@{ip}:{port})")
            connect_ssh(ip, username, port, password, from_gui=False)
        else:
            _safe_print(f"[*] SSH Buddy — {alias}: no saved password")
            dlg = _show_password_dialog(server)
            if dlg is None:
                _safe_print("Cancelled.")
                sys.exit(0)
                
            if dlg.get("force_key"):
                _safe_print(f"[*] SSH Buddy — {alias}: Forcing SSH key auth")
                connect_ssh(ip, username, port, None, from_gui=False, try_key_first=True)
                return
                
            password = dlg.get("password")
            if dlg.get("save") and password:
                save_password(alias, password)
                _safe_print("[*] Password saved.")
            connect_ssh(ip, username, port, password, from_gui=False)


if __name__ == "__main__":
    main()
