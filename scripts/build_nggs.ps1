param(
    [switch]$OneFile,
    [string]$Icon = 'nggs.png',
    [switch]$UacAdmin,
    [string]$Name = 'otimizador NGGS-NegroMancer'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Exec($exe, [string[]]$argList=@()) {
    $quoted = $argList | ForEach-Object {
        $s = $_
        if ($s -match '[:;,.(){}\[\]\s]') { '"' + ($s -replace '"','\"') + '"' } else { $s }
    }
    $argLine = [string]::Join(' ', $quoted)
    Write-Host "`n> $exe $argLine" -ForegroundColor Cyan
    $p = Start-Process -FilePath $exe -ArgumentList $argLine -NoNewWindow -PassThru -Wait
    if ($p.ExitCode -ne 0) { throw "Command failed with exit code $($p.ExitCode): $exe" }
}

# Ensure previous app instances are not locking files
Get-Process -Name $Name -ErrorAction SilentlyContinue | ForEach-Object {
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
Exec $py @('-c','import PyQt6, sys; print(''PyQt6 OK:'', PyQt6.__file__)')

# Clean old build (best-effort)
function SafeRemove($p) {
    if (Test-Path $p) {
        try { Remove-Item -Recurse -Force -ErrorAction Stop $p }
        catch { Write-Host "Skip cleaning ${p}: $($_.Exception.Message)" -ForegroundColor Yellow }
    }
}
SafeRemove build
SafeRemove dist
if (Test-Path "$Name.spec") { Remove-Item -Force "$Name.spec" -ErrorAction SilentlyContinue }
if (Test-Path *.spec) { Remove-Item -Force *.spec -ErrorAction SilentlyContinue }

# Handle icon (convert PNG to ICO when needed)
New-Item -ItemType Directory -Force -Path build_tmp | Out-Null
$iconArg = $null
if ($Icon -and (Test-Path $Icon)) {
    $ext = [System.IO.Path]::GetExtension($Icon).ToLowerInvariant()
    if ($ext -eq '.png') {
        $icoPath = (Join-Path 'build_tmp' 'app_icon.ico')
        Exec $pip @('install','--upgrade','pillow')
        $pycode = "from PIL import Image; Image.open(r'$Icon').save(r'$icoPath', sizes=[(256,256),(128,128),(64,64),(32,32),(16,16)])"
        Exec $py @('-c', $pycode)
        $iconArg = $icoPath
    } elseif ($ext -eq '.ico') {
        $iconArg = $Icon
    }
}

# Build args (as array for reliable quoting)
$buildArgs = @('--noconfirm','--clean','--noconsole','--name', $Name, '--collect-all','PyQt6','--distpath','dist_build','--workpath','build_tmp')
if ($iconArg) { $buildArgs += @('--icon', $iconArg) }
$bg = 'backgroundnggs.png'
if (Test-Path $bg) { $buildArgs += @('--add-data', "$bg;.") }
$logo = 'nggs.png'
if (Test-Path $logo) { $buildArgs += @('--add-data', "$logo;.") }
$buildArgs += @('src/main.py')
if ($OneFile) { $buildArgs = @('--onefile') + $buildArgs }
if ($UacAdmin){ $buildArgs = @('--uac-admin') + $buildArgs }

# Run PyInstaller
Exec (Join-Path .venv 'Scripts/pyinstaller.exe') $buildArgs

Write-Host "`nBuild finished." -ForegroundColor Green
if ($OneFile) {
    $p = Join-Path 'dist_build' ($Name + '.exe')
    Write-Host "Executable: '$p'"
} else {
    $p = Join-Path (Join-Path 'dist_build' $Name) ($Name + '.exe')
    Write-Host "Executable: '$p'"
}
