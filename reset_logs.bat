@echo off
setlocal

echo Checking for ADB device...
adb start-server > nul

:: Check if a device is connected and authorized. The 'findstr "device$"' is a
:: robust way to ensure we find a line ending with "device", not just any
:: line containing the word.
adb devices | findstr "device$" > nul
if %errorlevel% neq 0 (
    echo.
    echo ERROR: No authorized Android device found.
    echo Please ensure your phone is connected, USB debugging is enabled,
    echo and you have authorized this computer.
    echo.
    pause
    exit /b 1
)

echo Device found.
echo.
echo Resetting batterystats on the device...
adb shell dumpsys batterystats --reset
echo.
echo Batterystats have been reset. You can now start collecting new logs.
echo.
pause
endlocal