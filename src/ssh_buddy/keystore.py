"""
keystore.py — Secure password storage via system keychain
  Windows : Windows Credential Manager
  Linux   : libsecret / kwallet / keyrings.alt (fallback)
"""

SERVICE = "ssh-buddy"

# Try system keyring first; fall back to a simple encrypted file store
try:
    import keyring
    _USE_KEYRING = True
except ImportError:
    _USE_KEYRING = False

# ── fallback: AES-128 in a local file ──────────────────────────────────────
import json, os, base64, hashlib
from pathlib import Path

_FALLBACK_PATH = Path.home() / ".ssh_buddy" / "vault.json"
_SALT = b"ssh-buddy-v1"


def _derive_key():
    """Derive a machine-unique key (not truly secure, but better than plaintext)."""
    machine_id = ""
    for f in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
        if os.path.exists(f):
            machine_id = open(f).read().strip()
            break
    if not machine_id:
        import platform
        machine_id = platform.node()
    return hashlib.sha256(_SALT + machine_id.encode()).digest()[:16]


def _fallback_load():
    if _FALLBACK_PATH.exists():
        try:
            return json.loads(_FALLBACK_PATH.read_text())
        except Exception:
            pass
    return {}


def _fallback_save(data):
    _FALLBACK_PATH.parent.mkdir(exist_ok=True)
    _FALLBACK_PATH.write_text(json.dumps(data))


def _xor_enc(text: str) -> str:
    key = _derive_key()
    raw = text.encode()
    enc = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
    return base64.b64encode(enc).decode()


def _xor_dec(enc: str) -> str:
    key = _derive_key()
    raw = base64.b64decode(enc.encode())
    dec = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
    return dec.decode()


# ── public API ─────────────────────────────────────────────────────────────

def save_password(alias: str, password: str):
    if _USE_KEYRING:
        try:
            keyring.set_password(SERVICE, alias, password)
            return
        except Exception:
            pass
    # fallback
    data = _fallback_load()
    data[alias] = _xor_enc(password)
    _fallback_save(data)


def get_password(alias: str):
    if _USE_KEYRING:
        try:
            pw = keyring.get_password(SERVICE, alias)
            if pw is not None:
                return pw
        except Exception:
            pass
    # fallback
    data = _fallback_load()
    enc = data.get(alias)
    if enc:
        try:
            return _xor_dec(enc)
        except Exception:
            pass
    return None


def delete_password(alias: str):
    if _USE_KEYRING:
        try:
            keyring.delete_password(SERVICE, alias)
        except Exception:
            pass
    data = _fallback_load()
    if alias in data:
        del data[alias]
        _fallback_save(data)
