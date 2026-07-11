@echo off
setlocal

title SOC Sentinel Server

powershell -NoExit -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-SOC-Sentinel.ps1"
if errorlevel 1 (
    echo.
    echo SOC Sentinel failed to start.
    pause
    exit /b 1
)
