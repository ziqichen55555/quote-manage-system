@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Re-Ware: merging product list + Blancco report...
echo (includes laptop battery tier: 70%%+ / Under 70%%)
echo.

set "ENGINE=%~dp0merge_receipt_blancco.py"
set "REPO_ENGINE=c:\Users\User\quote-management-system\quote-manage-system\tools\reware_merge\merge_receipt_blancco.py"
if exist "%REPO_ENGINE%" (
    echo Syncing merge_receipt_blancco.py from repo...
    copy /Y "%REPO_ENGINE%" "%ENGINE%" >nul
)
if not exist "%ENGINE%" (
    echo.
    echo ERROR: merge_receipt_blancco.py is missing in this folder.
    echo run_merge.bat only starts Python; the merge program must be merge_receipt_blancco.py
    echo Keep both files together. Copy from tools\reware_merge in the git repo.
    echo.
    pause
    exit /b 1
)

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

%PY% "%ENGINE%"
set EXITCODE=%ERRORLEVEL%
echo.
if %EXITCODE% NEQ 0 (
    echo Merge finished with warnings ^(see import-not-ready report^).
    echo Still upload MERGED import-all CSV if it has your devices ^(Pass + CMOS Fail^).
) else (
    echo OK. Upload MERGED import-all CSV to Odoo ^(NOT import-ready — that file has Pass only^).
)
pause
exit /b %EXITCODE%
