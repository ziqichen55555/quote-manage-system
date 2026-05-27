@echo off
REM Independent Cloudflare Quick Tunnel launcher.
REM Run this by double-clicking, or:  start "" scripts\run-tunnel.cmd
REM This window is INDEPENDENT of Cursor — closing Cursor will NOT kill it.
REM Close this black window to stop the tunnel.

cd /d "%~dp0\.."
title Cloudflare Tunnel (quote-manage-system)
echo ====================================================
echo Cloudflare Quick Tunnel
echo Local target: http://localhost:8070
echo Watch for a line containing trycloudflare.com below.
echo Closing this window stops the tunnel.
echo ====================================================
echo.
cloudflared.exe tunnel --url http://localhost:8070 > cloudflared.log 2>&1
echo.
echo Tunnel exited. Press any key to close.
pause >nul
