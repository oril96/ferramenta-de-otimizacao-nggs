param(
    [switch]$Install
)

if ($Install) {
    Write-Host "Installing dependencies (PyQt6)..."
    python -m pip install --upgrade pip
    python -m pip install PyQt6
}

Write-Host "Launching Optimus Toolbox UI..."
python -m src.main

