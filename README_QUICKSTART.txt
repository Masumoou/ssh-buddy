=============================================
  SSH Buddy — Quick Start Guide
=============================================

FIRST TIME SETUP (Windows):
  Open PowerShell and run:
  iwr https://raw.githubusercontent.com/Masumoou/ssh-buddy/main/install.ps1 -UseBasicParsing | iex

FIRST TIME SETUP (Linux):
  curl -sL https://raw.githubusercontent.com/Masumoou/ssh-buddy/main/install.sh | bash

DAILY USE (Restart your terminal first!):
  - Just type: ssh user@ip  (the wrapper handles everything, shows GUI if new)
  - Need the GUI? Type: sshbuddy  (from anywhere!)
  - Or open the GUI from the tray icon in your taskbar.

MANUAL COMMANDS (if needed):
  ssh-buddy add          Add a server interactively
  ssh-buddy connect      Pick a server and connect
  ssh-buddy list         List all saved servers
  ssh-buddy search xxx   Search by IP, alias, etc.
  ssh-buddy delete alias Delete a server
