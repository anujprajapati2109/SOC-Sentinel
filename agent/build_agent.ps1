$ErrorActionPreference = "Stop"

$agentRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $agentRoot

python -m pip install -r requirements-build.txt
python -m PyInstaller --clean SOC-Agent.spec

Write-Host ""
Write-Host "Build complete:"
Write-Host (Join-Path $agentRoot "dist\SOC-Agent.exe")
