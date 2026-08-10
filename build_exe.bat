@echo off
REM Builds a single-file Windows .exe with the ideaForge icon.
REM Run this on Windows (PyInstaller builds are platform-specific —
REM you can't build a .exe from Linux/Mac).
python -m pip install pyinstaller
python -m PyInstaller ^
    --name "ThrustDashboard" ^
    --windowed ^
    --onefile ^
    --icon "assets\app_icon.ico" ^
    --add-data "assets;assets" ^
    main.py
echo.
echo Done. Find ThrustDashboard.exe in the dist\ folder.
pause