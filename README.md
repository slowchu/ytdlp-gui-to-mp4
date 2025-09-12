# ytdlp-gui-to-mp4

A lightweight, open-source graphical interface for downloading and converting videos from supported platforms using [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [FFmpeg](https://ffmpeg.org/) into Discord friendly .MP4 files

Designed to make downloading and converting videos simple, fast, and Discord-friendly — no terminal needed.

### Strongly suggest running the [batchfile](https://github.com/slowchu/ytdlp-gui-to-mp4/releases/download/v1.6/install-tools.bat) to install FFMPEG and yt-dlp automatically for easiest compatibility. Keep the file if windows asks you to delete it. 

---
[Release v1.7](https://github.com/slowchu/ytdlp-gui-to-mp4/releases/tag/v1.7)

Fixed:
 
403 errors caused by yt-dlp using ios as the default method, now it avoids this if it can. This was the root issue of the raw files being "empty", and prior to this, updating yt-dlp would fix this. After multiple attempts at yt-dlp updates not fixing this issue this time, I realized from a bug report on yt-dlp what was going on.

Changed:

packaged as a onedir for two reasons, 1: allows the program to open faster 2: stop being flagged as malicious software so often

Run install-tools.bat as an administration, extract files from the zip provided to anywhere, launch yt-dlp gui.exe.


![image](https://github.com/user-attachments/assets/9a8b20f4-6760-40a7-ab39-f55a788abddd)





## ✅ Features

- Paste any yt-dlp supported video platform URL 
- Choose your output filename
- Adjust video quality using an intuitive slider and resolution drop down
- “Discord Optimized” mode, attempts to output at low settings in an attempt to optimize size for non-nitro file limits/mobile usage:
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


## ⚙️ Optional: Setup Script (`install-tools.bat`)

This project includes a helpful batch script: `install-tools.bat`

### 🔧 What It Does:
- Downloads the latest versions of:
  - [yt-dlp.exe](https://github.com/yt-dlp/yt-dlp)
  - [ffmpeg.exe](https://www.gyan.dev/ffmpeg/builds/)
- Adds both tools to your system `PATH`
  - This allows you to run `yt-dlp` and `ffmpeg` from anywhere
- Sets everything up so the GUI works out of the box

### 📌 When to Use It:
- If the GUI doesn’t work because `yt-dlp` or `ffmpeg` is missing

### 🛠 How to Use:
1. Right-click the file `install-tools.bat`
2. Choose **Run as Administrator**
3. Wait for it to finish downloading and updating your system

> 💡 You may need to restart your terminal or PC after running it for PATH changes to apply.


### Disclaimer

This tool uses FFmpeg, a free and open-source multimedia framework licensed under the GNU General Public License (GPL) or Lesser GPL (LGPL), depending on the build.

FFmpeg is not distributed with this project. To learn more or get the latest version, visit: https://ffmpeg.org

This tool uses:

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — a powerful command-line video downloader (Unlicense)
- [FFmpeg](https://ffmpeg.org) a free and open-source multimedia framework licensed under the GNU General Public License (GPL) or Lesser GPL (LGPL), depending on the build.


These tools are not bundled or distributed with the project. Visit their official pages for more information. 

This project optionally uses a batch file (`install-tools.bat`) to download and configure:

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — a command-line video downloader (licensed under The Unlicense)
- [FFmpeg](https://ffmpeg.org) — a multimedia converter (licensed under GPL/LGPL)

The script downloads these tools from their official sources and installs them to a local tools directory (e.g. `C:\Program Files\VideoTools`). It also adds them to your system PATH so the GUI can access them.

These tools are not created or maintained by this project. They are used as external dependencies. Running the batch file is entirely optional — you may install and configure these tools manually if preferred.
