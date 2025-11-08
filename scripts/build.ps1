param(
    [switch]$OneFile,
    [string]$Icon,
    [switch]$UacAdmin
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Exec($exe, [string[]]$argList=@()) {
    $argLine = [string]::Join(' ', $argList)
    Write-Host "`n> $exe $argLine" -ForegroundColor Cyan
    $p = Start-Process -FilePath $exe -ArgumentList $argLine -NoNewWindow -PassThru -Wait
    if ($p.ExitCode -ne 0) { throw "Command failed with exit code $($p.ExitCode): $exe" }
}

# Ensure previous app instances are not locking files
Get-Process -Name 'OptimusToolbox' -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "Stopping running process: $($_.Name) (Id=$($_.Id))" -ForegroundColor Yellow
    try { Stop-Process -Id $_.Id -Force -ErrorAction Stop } catch {}
}

# Ensure venv
if (-not (Test-Path .venv)) {
    Write-Host "Creating virtualenv (.venv)..."
    python -m venv .venv
}

$py = Join-Path .venv 'Scripts/python.exe'
$pip = Join-Path .venv 'Scripts/pip.exe'
if (-not (Test-Path $py)) { throw "Virtualenv seems corrupted: $py not found" }

# Install deps
Exec $py @('-m','pip','install','--upgrade','pip')
Exec $pip @('install','--upgrade','pyinstaller','PyQt6')

# Verify PyQt6 import
$code = '"import PyQt6, sys; print(\"PyQt6 OK:\", PyQt6.__file__)"'
Exec $py @('-c', $code)

# Clean old build (best-effort)
function SafeRemove($p) {
    if (Test-Path $p) {
        try { Remove-Item -Recurse -Force -ErrorAction Stop $p }
        catch { Write-Host "Skip cleaning ${p}: $($_.Exception.Message)" -ForegroundColor Yellow }
    }
}
SafeRemove build
SafeRemove dist
SafeRemove OptimusToolbox.spec

# Build args (write to fresh output paths to avoid locks)
$buildArgs = @('--noconfirm','--clean','--noconsole','--name','OptimusToolbox','--collect-all','PyQt6','--distpath','dist_build','--workpath','build_tmp','src/main.py')
if ($OneFile) { $buildArgs = @('--onefile') + $buildArgs }
if ($Icon)    { $buildArgs = @('--icon', $Icon) + $buildArgs }
if ($UacAdmin){ $buildArgs = @('--uac-admin') + $buildArgs }

# Run PyInstaller
Exec (Join-Path .venv 'Scripts/pyinstaller.exe') $buildArgs

Write-Host "`nBuild finished." -ForegroundColor Green
if ($OneFile) {
    Write-Host "Executable: dist_build\\OptimusToolbox.exe"
} else {
    Write-Host "Executable: dist_build\\OptimusToolbox\\OptimusToolbox.exe"
}


