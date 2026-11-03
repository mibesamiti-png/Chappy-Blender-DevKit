@echo off
cd /d "%~dp0"
python -m cbdk scan input_sources_private --output reports/latest
if errorlevel 1 echo Scan failed. Check Python 3.11+ and source directory.
pause
