=============================================
  SSH Buddy — Quick Start Guide
=============================================

FIRST TIME SETUP:
  python installer.py
  (then restart your terminal)

DAILY USE:
  - Tray icon is always running in your taskbar
  - Just type: ssh user@ip  (the wrapper handles everything)
  - Or open the GUI from the tray icon

MANUAL COMMANDS (if needed):
  python ssh_buddy.py gui          Open the graphical interface
  python ssh_buddy.py add          Add a server interactively
  python ssh_buddy.py connect      Pick a server and connect
  python ssh_buddy.py list         List all saved servers
  python ssh_buddy.py search xxx   Search by IP, alias, etc.
  python ssh_buddy.py delete alias Delete a server
  python ssh_buddy.py export       Export servers to JSON
  python ssh_buddy.py import f.json Import servers from JSON

  python ssh_buddy.py install      Re-run the installer
  python ssh_buddy.py tray         Start the tray app only
  python ssh_buddy.py wrapper user@ip  Run the SSH wrapper directly
