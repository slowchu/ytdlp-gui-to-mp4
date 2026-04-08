@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   yt-dlp + FFmpeg + Deno Installer
echo ========================================

REM Set installation directory
set "TOOL_DIR=%ProgramFiles%\VideoTools"
echo Creating installation folder: %TOOL_DIR%
mkdir "%TOOL_DIR%" >nul 2>&1

REM ---- yt-dlp ----
echo.
echo Downloading yt-dlp.exe...
curl -L -o "%TOOL_DIR%\yt-dlp.exe" https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe
if errorlevel 1 (
    echo Error downloading yt-dlp.exe. Exiting.
    pause
    exit /b 1
)

REM ---- FFmpeg ----
echo.
echo Downloading ffmpeg release...
curl -L -o "%TEMP%\ffmpeg.zip" https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
if errorlevel 1 (
    echo Error downloading ffmpeg.zip. Exiting.
    pause
    exit /b 1
)

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

REM Cleanup temporary ffmpeg files
rd /s /q "%TEMP%\ffmpeg" >nul 2>&1
del "%TEMP%\ffmpeg.zip" >nul 2>&1

REM ---- Deno (required for yt-dlp YouTube JS challenges) ----
echo.
echo Checking for Deno...
where deno >nul 2>&1
if %errorlevel%==0 (
    echo Deno is already installed, skipping.
) else (
    echo Installing Deno via PowerShell...
    powershell -Command "irm https://deno.land/install.ps1 | iex"
    if errorlevel 1 (
        echo.
        echo Warning: Deno auto-install failed.
        echo Please install Deno manually from https://deno.com
        echo or run: winget install DenoLand.Deno
        echo.
    ) else (
        echo Deno installed successfully.
    )
)

REM ---- yt-dlp config for EJS script downloads ----
echo.
echo Setting up yt-dlp config for YouTube JS challenge scripts...
set "YTDLP_CONFIG_DIR=%APPDATA%\yt-dlp"
mkdir "%YTDLP_CONFIG_DIR%" >nul 2>&1

REM Check if config already has remote-components setting
if exist "%YTDLP_CONFIG_DIR%\config.txt" (
    findstr /C:"--remote-components" "%YTDLP_CONFIG_DIR%\config.txt" >nul 2>&1
    if !errorlevel!==0 (
        echo yt-dlp config already has remote-components set, skipping.
    ) else (
        echo.>>"%YTDLP_CONFIG_DIR%\config.txt"
        echo --remote-components ejs:github>>"%YTDLP_CONFIG_DIR%\config.txt"
        echo Added remote-components to existing yt-dlp config.
    )
) else (
    echo --remote-components ejs:github>"%YTDLP_CONFIG_DIR%\config.txt"
    echo Created yt-dlp config with remote-components.
)

REM ---- Update System PATH ----
echo.
echo Adding %TOOL_DIR% to the system PATH...
setx /M PATH "%PATH%;%TOOL_DIR%" >nul 2>&1
if errorlevel 1 (
    echo Failed to update system PATH. Please run this script as Administrator.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Installation complete!
echo ========================================
echo Tools installed to: %TOOL_DIR%
echo System PATH updated.
echo.
echo Installed:
echo   - yt-dlp.exe
echo   - ffmpeg.exe
echo   - Deno (JS runtime for YouTube)
echo   - yt-dlp config (auto-downloads EJS scripts)
echo.
echo You may need to restart your terminal or PC.
echo.
pause
