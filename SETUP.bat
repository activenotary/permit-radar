@echo off
title Permit Radar Setup
echo ============================================
echo   PERMIT RADAR - ONE-CLICK SETUP
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
  echo Python is not installed yet. The Microsoft Store will open now.
  echo.
  echo   1. Click INSTALL / GET on the Python page
  echo   2. Wait for it to finish
  echo   3. DOUBLE-CLICK THIS FILE AGAIN
  echo.
  start python
  pause
  exit /b
)

echo [1/6] Python found:
python --version
echo.

echo [2/6] Copying project to C:\dev\permit-radar (outside OneDrive)...
if not exist C:\dev mkdir C:\dev
robocopy "%~dp0." C:\dev\permit-radar /E /NFL /NDL /NJH /NJS >nul
cd /d C:\dev\permit-radar

echo [3/6] Installing required package...
python -m pip install requests --quiet

echo [4/6] Pulling LIVE permits from Chicago + Austin...
python ingest.py

echo [5/6] Tagging and scoring permits...
python enrich.py
python digest.py

echo [6/6] Building your website...
python pseo.py

echo.
echo ============================================
echo   DONE - opening your site in the browser
echo ============================================
start "" "C:\dev\permit-radar\docs\index.html"
start "" "C:\dev\permit-radar\out\digests"
echo.
echo Your project now lives at C:\dev\permit-radar
echo You can close this window.
pause
