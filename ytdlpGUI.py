import os
import sys
import threading
import shutil
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk
from yt_dlp import YoutubeDL

# -----------------------------------------------------------------------------
# Constants & Helpers
# -----------------------------------------------------------------------------
if os.name == 'nt':
    CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW
else:
    CREATE_NO_WINDOW = 0


def find_tool(name, fallback_path=None):
    """
    Locate a tool by name in PATH or fallback location.
    Exits with an error dialog if not found.
    """
    path = shutil.which(name)
    if path:
        return path
    if fallback_path and os.path.exists(fallback_path):
        return fallback_path
    messagebox.showerror(f"{name} Not Found", f"{name} is not installed or not in PATH.")
    sys.exit(1)


def get_videos_folder():
    """
    Return the user's Videos folder on Windows or ~/Videos elsewhere.
    """
    if os.name == 'nt':
        return os.path.join(os.environ.get("USERPROFILE", ""), "Videos")
    return os.path.join(os.path.expanduser("~"), "Videos")

FFMPEG_PATH = find_tool("ffmpeg", r"C:\Program Files\VideoTools\ffmpeg.exe")
videos_dir = get_videos_folder()
DOWNLOAD_DIR = os.path.join(videos_dir, "YT-DLP Downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

BASE_BITRATES = {
    "Original": 1500, "480p": 1000, "720p": 1500,
    "1080p": 2500, "1440p": 4000, "4K": 8000
}
REFERENCE_CRITERION = 23

# -----------------------------------------------------------------------------
# Video Duration via yt_dlp API
# -----------------------------------------------------------------------------
def fetch_video_duration(url):
    """
    Extract metadata and return duration in seconds.
    """
    try:
        with YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return float(info.get('duration', 0))
    except Exception:
        status_label.config(text="Duration fetch failed")
        messagebox.showwarning("Duration Error", "Could not retrieve video duration. Check URL.")
        return 0.0

# -----------------------------------------------------------------------------
# Size Estimation
# -----------------------------------------------------------------------------
def update_estimated_size():
    url = url_entry.get().strip()
    if not url:
        estimated_label.config(text="Estimated Output Size: N/A (enter URL)")
        return

    duration = fetch_video_duration(url)
    if duration <= 0:
        estimated_label.config(text="Estimated Output Size: Unable to determine duration")
        return

    use_discord = discord_var.get()
    res = "720p" if use_discord else resolution_var.get()
    crf = 28 if use_discord else quality_var.get()

    base = BASE_BITRATES.get(res, 1500)
    mult = REFERENCE_CRITERION / crf
    fudge = max(0.7, min(1.0, 1 - ((crf - 18) / 12) * 0.028))

    vb = base * mult * fudge
    ab = 96 if use_discord else 128
    total = vb + ab
    if static_var.get():
        total *= 0.20  # reduce to 20% when static image

    size_mb = (duration * total) / 8000.0
    low, high = size_mb * 0.95, size_mb * 1.25
    estimated_label.config(text=f"Estimated Output Size: {low:.1f}–{high:.1f} MB")


def start_estimation_thread():
    threading.Thread(target=update_estimated_size, daemon=True).start()

# -----------------------------------------------------------------------------
# Download & Convert via yt_dlp API + ffmpeg subprocess
# -----------------------------------------------------------------------------
def download_and_convert(url, filename):
    raw_path = os.path.join(DOWNLOAD_DIR, f"{filename}_raw.mkv")
    final_path = os.path.join(DOWNLOAD_DIR, f"{filename}.mp4")

    if os.path.exists(final_path):
        if not messagebox.askyesno("Exists", f"'{final_path}' exists. Overwrite?"):
            status_label.config(text="Canceled by user")
            return

    try:
        status_label.config(text="Downloading video...")
        progress_bar.start()
        ydl_opts = {
            'format': 'bestvideo*+bestaudio/best',
            'merge_output_format': 'mkv',
            'outtmpl': raw_path,
        }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        status_label.config(text="Converting with FFmpeg...")
        use_discord = discord_var.get()
        target_res = "720p" if use_discord else resolution_var.get()
        if target_res == "Original":
            vf = "scale=iw:ih:flags=lanczos"
        elif target_res == "4K":
            vf = "scale=3840:2160:flags=lanczos"
        else:
            h = int(target_res.replace("p", ""))
            vf = f"scale={int(h*16/9)}:{h}:flags=lanczos"

        crf_val = "28" if use_discord else str(quality_var.get())
        audio_br = "96k" if use_discord else "128k"

        ff_cmd = [
            FFMPEG_PATH, '-y', '-i', raw_path,
            '-c:v', 'libx264', '-crf', crf_val, '-preset', 'slow',
            '-vf', vf,
            '-c:a', 'aac', '-b:a', audio_br,
            final_path
        ]
        subprocess.run(ff_cmd, check=True, creationflags=CREATE_NO_WINDOW)

        if os.path.exists(raw_path):
            os.remove(raw_path)

        status_label.config(text="Done")
        messagebox.showinfo("Success", f"Saved to:\n{final_path}")
    except Exception as e:
        status_label.config(text="Error during download/convert")
        messagebox.showerror("Processing Error", str(e))
    finally:
        progress_bar.stop()


def start_download():
    url = url_entry.get().strip()
    name = filename_entry.get().strip()
    if not url:
        messagebox.showwarning("Input Required", "Please enter a video URL.")
        return
    if not name:
        messagebox.showwarning("Input Required", "Please enter an output filename.")
        return
    safe = "".join(c for c in name if c.isalnum() or c in " _-").rstrip()
    threading.Thread(target=download_and_convert, args=(url, safe), daemon=True).start()

# -----------------------------------------------------------------------------
# UI Setup
# -----------------------------------------------------------------------------
def on_discord_toggle(*_):
    if discord_var.get():
        resolution_menu.config(state="disabled")
        quality_slider.config(state="disabled")
        resolution_var.set("720p")
    else:
        resolution_menu.config(state="normal")
        quality_slider.config(state="normal")
    start_estimation_thread()

root = tk.Tk()
root.title("Video Downloader & Converter")
root.resizable(False, False)

# URL Input
tk.Label(root, text="Enter Video URL:").pack(anchor="w", padx=10, pady=(10,0))
url_entry = tk.Entry(root, width=60)
url_entry.pack(padx=10, pady=4)

# Filename Input
tk.Label(root, text="Enter Output Filename (no extension):").pack(anchor="w", padx=10)
filename_entry = tk.Entry(root, width=60)
filename_entry.pack(padx=10, pady=4)

# Resolution
tk.Label(root, text="Select Resolution:").pack(anchor="w", padx=10)
resolution_options = ["Original","480p","720p","1080p","1440p","4K"]
resolution_var = tk.StringVar(value="720p")
resolution_menu = tk.OptionMenu(root, resolution_var, *resolution_options, command=lambda _: start_estimation_thread())
resolution_menu.pack(padx=10, pady=4)

# Estimate
tk.Button(root, text="Estimate File Size", command=start_estimation_thread).pack(padx=10)
estimated_label = tk.Label(root, text="Estimated Output Size: N/A")
estimated_label.pack(padx=10, pady=4)

# Static Image Mode
static_var = tk.BooleanVar()
tk.Checkbutton(root, text="Static Image (Low Motion) - reduces bitrate", variable=static_var, command=start_estimation_thread).pack(anchor="w", padx=10, pady=4)

# Quality Slider
tk.Label(root, text="Quality (High Quality ←→ Smaller File):").pack(anchor="w", padx=10)
frame = tk.Frame(root)
frame.pack(fill="x", padx=10)
tk.Label(frame, text="High Quality").pack(side="left")
quality_var = tk.DoubleVar(value=23)
quality_slider = ttk.Scale(frame, from_=30, to=18, variable=quality_var, command=lambda _: None)
quality_slider.pack(side="left", fill="x", expand=True, padx=5)
quality_value_label = tk.Label(frame, text=lambda: f"{quality_var.get():.0f}")
quality_value_label.pack(side="left")

# Discord Mode
discord_var = tk.BooleanVar()
tk.Checkbutton(root, text="Discord Optimized Mode - suitable for 8MB limit", variable=discord_var, command=start_estimation_thread).pack(anchor="w", padx=10, pady=4)
discord_var.trace_add("write", on_discord_toggle)

# Download Button
tk.Button(root, text="Download & Convert", command=start_download).pack(padx=10, pady=6)
progress_bar = ttk.Progressbar(root, mode='indeterminate', length=350)
progress_bar.pack(padx=10)
status_label = tk.Label(root, text="Idle - Ready to start")
status_label.pack(padx=10, pady=6)

root.mainloop()