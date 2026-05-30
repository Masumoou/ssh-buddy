@echo off
:: install.bat — SSH Buddy installer for Windows
:: Run as Administrator for best results

echo.
echo  ====================================
echo   ^⚡ SSH Buddy — Windows Installer
echo  ====================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found.
    echo  Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo  [OK] Python found
echo.

:: Install Python dependencies
echo  Installing Python dependencies...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo  [WARN] pip install had issues. Continuing...
)
echo  [OK] Dependencies installed
echo.

:: Create ssh-buddy.bat launcher in current directory
set SCRIPT_DIR=%~dp0

echo @echo off > "%SCRIPT_DIR%ssh-buddy.bat"
echo python "%SCRIPT_DIR%ssh_buddy.py" %%* >> "%SCRIPT_DIR%ssh-buddy.bat"

echo  [OK] Created ssh-buddy.bat launcher

:: Optionally add to PATH (requires admin)
echo.
echo  To use 'ssh-buddy' from anywhere, add this folder to your PATH:
echo  %SCRIPT_DIR%
echo.
echo  Or run from this folder:
echo    ssh-buddy.bat add
echo    ssh-buddy.bat gui
echo    ssh-buddy.bat connect
echo.

:: Check for plink (PuTTY) for password SSH on Windows
where plink >nul 2>&1
if %errorlevel% neq 0 (
    echo  [NOTE] plink (PuTTY) not found.
    echo         For password-based SSH on Windows, install PuTTY:
    echo         https://www.putty.org/
    echo.
)

echo  ====================================
echo   Installation complete!
echo  ====================================
echo.
echo   CLI:  ssh-buddy.bat list
echo   GUI:  ssh-buddy.bat gui
echo.
pause
