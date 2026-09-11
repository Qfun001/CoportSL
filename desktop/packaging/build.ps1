$ErrorActionPreference = "Stop"

$desktopRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$projectRoot = (Resolve-Path (Join-Path $desktopRoot "..")).Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPython) {
    $python = $venvPython
}
else {
    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python was not found. Create .venv and install requirements.txt and requirements-desktop.txt."
    }
    $python = $pythonCommand.Source
}

& (Join-Path $PSScriptRoot "build-workers.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "C++ worker build failed."
}

Push-Location $projectRoot
try {
    & $python -m compileall -q desktop tools
    if ($LASTEXITCODE -ne 0) {
        throw "Python syntax check failed."
    }
    & $python -m PyInstaller --clean --noconfirm (Join-Path $PSScriptRoot "CoportSL.spec")
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller packaging failed."
    }
}
finally {
    Pop-Location
}

$artifact = Join-Path $projectRoot "dist\CoportSL.exe"
if (-not (Test-Path -LiteralPath $artifact)) {
    throw "Package build completed but artifact was not found: $artifact"
}

Get-Item -LiteralPath $artifact | Select-Object FullName, Length, LastWriteTime
Get-FileHash -LiteralPath $artifact -Algorithm SHA256
