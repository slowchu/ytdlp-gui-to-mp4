@echo off
setlocal enabledelayedexpansion

echo ========================================
echo  yt-dlp + FFmpeg Installer for Windows
echo ========================================

REM Set installation directory
set "TOOL_DIR=%ProgramFiles%\VideoTools"
echo Creating installation folder: %TOOL_DIR%
mkdir "%TOOL_DIR%" >nul 2>&1

REM Download yt-dlp.exe
echo Downloading yt-dlp.exe...
curl -L -o "%TOOL_DIR%\yt-dlp.exe" https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe
if errorlevel 1 (
    echo Error downloading yt-dlp.exe. Exiting.
    pause
    exit /b 1
)

REM Download ffmpeg.exe (static build zip)
echo Downloading ffmpeg release...
curl -L -o "%TEMP%\ffmpeg.zip" https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
if errorlevel 1 (
    echo Error downloading ffmpeg.zip. Exiting.
    pause
    exit /b 1
)

REM Extract ffmpeg.exe using PowerShell
echo Extracting ffmpeg.exe...
powershell -Command "Expand-Archive -Force '%TEMP%\ffmpeg.zip' '%TEMP%\ffmpeg'"
if errorlevel 1 (
    echo Error extracting ffmpeg.zip. Exiting.
    pause
    exit /b 1
)

REM Find ffmpeg.exe in the extracted folder and copy it to TOOL_DIR
set "FFMPEG_FOUND=0"
for /r "%TEMP%\ffmpeg" %%F in (ffmpeg.exe) do (
    copy "%%F" "%TOOL_DIR%\ffmpeg.exe" >nul
    if not errorlevel 1 (
        set "FFMPEG_FOUND=1"
        goto :found_ffmpeg
    )
)

:found_ffmpeg
if "%FFMPEG_FOUND%"=="0" (
    echo ffmpeg.exe was not found in the extracted files. Exiting.
    pause
    exit /b 1
)

REM Cleanup temporary files
rd /s /q "%TEMP%\ffmpeg"
del "%TEMP%\ffmpeg.zip"

REM Update System PATH
echo Adding %TOOL_DIR% to the system PATH...
setx /M PATH "%PATH%;%TOOL_DIR%" >nul 2>&1
if errorlevel 1 (
    echo Failed to update system PATH. Please run this script as Administrator.
    pause
    exit /b 1
)

echo.
echo ✅ Installation complete!
echo Tools installed to: %TOOL_DIR%
echo System PATH updated. You may need to restart your terminal or PC.
echo.
pause
