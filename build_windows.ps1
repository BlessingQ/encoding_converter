$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$iconPngPath = Join-Path $projectRoot "assets\icon.png"
$iconIcoPath = Join-Path $projectRoot "assets\icon.ico"
$venvPython3 = Join-Path $projectRoot ".venv\Scripts\python3.exe"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$localPython = Join-Path $projectRoot "tools\python313\python.exe"
$pythonCmd = $null

if (Test-Path $venvPython3) {
    $pythonCmd = $venvPython3
} elseif (Test-Path $venvPython) {
    $pythonCmd = $venvPython
} elseif (Test-Path $localPython) {
    $pythonCmd = $localPython
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} else {
    throw "Python launcher not found. Create .venv, install Python, add py/python to PATH, or place Python at tools\\python313\\python.exe."
}

$args = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--windowed",
    "--onefile",
    "--name", "ENCConverter",
    "--collect-all", "tkinterdnd2",
    "gui.py"
)

if (Test-Path $iconIcoPath) {
    $args += @("--icon", "assets/icon.ico")
}

if (Test-Path $iconPngPath) {
    $args += @("--add-data", "assets/icon.png:assets")
}

& $pythonCmd @args

Write-Host ""
Write-Host "Build complete:"
Write-Host "  dist/ENCConverter.exe"
