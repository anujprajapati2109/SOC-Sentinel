$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServerDir = Join-Path $ProjectRoot "soc_server"
$PythonPath = Join-Path $ServerDir ".venv\Scripts\python.exe"
$LogPath = Join-Path $ServerDir "server_startup.log"

Set-Location -LiteralPath $ServerDir
"$(Get-Date -Format s) launcher-started" | Out-File -FilePath $LogPath -Encoding ASCII

if (-not (Test-Path -LiteralPath $PythonPath)) {
    Write-Host "Creating Python virtual environment..."
    "$(Get-Date -Format s) creating-venv" | Out-File -FilePath $LogPath -Append -Encoding ASCII
    python -m venv .venv
}

Write-Host "Checking server dependencies..."
"$(Get-Date -Format s) checking-dependencies" | Out-File -FilePath $LogPath -Append -Encoding ASCII
& $PythonPath -c "import flask, flask_sqlalchemy, sqlalchemy, psutil" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing server dependencies..."
    "$(Get-Date -Format s) installing-dependencies" | Out-File -FilePath $LogPath -Append -Encoding ASCII
    & $PythonPath -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install server dependencies."
    }
}

$env:FLASK_CONFIG = "production"

Write-Host "Starting SOC Sentinel server..."
Write-Host "URL: http://127.0.0.1:5000"
"$(Get-Date -Format s) starting-flask" | Out-File -FilePath $LogPath -Append -Encoding ASCII

Start-Job -ScriptBlock {
    Start-Sleep -Seconds 2
    Start-Process "http://127.0.0.1:5000"
} | Out-Null

& $PythonPath app.py
