Write-Host "⚡ Downloading SSH Buddy..." -ForegroundColor Cyan
$repoUrl = "https://github.com/Masumoou/ssh-buddy/archive/refs/heads/main.zip"
$tempZip = "$env:TEMP\ssh-buddy.zip"
$installDir = "$env:USERPROFILE\ssh-buddy"

# Download Zip
Invoke-WebRequest -Uri $repoUrl -OutFile $tempZip

Write-Host "📦 Extracting files..." -ForegroundColor Cyan
Expand-Archive -Path $tempZip -DestinationPath $env:TEMP -Force

# Move to User Profile folder
if (Test-Path $installDir) {
    Remove-Item -Recurse -Force $installDir
}
Move-Item -Path "$env:TEMP\ssh-buddy-main" -Destination $installDir -Force

Set-Location $installDir
Write-Host "🚀 Starting Installer..." -ForegroundColor Green

# Run the UI installer
python installer.py
