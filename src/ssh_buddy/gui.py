import tkinter as tk
from tkinter import ttk, messagebox
import threading

from .db import init_db, get_all_servers, add_server, delete_server, search_servers, get_server, update_server
from .keystore import save_password, get_password, delete_password
from .connector import connect_ssh

# ── Colour palette — 2026 Premium SaaS Dark Theme ────────────────────────────
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
YELLOW   = "#F59E0B"

# ── Fonts ───────────────────────────────────────────────────────────────────
_FONT_FAMILY = "Segoe UI"
FT_TITLE  = (_FONT_FAMILY, 16, "bold")
FT_SUB    = (_FONT_FAMILY, 13, "bold")
FT_LABEL  = (_FONT_FAMILY, 10, "bold")
FT_INPUT  = (_FONT_FAMILY, 11)
FT_MONO   = ("Consolas", 12, "bold")
FT_BTN    = (_FONT_FAMILY, 11, "bold")
FT_SMALL  = (_FONT_FAMILY, 11)

# ── Custom Tkinter Components ───────────────────────────────────────────────

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
        self.rect_id = self._create_rounded_rect(1, 1, width-2, height-2, radius, fill=bg_color, outline=BORDER, width=1)
        icon_w = 38
        self._create_rounded_rect(1, 1, icon_w, height-2, radius, fill=SURFACE2)
        self.create_text(icon_w/2 + 1, height/2, text=icon, fill=MUTED, font=("Segoe Fluent Icons", 12))
        
        self.entry = tk.Entry(self, textvariable=textvariable, show=show, bg=bg_color, fg=fg_color, font=font, relief="flat", insertbackground=BLUE, highlightthickness=0)
        self.placeholder = placeholder
        self.fg_color = fg_color
        self.textvariable = textvariable
        self.show = show
        
        if self.placeholder and not self.textvariable.get():
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
        if self.entry.cget("show"):
            self.entry.config(show="")
            self.itemconfig(self.eye_id, text="\uED1A")
        else:
            self.entry.config(show="●")
            self.itemconfig(self.eye_id, text="\uE890")
            
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
        
        kwargs_rect = {"fill": btn_color}
        kwargs_rect["outline"] = outline_color if outline_color else "#05080E"
        kwargs_rect["width"] = outline_width if outline_width else 1
            
        self.rect_id = self._create_rounded_rect(0, 0, width-1, height-1, radius, **kwargs_rect)
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

class ScrollableCardsFrame(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("Dark.Vertical.TScrollbar", troughcolor=BG, background=CARD, bordercolor=BG, arrowcolor=TEXT, relief="flat", borderwidth=0, arrowsize=12)
        s.map("Dark.Vertical.TScrollbar", background=[("active", SURFACE2)])
        self.scrollbar.configure(style="Dark.Vertical.TScrollbar")
        
        self.scrollable_frame = tk.Frame(self.canvas, bg=BG)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.bind("<Configure>", self._on_frame_configure)
        
        def _auto_hide_scrollbar(*args):
            self.scrollbar.set(*args)
            if float(args[0]) <= 0.0 and float(args[1]) >= 1.0:
                self.scrollbar.grid_remove()
            else:
                self.scrollbar.grid()

        self.canvas.configure(yscrollcommand=_auto_hide_scrollbar)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
    def _on_frame_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

# ── Application Main ────────────────────────────────────────────────────────

class SSHBuddyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("⚡ SSH Buddy")
        self.root.geometry("1100x700")
        self.root.minsize(900, 520)
        self.root.configure(bg=BG)
        self._all = []
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        self._build()
        self._load()

    def _build(self):
        # Header
        hdr = tk.Frame(self.root, bg=BG2, height=64)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        lf = tk.Frame(hdr, bg=BG2)
        lf.pack(side="left", padx=20, pady=16)
        tk.Label(lf, text="⚡", bg=BG2, fg=GREEN, font=("Segoe UI", 20, "bold")).pack(side="left")
        tk.Label(lf, text=" SSH Buddy", bg=BG2, fg=TEXT, font=FT_TITLE).pack(side="left", padx=(5,0))
        
        self._badge = tk.StringVar(value="0 servers")
        tk.Label(hdr, textvariable=self._badge, bg=CARD, fg=MUTED, font=FT_SMALL).pack(side="right", padx=20, pady=20)
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        # Toolbar
        tb = tk.Frame(self.root, bg=BG)
        tb.pack(fill="x", padx=16, pady=(16, 8))
        
        add_btn = RoundedButton(tb, text="Add Server", icon="\uE710", command=self._add, width=160, height=44, radius=8, btn_color="#0E9F6E", fg_color=TEXT, hover_color=GREEN, font=FT_BTN)
        add_btn.pack(side="left", padx=4)
        
        ref_btn = RoundedButton(tb, text="Refresh", icon="\uE72C", command=self._load, width=120, height=44, radius=8, btn_color=CARD, fg_color=TEXT, hover_color=SURFACE2, font=FT_BTN, outline_color=BORDER, outline_width=1)
        ref_btn.pack(side="left", padx=4)

        pwd_btn = RoundedButton(tb, text="Password", icon="\uE8D7", command=self._change_password, width=130, height=44, radius=8, btn_color=CARD, fg_color=TEXT, hover_color=SURFACE2, font=FT_BTN, outline_color=BORDER, outline_width=1)
        pwd_btn.pack(side="left", padx=4)

        sf = tk.Frame(tb, bg=BG)
        sf.pack(side="right", padx=4)
        self._sv = tk.StringVar()
        self._sv.trace("w", self._search)
        self._search_entry = RoundedIconEntry(sf, icon="\uE721", textvariable=self._sv, width=320, height=44, radius=8, bg_color=CARD, fg_color=TEXT, font=FT_INPUT, placeholder="Search by IP, alias, tags...")
        self._search_entry.pack()

        # Cards Area
        self.cards_frame = ScrollableCardsFrame(self.root)
        self.cards_frame.pack(fill="both", expand=True, padx=8, pady=8)

    def _search(self, *_):
        if not hasattr(self, 'cards_frame'): return
        q = self._sv.get().strip()
        if q == "Search by IP, alias, tags...":
            q = ""
        self._fill(search_servers(q) if q else self._all)

    def _load(self, *_):
        self._all = get_all_servers()
        self._fill(self._all)

    def _fill(self, servers):
        for widget in self.cards_frame.scrollable_frame.winfo_children():
            widget.destroy()
            
        if not servers:
            lbl = tk.Label(self.cards_frame.scrollable_frame, text="No servers found. Add one to get started.", bg=BG, fg=MUTED, font=FT_SUB)
            lbl.pack(pady=60)
            self._badge.set("0 servers")
            return
            
        for srv in servers:
            self._create_server_card(srv)
            
        n = len(servers)
        self._badge.set(f"{n} server{'s' if n!=1 else ''}")

    def _create_server_card(self, srv):
        card = RoundedCard(self.cards_frame.scrollable_frame, radius=8, bg_color=CARD, parent_bg=BG, left_glow=True)
        card.pack(fill="x", padx=16, pady=6)
        
        inner = card.inner
        
        icon_f = tk.Frame(inner, bg=CARD)
        icon_f.pack(side="left", padx=(20, 16), pady=20)
        tk.Label(icon_f, text="\uE7F4", bg=SURFACE2, fg=BLUE, font=("Segoe Fluent Icons", 20)).pack(ipadx=12, ipady=12)
        
        det_f = tk.Frame(inner, bg=CARD)
        det_f.pack(side="left", fill="y", pady=20)
        tk.Label(det_f, text=srv["alias"], bg=CARD, fg=TEXT, font=FT_SUB).pack(anchor="w")
        tk.Label(det_f, text=f"{srv['username']}@{srv['ip']}:{srv['port']}", bg=CARD, fg=MUTED, font=FT_MONO).pack(anchor="w", pady=(4,0))
        
        extra_f = tk.Frame(inner, bg=CARD)
        extra_f.pack(side="left", fill="both", expand=True, padx=40, pady=20)
        
        if srv.get("tags"):
            tags_f = tk.Frame(extra_f, bg=CARD)
            tags_f.pack(anchor="w")
            tk.Label(tags_f, text="\uE8EC", bg=CARD, fg=MUTED, font=("Segoe Fluent Icons", 10)).pack(side="left")
            tk.Label(tags_f, text=f" {srv['tags']}", bg=CARD, fg=MUTED, font=FT_SMALL).pack(side="left")
            
        if srv.get("notes"):
            notes_f = tk.Frame(extra_f, bg=CARD)
            notes_f.pack(anchor="w", pady=(8,0))
            tk.Label(notes_f, text="\uE8A5", bg=CARD, fg=MUTED, font=("Segoe Fluent Icons", 10)).pack(side="left")
            tk.Label(notes_f, text=f" {srv['notes']}", bg=CARD, fg=MUTED, font=FT_SMALL).pack(side="left")
            
        act_f = tk.Frame(inner, bg=CARD)
        act_f.pack(side="right", padx=20, pady=20)
        
        RoundedButton(act_f, text="Connect", icon="\uE945", command=lambda s=srv: self._connect_srv(s),
                      width=140, height=44, radius=8, btn_color="#0E9F6E", fg_color=TEXT, hover_color=GREEN, font=FT_BTN).pack(side="left", padx=6)
        RoundedButton(act_f, text="", icon="\uE70F", command=lambda s=srv: self._edit_srv(s),
                      width=44, height=44, radius=8, btn_color=SURFACE2, fg_color=TEXT, hover_color=BLUE, font=FT_BTN).pack(side="left", padx=6)
        RoundedButton(act_f, text="", icon="\uE8D7", command=lambda s=srv: self._copy_key_flow(s),
                      width=44, height=44, radius=8, btn_color=SURFACE2, fg_color=TEXT, hover_color=YELLOW, font=FT_BTN).pack(side="left", padx=6)
        RoundedButton(act_f, text="", icon="\uE8D8", command=lambda s=srv: self._remove_key_flow(s),
                      width=44, height=44, radius=8, btn_color=SURFACE2, fg_color="#F97316", hover_color=RED, font=FT_BTN).pack(side="left", padx=6)
        RoundedButton(act_f, text="", icon="\uE74D", command=lambda s=srv: self._delete_srv(s),
                      width=44, height=44, radius=8, btn_color=SURFACE2, fg_color=RED, hover_color="#7F1D1D", font=FT_BTN).pack(side="left", padx=6)

    def _connect_srv(self, srv):
        from .connector import connect_ssh, check_key_auth
        
        def _check_and_connect():
            if srv.get("use_key", 0):
                # User wants key auth, verify it works
                key_works = check_key_auth(srv["ip"], srv["username"], srv["port"])
                if key_works:
                    connect_ssh(srv["ip"], srv["username"], srv["port"], None, from_gui=True, try_key_first=True)
                    return
                # Key auth failed. Correct DB and show error
                update_server(srv["alias"], use_key=0)
                self.root.after(0, lambda: _key_failed_fallback())
                return
                
            # If use_key is 0, respect it and prompt for password
            self.root.after(0, _prompt_password_and_connect)
        
        def _key_failed_fallback():
            """Show error that SSH key was not found, then fallback to password."""
            messagebox.showwarning(
                "SSH Key Not Found",
                f"SSH key was not found on {srv['username']}@{srv['ip']}.\n\n"
                f"This server does not have your SSH key configured.\n"
                f"Falling back to password authentication.",
            )
            _prompt_password_and_connect()
            
        def _prompt_password_and_connect():
            pw = get_password(srv["alias"])
            if not pw:
                dlg = _PwDlg(self.root, srv)
                self.root.wait_window(dlg.top)
                if dlg.cancelled:
                    if getattr(dlg, "force_key", False):
                        # User clicked "Try Key Auth Instead"
                        threading.Thread(target=lambda: connect_ssh(
                            srv["ip"], srv["username"], srv["port"], None, from_gui=True, try_key_first=True), daemon=True).start()
                    return
                pw = dlg.password or None
                if dlg.save and pw: save_password(srv["alias"], pw)
            
            # Use password
            threading.Thread(target=lambda: connect_ssh(
                srv["ip"], srv["username"], srv["port"], pw, from_gui=True), daemon=True).start()

        threading.Thread(target=_check_and_connect, daemon=True).start()

    def _copy_key_flow(self, srv):
        import os, subprocess, platform
        from .connector import copy_ssh_key
        
        pub_keys = ["~/.ssh/id_ed25519.pub", "~/.ssh/id_rsa.pub", "~/.ssh/id_ecdsa.pub", "~/.ssh/id_dsa.pub"]
        found_key = None
        for p in pub_keys:
            full = os.path.expanduser(p)
            if os.path.exists(full):
                found_key = full
                break
                
        if not found_key:
            if messagebox.askyesno("No Key Found", "No SSH key found.\nGenerate one first? (ssh-keygen -t ed25519)"):
                try:
                    kwargs = {}
                    if platform.system() == "Windows": kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                    subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", os.path.expanduser("~/.ssh/id_ed25519"), "-N", ""], **kwargs)
                    found_key = os.path.expanduser("~/.ssh/id_ed25519.pub")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to generate key: {e}")
                    return
            else:
                return
                
        with open(found_key, "r") as f:
            pubkey_content = f.read().strip()
            
        fingerprint = pubkey_content[:40] + "..."
        if not messagebox.askyesno("Copy SSH Key", f"Copy your SSH public key to {srv['username']}@{srv['ip']}?\n\nKey: {fingerprint}\n\nThis will allow passwordless login."):
            return
            
        pw = get_password(srv["alias"])
        if not pw:
            dlg = _PwDlg(self.root, srv)
            self.root.wait_window(dlg.top)
            if dlg.cancelled: return
            pw = dlg.password
            if dlg.save and pw: save_password(srv["alias"], pw)
            
        def _copy_bg():
            success = copy_ssh_key(srv["ip"], srv["username"], srv["port"], pw, pubkey_content)
            if success:
                update_server(srv["alias"], use_key=1)
                self.root.after(0, lambda: messagebox.showinfo("Success", "✅ SSH key copied! You can now connect without password."))
                self.root.after(0, self._load)
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", "Failed to copy SSH key. Check password and permissions."))
                
        threading.Thread(target=_copy_bg, daemon=True).start()

    def _remove_key_flow(self, srv):
        import os, platform
        from .connector import remove_ssh_key
        
        pub_keys = ["~/.ssh/id_ed25519.pub", "~/.ssh/id_rsa.pub", "~/.ssh/id_ecdsa.pub", "~/.ssh/id_dsa.pub"]
        found_key = None
        for p in pub_keys:
            full = os.path.expanduser(p)
            if os.path.exists(full):
                found_key = full
                break
                
        if not found_key:
            messagebox.showinfo("No Key Found", "No local SSH key found. There is nothing to remove.")
            return
                
        with open(found_key, "r") as f:
            pubkey_content = f.read().strip()
            
        if not messagebox.askyesno("Remove SSH Key", f"Remove your SSH key from {srv['username']}@{srv['ip']}?\n\nThis will safely remove your specific key without affecting other users' keys on the server."):
            return
            
        pw = get_password(srv["alias"])
        if not pw:
            dlg = _PwDlg(self.root, srv)
            self.root.wait_window(dlg.top)
            if dlg.cancelled: return
            pw = dlg.password
            if dlg.save and pw: save_password(srv["alias"], pw)
            
        def _remove_bg():
            success = remove_ssh_key(srv["ip"], srv["username"], srv["port"], pw, pubkey_content)
            if success:
                update_server(srv["alias"], use_key=0)
                self.root.after(0, lambda: messagebox.showinfo("Success", "✅ SSH key removed successfully from the server!"))
                self.root.after(0, self._load)
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", "Failed to remove SSH key. Check password and permissions."))
                
        threading.Thread(target=_remove_bg, daemon=True).start()


    def _add(self):
        dlg = _SrvDlg(self.root, "Add Server")
        self.root.wait_window(dlg.top)
        if dlg.result:
            d = dlg.result
            import socket
            try:
                with socket.create_connection((d["ip"], d["port"]), timeout=3):
                    pass
            except OSError:
                messagebox.showerror("Connection Error", f"Could not connect to {d['ip']}:{d['port']}. Server was not saved.")
                return

            ok, msg = add_server(d["alias"], d["ip"], d["username"], d["port"], d["tags"], d["notes"], d.get("use_key", 0))
            if ok:
                if d.get("password"): save_password(d["alias"], d["password"])
                self._load()
            else: messagebox.showerror("Error", msg)

    def _edit_srv(self, srv):
        dlg = _SrvDlg(self.root, "Edit Server", srv)
        self.root.wait_window(dlg.top)
        if dlg.result:
            d = dlg.result
            import socket
            try:
                with socket.create_connection((d["ip"], d["port"]), timeout=3):
                    pass
            except OSError:
                messagebox.showerror("Connection Error", f"Could not connect to {d['ip']}:{d['port']}. Changes were not saved.")
                return

            update_server(srv["alias"], ip=d["ip"], username=d["username"], port=d["port"], tags=d["tags"], notes=d["notes"], use_key=d.get("use_key", 0))
            if d.get("password") == "":
                delete_password(srv["alias"])
            elif d.get("password"):
                save_password(srv["alias"], d["password"])
            self._load()

    def _delete_srv(self, srv):
        if messagebox.askyesno("Delete", f"Delete '{srv['alias']}' ({srv['username']}@{srv['ip']})?"):
            delete_server(srv["alias"])
            delete_password(srv["alias"])
            self._load()

    def _change_password(self):
        dlg = _ChangePwDlg(self.root)
        self.root.wait_window(dlg.top)


class _PwDlg:
    def __init__(self, parent, srv):
        self.password = None
        self.save = False
        self.cancelled = True
        self.force_key = False
        self.srv = srv
        
        t = tk.Toplevel(parent)
        self.top = t
        t.title("SSH Buddy — Password Required")
        t.configure(bg=BG)
        t.resizable(False, False)
        t.transient(parent)
        t.grab_set()
        t.protocol("WM_DELETE_WINDOW", self._cancel)

        hdr = tk.Frame(t, bg=BG2)
        hdr.pack(fill="x", ipady=8)
        tk.Label(hdr, text=f"⚡  {srv['alias']}", bg=BG2, fg=BLUE, font=FT_TITLE).pack(pady=(16, 4))
        tk.Label(hdr, text=f"{srv['username']}@{srv['ip']}:{srv['port']}", bg=BG2, fg=MUTED, font=FT_SUB).pack(pady=(0, 8))
        tk.Frame(t, bg=BORDER, height=1).pack(fill="x")

        card = RoundedCard(t, radius=8, bg_color=CARD, parent_bg=BG, left_glow=True)
        card.pack(fill="x", padx=20, pady=24)

        pf = tk.Frame(card.inner, bg=CARD)
        pf.pack(fill="x", padx=20, pady=(20, 8))
        
        lbl_f = tk.Frame(pf, bg=CARD)
        lbl_f.pack(fill="x", padx=(56, 0), pady=(0, 4))
        tk.Label(lbl_f, text="Password", bg=CARD, fg=MUTED, font=FT_LABEL, anchor="w").pack(side="left")
        
        self._pw_var = tk.StringVar()
        pw_entry = RoundedIconEntry(pf, icon="\uE72E", textvariable=self._pw_var, show="●", width=420, height=44, radius=8, bg_color=BG2, fg_color=TEXT, font=FT_INPUT)
        pw_entry.pack(fill="x")
        pw_entry.focus_set()

        self._save_var = tk.BooleanVar(value=True)
        tk.Checkbutton(card.inner, text="  Remember this password", variable=self._save_var,
                       bg=CARD, fg=TEXT, selectcolor=SURFACE, activebackground=CARD, activeforeground=TEXT,
                       font=FT_SMALL, highlightthickness=0).pack(padx=24, pady=(0, 20), anchor="w")

        pw_entry.entry.bind("<Return>", lambda _: self._ok())

        bf = tk.Frame(t, bg=BG)
        bf.pack(fill="x", padx=20, pady=(8, 24))
        
        ok_btn = RoundedButton(bf, text="Connect", icon="\uE945", command=self._ok,
                               width=160, height=48, radius=8, btn_color="#0E9F6E", fg_color=TEXT, hover_color=GREEN, font=FT_BTN)
        ok_btn.pack(side="left", padx=(0, 4), expand=True)
        
        key_btn = RoundedButton(bf, text="Try Key Auth", icon="\uE8D7", command=self._try_key,
                                width=180, height=48, radius=8, btn_color=SURFACE2, fg_color=BLUE, hover_color=CARD, font=FT_BTN, outline_color=BLUE, outline_width=1)
        key_btn.pack(side="left", padx=4, expand=True)
        
        cancel_btn = RoundedButton(bf, text="Cancel", command=self._cancel,
                                   width=130, height=48, radius=8, btn_color=CARD, fg_color=TEXT, hover_color=SURFACE2, font=FT_BTN, outline_color=BORDER, outline_width=1)
        cancel_btn.pack(side="right", padx=(4, 0), expand=True)

        t.update_idletasks()
        t.minsize(580, 10)

    def _try_key(self):
        from .connector import check_key_auth
        self.top.config(cursor="wait")
        self.top.update()
        
        if check_key_auth(self.srv["ip"], self.srv["username"], self.srv["port"]):
            self.force_key = True
            self.cancelled = True
            self.top.destroy()
        else:
            self.top.config(cursor="")
            messagebox.showerror("Key Not Found", "Your SSH key was not found on this server. Please enter the password to connect.", parent=self.top)

    def _ok(self):
        self.password = self._pw_var.get()
        self.save = self._save_var.get()
        self.cancelled = False
        self.top.destroy()

    def _cancel(self):
        self.cancelled = True
        self.top.destroy()


class _SrvDlg:
    def __init__(self, parent, title="Server", server=None):
        self.result = None
        self.editing = server is not None
        editing = self.editing
        
        t = tk.Toplevel(parent)
        self.top = t
        t.title(title)
        t.configure(bg=BG)
        t.resizable(False, False)
        t.transient(parent)
        t.grab_set()
        t.protocol("WM_DELETE_WINDOW", self._cancel)

        hdr_frame = tk.Frame(t, bg=BG)
        hdr_frame.pack(fill="x", padx=16, pady=(12, 8))
        
        hdr = tk.Canvas(hdr_frame, height=100, bg=CARD, highlightthickness=0)
        hdr.pack(fill="x")
        
        def _draw_radar(w, h):
            hdr.delete("all")
            hdr.create_polygon([0,0, w-1,0, w-1,h-1, 0,h-1], fill=CARD, outline="#05080E", width=1, smooth=True)
            hdr.create_polygon([1,1, w-2,1, w-2,h-2, 1,h-2], fill="", outline="#1F2937", width=1, smooth=True)
            cx, cy = w/2, h/2
            hdr.create_oval(cx-300, cy-150, cx+300, cy+150, fill="#081A12", outline="")
            hdr.create_oval(cx-150, cy-150, cx+150, cy+150, outline="#0A2216", width=1)
            hdr.create_oval(cx-250, cy-250, cx+250, cy+250, outline="#071810", width=1)
            hdr.create_oval(cx+148, cy-2, cx+152, cy+2, fill=GREEN, outline="")
            hdr.create_oval(cx-252, cy-2, cx-248, cy+2, fill="#082A1B", outline="")
            
            alias_text = server["alias"] if editing else "New Server"
            hdr.create_text(cx, h * 0.75, text=alias_text, fill=TEXT, font=FT_SUB)
        
        hdr.bind("<Configure>", lambda e: _draw_radar(e.width, e.height))
        
        badge_f = tk.Frame(hdr, bg="#081A12")
        badge_f.place(relx=0.5, rely=0.35, anchor="center")
        badge_text = "Edit Server" if editing else "Add Server"
        RoundedBadge(badge_f, text=badge_text, icon="\uE70F" if editing else "\uE945", width=220, height=32, radius=16, bg_color="#061510", fg_color=GREEN, border_color="#103F25", font=FT_BTN).pack()

        form_outer = tk.Frame(t, bg=BG)
        form_outer.pack(fill="both", expand=True, padx=16, pady=(8, 0))

        edit_card = RoundedCard(form_outer, radius=8, bg_color=CARD, parent_bg=BG, left_glow=True)
        edit_card.pack(fill="x", pady=(0, 16))

        edit_title = tk.Frame(edit_card.inner, bg=CARD)
        edit_title.pack(fill="x", padx=24, pady=(20, 8))
        tk.Label(edit_title, text="\uE8A4", bg=CARD, fg=BLUE, font=("Segoe Fluent Icons", 14)).pack(side="left")
        tk.Label(edit_title, text="SERVER DETAILS", bg=CARD, fg=MUTED, font=FT_LABEL).pack(side="left", padx=(10,0))

        editable_fields = [
            ("alias",    "Alias * (required)",            server["alias"] if editing else "",        "",                 "\uE77B"),
            ("ip",       "IP Address *",                  server["ip"] if editing else "",           "e.g. 192.168.1.1", "\uE7F4"),
            ("username", "Username *",                    server["username"] if editing else "",     "e.g. root",        "\uE77B"),
            ("port",     "Port",                          str(server["port"]) if editing else "22",  "22",               "\uE17D"),
            ("tags",     "Tags (comma-separated)",        server.get("tags","") if editing else "",  "e.g. prod, web",   "\uE8EC"),
            ("notes",    "Notes",                         server.get("notes","") if editing else "", "Optional notes...", "\uE8A5"),
        ]
        
        self._vars = {}
        self._entries = {}
        first_entry = None
        
        for key, lbl, default, placeholder, icon in editable_fields:
            f = tk.Frame(edit_card.inner, bg=CARD)
            f.pack(fill="x", padx=16, pady=(8, 4))
            lbl_f = tk.Frame(f, bg=CARD)
            lbl_f.pack(fill="x", padx=(56, 0), pady=(0, 4))
            tk.Label(lbl_f, text=lbl, bg=CARD, fg=MUTED, font=FT_LABEL, anchor="w").pack(side="left")
            
            var = tk.StringVar(value=default)
            e = RoundedIconEntry(f, icon=icon, textvariable=var, width=540, height=44, radius=8, bg_color=BG2, fg_color=TEXT, font=FT_INPUT, placeholder=placeholder)
            e.pack(fill="x")
            
            if editing and key == "alias":
                e.entry.config(state="disabled")
                
            self._vars[key] = var
            self._entries[key] = e
            if first_entry is None and not (editing and key == "alias"):
                first_entry = e

        pf = tk.Frame(edit_card.inner, bg=CARD)
        pf.pack(fill="x", padx=16, pady=(8, 24))
        lbl_f = tk.Frame(pf, bg=CARD)
        lbl_f.pack(fill="x", padx=(56, 0), pady=(0, 4))
        pw_lbl = "Password (update or leave empty to clear)" if editing else "Password (optional, saved securely)"
        tk.Label(lbl_f, text=pw_lbl, bg=CARD, fg=MUTED, font=FT_LABEL, anchor="w").pack(side="left")
        
        self._pw = tk.StringVar()
        pw_placeholder = "Leave empty to clear password" if editing else "Leave empty if not required"
        
        if editing:
            saved_pw = get_password(server["alias"])
            if saved_pw:
                self._pw.set(saved_pw)
                
        RoundedIconEntry(pf, icon="\uE72E", textvariable=self._pw, show="●", width=540, height=44, radius=8, bg_color=BG2, fg_color=TEXT, font=FT_INPUT, placeholder=pw_placeholder).pack(fill="x")
        
        use_key_var = tk.BooleanVar(value=bool(server.get("use_key", 0)) if editing else False)
        
        cb_f = tk.Frame(edit_card.inner, bg=CARD, cursor="hand2")
        cb_f.pack(padx=24, pady=(0, 20), anchor="w")
        
        cb_icon = tk.Label(cb_f, text="\uE73A" if use_key_var.get() else "\uE739", bg=CARD, fg=GREEN if use_key_var.get() else MUTED, font=("Segoe Fluent Icons", 14))
        cb_icon.pack(side="left")
        
        cb_text = tk.Label(cb_f, text="  Use SSH key (passwordless)", bg=CARD, fg=TEXT, font=FT_SMALL)
        cb_text.pack(side="left")
        
        def _toggle_cb(*_):
            val = not use_key_var.get()
            use_key_var.set(val)
            
        cb_icon.bind("<Button-1>", _toggle_cb)
        cb_text.bind("<Button-1>", _toggle_cb)
        
        use_key_var.trace_add("write", lambda *_: cb_icon.config(text="\uE73A" if use_key_var.get() else "\uE739", fg=GREEN if use_key_var.get() else MUTED))
        self._use_key_var = use_key_var
        
        self.key_status_lbl = tk.Label(edit_card.inner, text="", bg=CARD, fg=GREEN, font=FT_SMALL)
        self.key_status_lbl.pack(padx=24, pady=(0, 20), anchor="w")
        
        if not editing:
            # Auto-check key auth in background
            def _check_bg():
                from .connector import check_key_auth
                ip = self._vars["ip"].get().strip()
                usr = self._vars["username"].get().strip()
                try: p = int(self._vars["port"].get().strip() or "22")
                except: p = 22
                if ip and usr and ip != "e.g. 192.168.1.1" and usr != "e.g. root":
                    if check_key_auth(ip, usr, p):
                        self.top.after(0, lambda: self._use_key_var.set(True))
                        self.top.after(0, lambda: self.key_status_lbl.config(text="✅ SSH key detected on this server"))
                        
            # Bind to unfocus of IP/username
            self._entries["ip"].entry.bind("<FocusOut>", lambda e: threading.Thread(target=_check_bg, daemon=True).start(), add="+")
            self._entries["username"].entry.bind("<FocusOut>", lambda e: threading.Thread(target=_check_bg, daemon=True).start(), add="+")

        if first_entry:
            first_entry.focus_set()

        bf = tk.Frame(t, bg=BG)
        bf.pack(fill="x", padx=16, pady=(8, 24))

        save_text = "Save Changes" if editing else "Add Server"
        save_btn = RoundedButton(bf, text=save_text, icon="\uE74E", command=self._ok,
                                 width=260, height=48, radius=8, btn_color="#0E9F6E", fg_color=TEXT, hover_color=GREEN, font=FT_BTN)
        save_btn.pack(side="left", expand=True)

        just_btn = RoundedButton(bf, text="Cancel", command=t.destroy,
                                 width=260, height=48, radius=8, btn_color=CARD, fg_color=TEXT, hover_color=SURFACE2, font=FT_BTN, outline_color=BORDER, outline_width=1)
        just_btn.pack(side="right", expand=True)

        t.update_idletasks()
        t.minsize(610, 10)

    def _ok(self):
        alias = self._vars["alias"].get().strip()
        ip = self._vars["ip"].get().strip()
        username = self._vars["username"].get().strip()
        
        if not alias or not ip or not username or alias == "e.g. prod, web" or ip == "e.g. 192.168.1.1" or username == "e.g. root":
             messagebox.showerror("Error", "Alias, IP and Username are required.")
             return
             
        try: port = int(self._vars["port"].get().strip() or "22")
        except ValueError: port = 22
        
        self.result = {
            "alias": alias, "ip": ip, "username": username, "port": port,
            "tags": self._vars["tags"].get().strip(),
            "notes": self._vars["notes"].get().strip(),
            "use_key": 1 if self._use_key_var.get() else 0
        }
        
        for k in ["tags", "notes"]:
            if self.result[k].startswith("e.g.") or self.result[k].startswith("Optional notes"):
                self.result[k] = ""


        pw_val = self._pw.get()
        if pw_val in ["Leave empty if not required", "Leave empty to clear password"]:
            pw_val = "" if self.editing else None
        elif not pw_val and self.editing:
            pw_val = ""
        elif not pw_val:
            pw_val = None
            
        self.result["password"] = pw_val

        self.top.destroy()

    def _cancel(self):
        self.result = None
        self.top.destroy()

def run_gui():
    init_db()
    root = tk.Tk()
    try:
        from ctypes import windll; windll.shcore.SetProcessDpiAwareness(1)
    except Exception: pass
    SSHBuddyApp(root)
    root.mainloop()

class _ChangePwDlg:
    def __init__(self, parent):
        t = tk.Toplevel(parent)
        self.top = t
        t.title("Change Master Password")
        t.configure(bg=BG)
        t.resizable(False, False)
        t.transient(parent)
        t.grab_set()

        hdr = tk.Frame(t, bg=BG2)
        hdr.pack(fill="x", ipady=8)
        tk.Label(hdr, text="🔑 Change Password", bg=BG2, fg=BLUE, font=FT_TITLE).pack(pady=(16, 4))
        tk.Frame(t, bg=BORDER, height=1).pack(fill="x")

        card = RoundedCard(t, radius=8, bg_color=CARD, parent_bg=BG, left_glow=True)
        card.pack(fill="x", padx=20, pady=24)

        pf = tk.Frame(card.inner, bg=CARD)
        pf.pack(fill="x", padx=20, pady=20)
        
        # Old Password
        tk.Label(pf, text="Old Password", bg=CARD, fg=MUTED, font=FT_LABEL, anchor="w").pack(fill="x", pady=(0, 4))
        self.v_old = tk.StringVar()
        RoundedIconEntry(pf, icon="\uE72E", textvariable=self.v_old, show="●", width=420, height=44, radius=8, bg_color=BG2, fg_color=TEXT, font=FT_INPUT).pack(fill="x", pady=(0, 16))
        
        # New Password
        tk.Label(pf, text="New Password", bg=CARD, fg=MUTED, font=FT_LABEL, anchor="w").pack(fill="x", pady=(0, 4))
        self.v_new = tk.StringVar()
        RoundedIconEntry(pf, icon="\uE72E", textvariable=self.v_new, show="●", width=420, height=44, radius=8, bg_color=BG2, fg_color=TEXT, font=FT_INPUT).pack(fill="x", pady=(0, 16))
        
        # Confirm New
        tk.Label(pf, text="Confirm New Password", bg=CARD, fg=MUTED, font=FT_LABEL, anchor="w").pack(fill="x", pady=(0, 4))
        self.v_confirm = tk.StringVar()
        RoundedIconEntry(pf, icon="\uE72E", textvariable=self.v_confirm, show="●", width=420, height=44, radius=8, bg_color=BG2, fg_color=TEXT, font=FT_INPUT).pack(fill="x", pady=(0, 16))

        self.error_lbl = tk.Label(pf, text="Requirements: 12-16 chars, 1 uppercase, 1 lowercase, 1 number, 1 special.", bg=CARD, fg=MUTED, font=FT_SMALL)
        self.error_lbl.pack(pady=4)

        bf = tk.Frame(t, bg=BG)
        bf.pack(fill="x", padx=20, pady=(8, 24))
        
        save_btn = RoundedButton(bf, text="Save Changes", icon="\uE74E", command=self._ok,
                                 width=220, height=48, radius=8, btn_color="#0E9F6E", fg_color=TEXT, hover_color=GREEN, font=FT_BTN)
        save_btn.pack(side="left", expand=True)
        
        cancel_btn = RoundedButton(bf, text="Cancel", command=self.top.destroy,
                                   width=220, height=48, radius=8, btn_color=CARD, fg_color=TEXT, hover_color=SURFACE2, font=FT_BTN, outline_color=BORDER, outline_width=1)
        cancel_btn.pack(side="right", expand=True)

        t.update_idletasks()
        x = (t.winfo_screenwidth() // 2) - (t.winfo_width() // 2)
        y = (t.winfo_screenheight() // 2) - (t.winfo_height() // 2)
        t.geometry(f"+{x}+{y}")

    def _ok(self):
        from .security import change_master_password
        old = self.v_old.get()
        new = self.v_new.get()
        confirm = self.v_confirm.get()
        
        ok, msg = change_master_password(old, new, confirm)
        if ok:
            messagebox.showinfo("Success", msg, parent=self.top)
            self.top.destroy()
        else:
            self.error_lbl.config(text=msg, fg=RED)
