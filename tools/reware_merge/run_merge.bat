@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Re-Ware: merging product list + Blancco report...
echo (includes laptop battery tier: 70%%+ / Under 70%%)
echo.

py --version >nul 2>&1
if errorlevel 1 (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python is not installed or not on PATH.
        pause
        exit /b 1
    )
    set PY=python
) else (
    set PY=py
)

if exist "%~dp0requirements.txt" (
    %PY% -m pip install -q -r "%~dp0requirements.txt"
) else (
    echo requirements.txt not found — installing pandas openpyxl directly...
    %PY% -m pip install -q pandas openpyxl
)
if errorlevel 1 (
    echo ERROR: pip install failed. Try: %PY% -m pip install pandas openpyxl
    pause
    exit /b 1
)

%PY% "%~dp0merge_receipt_blancco.py"
set EXITCODE=%ERRORLEVEL%
echo.
if %EXITCODE% NEQ 0 (
    echo Merge finished with warnings ^(some serials failed Blancco^). Check the popup/console list.
) else (
    echo All rows matched Blancco. Review the .xlsx then upload SUCCESS rows to Odoo.
)
pause
exit /b %EXITCODE%
