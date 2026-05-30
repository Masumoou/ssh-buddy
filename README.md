# ⚡ SSH Buddy

> **Never forget a server IP, username, or password again.**

SSH Buddy saves all your server info (IP, username, port, tags, notes) and lets you
connect with one command — or one click in the GUI.

---

## 🚀 Quick Start

### Linux
```bash
chmod +x install.sh
./install.sh
source ~/.bashrc

ssh-buddy add          # add your first server
ssh-buddy connect      # pick from list and connect
ssh-buddy gui          # launch GUI
```

### Windows
```
Double-click install.bat (or run as Admin)

ssh-buddy.bat add
ssh-buddy.bat gui
```

---

## 📦 Requirements

| Requirement | Notes |
|---|---|
| Python 3.8+ | Built-in on most Linux; download from python.org for Windows |
| `keyring` lib | Installed via `pip install -r requirements.txt` |
| `sshpass` | Linux only — for password auto-fill (`sudo apt install sshpass`) |
| `plink` (optional) | Windows — for password auto-fill (install PuTTY) |

---

## 💻 CLI Commands

```
ssh-buddy add                   → add a new server (interactive)
ssh-buddy list                  → list all saved servers
ssh-buddy connect               → pick from list → connect
ssh-buddy connect prod-web      → connect by exact alias
ssh-buddy connect 207.31        → search by IP → connect
ssh-buddy connect ubuntu        → search by username → connect
ssh-buddy connect "invoicing"   → search by notes/tags → connect
ssh-buddy search oblak          → search without connecting
ssh-buddy delete prod-web       → delete a server
ssh-buddy export                → export all servers to JSON
ssh-buddy import backup.json    → import servers from JSON
ssh-buddy gui                   → launch GUI window
```

### Example Connect Flow (CLI)
```
$ ssh-buddy connect web

  Multiple matches:
  ALIAS           IP               USERNAME       PORT   TAGS
  ─────────────────────────────────────────────────────────
  prod-web        10.10.207.31     ubuntu         22     oblak,wcf
  staging-web     10.10.207.45     ubuntu         22     staging

  Pick number [1-2]: 1

→ prod-web — ubuntu@10.10.207.31:22
  tags: oblak,wcf
  notes: IIS server - AccountManagement, Authentication

Launching SSH...
```

---

## 🖥️ GUI

```bash
ssh-buddy gui
# or
python ssh_buddy.py gui
```

| Action | How |
|---|---|
| Connect | Double-click a row, OR select + click ⚡ CONNECT |
| Search | Type anything in the search bar (live filter) |
| Add server | Click ➕ Add |
| Edit server | Select row → ✏️ Edit |
| Delete | Select row → 🗑️ Delete (or press Delete key) |
| Sort | Click any column header |

---

## 🔐 Password Storage

- **Saved password**: stored in OS keychain (Windows Credential Manager / libsecret on Linux)
- **No keychain available** (headless Linux): auto-fallback to `~/.ssh_buddy/vault.json` (XOR-obfuscated, not military-grade but not plaintext)
- **No password saved**: SSH Buddy asks at connect time, with option to save
- **Key-based auth**: just leave password blank — SSH Buddy passes through to normal SSH

### Headless Linux (no desktop)
```bash
pip install keyrings.alt    # simple file-based keyring
# OR uncomment it in requirements.txt and re-run install.sh
```

---

## 📁 File Structure

```
ssh-buddy/
├── ssh_buddy.py    ← entry point
├── cli.py          ← all CLI commands
├── gui.py          ← tkinter GUI
├── db.py           ← SQLite operations
├── keystore.py     ← password storage
├── connector.py    ← SSH execution engine
├── requirements.txt
├── install.sh      ← Linux installer
├── install.bat     ← Windows installer
└── README.md
```

Data stored at: `~/.ssh_buddy/servers.db` and `~/.ssh_buddy/vault.json`

---

## 🔄 Backup / Move to Another Machine

```bash
# Export
ssh-buddy export my_servers.json

# On new machine
ssh-buddy import my_servers.json
# Then re-add passwords (not exported for security)
```

---

## 🛠️ Tips

- **Tags**: use comma-separated keywords like `oblak,wcf,iis,staging` — makes search fast
- **Notes**: write what the server does — `"IIS, AccountManagement, WCF endpoints"`
- **Alias**: make it memorable — `prod-web`, `db-01`, `staging-appsrv`
- **Search**: partial match — type `207` to find all `10.10.207.x` servers

---

## 🔮 Planned Improvements (open in Antigravity)

- [ ] SSH key selection per server
- [ ] Server groups / folders
- [ ] Jump host / bastion support (`ProxyJump`)
- [ ] Connection history & timestamps
- [ ] Ping / status check before connecting
- [ ] SFTP / SCP file transfer shortcut
- [ ] Import from `~/.ssh/config`
- [ ] Export to `~/.ssh/config`
- [ ] Tray icon (system tray) on Windows
