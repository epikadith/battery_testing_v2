@echo off
setlocal

echo Checking for ADB device...
adb start-server > nul

:: Check if a device is connected and authorized
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

echo --- IMPORTANT ---
echo Temporarily disabling charging to get accurate discharge data.
adb shell dumpsys battery set ac 0
adb shell dumpsys battery set usb 0
echo Charging disabled.
echo.

:: Generate a robust timestamp (YYYY-MM-DD_HH-MM) using WMIC to be independent of system locale
echo Generating timestamp...
for /f "tokens=2 delims==" %%a in ('wmic OS get LocalDateTime /value') do set "dt=%%a"
set "Timestamp=%dt:~0,4%-%dt:~4,2%-%dt:~6,2%_%dt:~8,2%-%dt:~10,2%"

:: Define the log directory structure
set "LogDir=logs\%Timestamp%"

echo Creating log directory: %LogDir%
mkdir "%LogDir%" > nul 2>&1

echo.
echo Collecting batterystats...
adb shell dumpsys batterystats > "%LogDir%\batterystats.txt"
echo   - Saved to %LogDir%\batterystats.txt

echo.
echo Collecting current battery info...
adb shell dumpsys battery > "%LogDir%\battery.txt"
echo   - Saved to %LogDir%\battery.txt

echo.
echo Collecting device info...
(
    echo Model:
    adb shell getprop ro.product.model
    echo.
    echo Android Version:
    adb shell getprop ro.build.version.release
) > "%LogDir%\device_info.txt"
echo   - Saved to %LogDir%\device_info.txt

echo.
echo Collecting package list...
adb shell pm list packages -U > "%LogDir%\packages.txt"
echo   - Saved to %LogDir%\packages.txt

echo.
echo --- IMPORTANT ---
echo Re-enabling charging.
adb shell dumpsys battery reset
echo Charging restored.

echo.
echo Log collection complete.
echo.
endlocal