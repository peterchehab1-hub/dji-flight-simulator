@echo off
title AeroSim Pro - DJI Flight Simulator Launcher
echo ================================================================
echo          AeroSim Pro | 3D DJI Drone Simulator
echo ================================================================
echo.
echo [1/2] Starting DJI Remote Automatic Discovery Bridge...
start /b "" python dji_rc_bridge.py

echo [2/2] Opening Simulator in your Web Browser...
timeout /t 2 >nul
start "" "http://localhost:8080/index.html"

echo.
echo ================================================================
echo  * Bridge is running! Turn on your DJI RC and connect it to Wi-Fi.
echo  * The simulator will automatically detect and connect to your RC.
echo  * To stop the bridge, close this window.
echo ================================================================
echo.
pause
