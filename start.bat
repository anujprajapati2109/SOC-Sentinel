@echo off
setlocal

title SOC Sentinel Production Server

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
if errorlevel 1 (
    echo.
    echo SOC Sentinel failed to start.
    pause
    exit /b 1
)
