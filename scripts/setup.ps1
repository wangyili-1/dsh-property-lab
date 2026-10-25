param([string]$Python = "", [switch]$InstallDsh)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$venv = Join-Path $projectRoot '.venv'
if (-not (Test-Path -LiteralPath (Join-Path $venv 'Scripts\python.exe'))) {
    if ($Python) { & $Python -m venv $venv }
    elseif (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv $venv }
    else { & python -m venv $venv }
    if ($LASTEXITCODE -ne 0) { throw 'Unable to create the virtual environment (Python >= 3.10 required).' }
}
$runner = Join-Path $venv 'Scripts\python.exe'
& $runner -m pip install -e "$projectRoot[dev]"
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $runner -m dsh_property_lab doctor
if ($LASTEXITCODE -ne 0) { throw 'Environment check failed.' }
if ($InstallDsh) {
    & $runner -m dsh_property_lab install-dsh
    if ($LASTEXITCODE -ne 0) { throw 'DSH skill installation failed.' }
}
Write-Host "Ready: $runner -m dsh_property_lab demo"
