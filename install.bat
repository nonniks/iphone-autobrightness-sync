@echo off
echo ========================================
echo    BrightnessSync Installation
echo ========================================
echo.

set "INSTALL_DIR=%LOCALAPPDATA%\BrightnessSync"

echo Creating installation folder...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo Copying files...
copy "dist\BrightnessSync.exe" "%INSTALL_DIR%\" > nul

echo Creating desktop shortcut...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\BrightnessSync.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\BrightnessSync.exe'; $Shortcut.Save()"

echo.
echo Installation complete!
echo Location: %INSTALL_DIR%
echo Desktop shortcut created
echo.
echo Launch now? (Y/N)
set /p choice=
if /i "%choice%"=="Y" start "" "%INSTALL_DIR%\BrightnessSync.exe"

pause