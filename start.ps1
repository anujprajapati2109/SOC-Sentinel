$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServerDir = Join-Path $ProjectRoot "soc_server"
$VenvDir = Join-Path $ProjectRoot ".venv"
$PythonPath = Join-Path $VenvDir "Scripts\python.exe"
$WaitressPath = Join-Path $VenvDir "Scripts\waitress-serve.exe"
$EnvPath = Join-Path $ProjectRoot ".env"

if (Test-Path -LiteralPath $EnvPath) {
    Get-Content -LiteralPath $EnvPath | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
        }
    }
}

$env:SOC_SENTINEL_ENV = if ($env:SOC_SENTINEL_ENV) { $env:SOC_SENTINEL_ENV } else { "production" }
$env:HOST = if ($env:HOST) { $env:HOST } else { "127.0.0.1" }
$env:PORT = if ($env:PORT) { $env:PORT } else { "5000" }

if (-not (Test-Path -LiteralPath $PythonPath)) {
    python -m venv $VenvDir
}

& $PythonPath -m pip install --upgrade pip
& $PythonPath -m pip install -r (Join-Path $ServerDir "requirements.txt")

Set-Location -LiteralPath $ServerDir
& $WaitressPath --host=$env:HOST --port=$env:PORT wsgi:application
