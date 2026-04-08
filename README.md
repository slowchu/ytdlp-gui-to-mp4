# ytdlp-gui-to-mp4

A lightweight, open-source graphical interface for downloading and converting videos from supported platforms using [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [FFmpeg](https://ffmpeg.org/) into Discord friendly .MP4 files

Designed to make downloading and converting videos simple, fast, and Discord-friendly — no terminal needed.

> ⚠️ **Important:** YouTube now requires a JavaScript runtime (Deno) and challenge solver scripts to download videos. If you haven't set these up, **run the batch file first** — it handles everything automatically. Without it, downloads will fail with "n challenge solving failed" errors.

### 🚀 Quick Start

1. Download and run [install-tools.bat](https://github.com/slowchu/ytdlp-gui-to-mp4/releases/download/v1.8/install-tools.bat) **as Administrator**
2. Restart your terminal or PC
3. Launch `yt-dlp gui.exe`

That's it. The batch file installs yt-dlp, FFmpeg, Deno, and configures everything automatically.

---
[Release v1.8](https://github.com/slowchu/ytdlp-gui-to-mp4/releases/tag/v1.8)

Fixed:
- Fixed "No raw file found" error when downloading videos with pre-merged formats
- Fixed Videos folder detection on Windows (was silently failing since v1.0)
- Fixed CRF value being passed as a float which some FFmpeg builds reject
- Fixed scale filter assuming 16:9 aspect ratio — now preserves source aspect ratio

Changed:
- Replaced two-command download fallback with single command using yt-dlp's recommended format string (`bv*+ba/b`)
- Added `--extractor-args "youtube:player_client=web"` to avoid iOS client 403 errors
- **install-tools.bat now installs [Deno](https://deno.com)** (required JavaScript runtime for YouTube downloads)
- **install-tools.bat now creates yt-dlp config** with `--remote-components ejs:github` for automatic challenge solver script downloads

---

Run install-tools.bat as an administrator, extract files from the zip provided to anywhere, launch yt-dlp gui.exe.


![image](https://github.com/user-attachments/assets/9a8b20f4-6760-40a7-ab39-f55a788abddd)


## ✅ Features

- Paste any yt-dlp supported video platform URL
- Choose your output filename
- Adjust video quality using an intuitive slider and resolution drop down
- "Discord Optimized" mode, attempts to output at low settings in an attempt to optimize size for non-nitro file limits/mobile usage:
  - 720p max resolution
  - CRF 28 for size reduction
  - 96kbps audio
- MP4 output (H.264 + 128k or 96k AAC)
- Saves files to your system's `Videos/YT-DLP Downloads` folder
- Filesize estimator + Static Image modifier (makes estimate more accurate for videos with static images, does **not** control quality)
- Clean GUI, no terminal required

---

## 📦 Requirements (if running from .py source)

- Python 3.7 or later
- `yt-dlp` installed (`yt-dlp.exe` must be in the same folder or system PATH)
- `ffmpeg` installed (`ffmpeg.exe` must be in the same folder or system PATH)
- `deno` installed and in system PATH ([download](https://deno.com))
- yt-dlp config with `--remote-components ejs:github` (or `yt-dlp-ejs` package installed)


## ⚙️ Recommended: Setup Script (`install-tools.bat`)

This project includes a setup script that handles all dependencies: `install-tools.bat`

**If you're new to yt-dlp or haven't configured it for YouTube's latest requirements, this is the easiest way to get everything working.** Running it is strongly recommended over manual setup.

### 🔧 What It Does:
- Downloads the latest versions of:
  - [yt-dlp.exe](https://github.com/yt-dlp/yt-dlp)
  - [ffmpeg.exe](https://www.gyan.dev/ffmpeg/builds/)
- Installs [Deno](https://deno.com) — a JavaScript runtime now **required** by yt-dlp to solve YouTube's anti-bot challenges
- Creates a yt-dlp config file that enables automatic download of challenge solver scripts (EJS)
- Adds all tools to your system `PATH`
- Sets everything up so the GUI works out of the box

### 📌 When to Use It:
- **First time setup** — run this before anything else
- If downloads fail with "n challenge solving failed" or "Requested format is not available" errors
- If `yt-dlp`, `ffmpeg`, or `deno` is missing
- To update yt-dlp and ffmpeg to the latest versions

### 🛠 How to Use:
1. Right-click the file `install-tools.bat`
2. Choose **Run as Administrator**
3. Wait for it to finish downloading and updating your system

> 💡 You may need to restart your terminal or PC after running it for PATH changes to apply.

### 🔧 Manual Setup (Advanced)

If you prefer not to use the batch file, you'll need to set up the following yourself:

1. Install [yt-dlp](https://github.com/yt-dlp/yt-dlp/releases/latest) and [FFmpeg](https://www.gyan.dev/ffmpeg/builds/) and add them to your PATH
2. Install [Deno](https://deno.com) (or Node.js 20+) and add it to your PATH
3. Create `%APPDATA%\yt-dlp\config.txt` with the line: `--remote-components ejs:github`

Without steps 2 and 3, YouTube downloads will not work.


### Disclaimer

This tool uses FFmpeg, a free and open-source multimedia framework licensed under the GNU General Public License (GPL) or Lesser GPL (LGPL), depending on the build.

FFmpeg is not distributed with this project. To learn more or get the latest version, visit: https://ffmpeg.org

This tool uses:

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — a powerful command-line video downloader (Unlicense)
- [FFmpeg](https://ffmpeg.org) — a free and open-source multimedia framework (GPL/LGPL)
- [Deno](https://deno.com) — a JavaScript runtime (MIT)

These tools are not bundled or distributed with the project. Visit their official pages for more information.

This project optionally uses a batch file (`install-tools.bat`) to download and configure:

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — a command-line video downloader (licensed under The Unlicense)
- [FFmpeg](https://ffmpeg.org) — a multimedia converter (licensed under GPL/LGPL)
- [Deno](https://deno.com) — a JavaScript runtime (licensed under MIT)

The script downloads these tools from their official sources and installs them to a local tools directory (e.g. `C:\Program Files\VideoTools`). It also adds them to your system PATH so the GUI can access them.

These tools are not created or maintained by this project. They are used as external dependencies. Running the batch file is entirely optional — you may install and configure these tools manually if preferred.
