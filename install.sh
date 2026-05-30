#!/bin/bash
# install.sh — SSH Buddy installer for Linux
set -e

echo ""
echo "⚡ SSH Buddy — Linux Installer"
echo "================================"

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "✗ Python3 not found. Install: sudo apt install python3 python3-pip"
    exit 1
fi

# Install Python deps
echo "→ Installing Python dependencies..."
pip3 install -r requirements.txt --quiet

# Install sshpass (for password-based SSH)
echo "→ Checking sshpass..."
if ! command -v sshpass &>/dev/null; then
    echo "  sshpass not found. Installing..."
    if command -v apt &>/dev/null; then
        sudo apt install -y sshpass
    elif command -v yum &>/dev/null; then
        sudo yum install -y sshpass
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y sshpass
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm sshpass
    else
        echo "  ⚠ Could not install sshpass automatically."
        echo "    Install manually: your-package-manager install sshpass"
    fi
else
    echo "  ✓ sshpass already installed"
fi

# Create launcher alias
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALIAS_LINE="alias ssh-buddy='python3 $SCRIPT_DIR/ssh_buddy.py'"

echo ""
echo "→ Adding alias to shell config..."

for RC in ~/.bashrc ~/.zshrc; do
    if [ -f "$RC" ]; then
        if ! grep -q "ssh-buddy" "$RC"; then
            echo "" >> "$RC"
            echo "# SSH Buddy" >> "$RC"
            echo "$ALIAS_LINE" >> "$RC"
            echo "  ✓ Added to $RC"
        else
            echo "  ✓ Already in $RC"
        fi
    fi
done

# Create a symlink in /usr/local/bin if writable
if [ -w /usr/local/bin ]; then
    cat > /usr/local/bin/ssh-buddy << EOF
#!/bin/bash
python3 "$SCRIPT_DIR/ssh_buddy.py" "\$@"
EOF
    chmod +x /usr/local/bin/ssh-buddy
    echo "  ✓ Created /usr/local/bin/ssh-buddy"
fi

echo ""
echo "✅ Done!"
echo ""
echo "  CLI : ssh-buddy add | list | connect | search | delete"
echo "  GUI : ssh-buddy gui"
echo ""
echo "  Reload shell:  source ~/.bashrc"
echo ""
