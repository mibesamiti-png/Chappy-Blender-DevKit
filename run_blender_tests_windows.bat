@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo   Chappy Blender DevKit - Windows One-Click Blender Tests
echo ============================================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows_run_blender_tests.ps1" %*
set "CBDK_EXIT=%ERRORLEVEL%"
echo.
if "%CBDK_EXIT%"=="0" (
  echo [SUCCESS] CBDK tests completed. Reports are under reports\latest\.
) else (
  echo [FAILED] Check the logs under reports\latest\.
)
echo.
pause
exit /b %CBDK_EXIT%
