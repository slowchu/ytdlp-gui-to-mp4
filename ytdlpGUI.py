import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import threading
import ctypes
from tkinter import ttk
import shutil
import math

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

def get_windows_videos_folder():
    try:
        FOLDERID_Videos = '{18989B1D-99B5-455B-841C-AB7C74E4DDFC}'
        SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
        SHGetKnownFolderPath.argtypes = [
            ctypes.c_char_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_wchar_p)
        ]
        path_ptr = ctypes.c_wchar_p()
        result = SHGetKnownFolderPath(FOLDERID_Videos.encode('utf-8'), 0, None, ctypes.byref(path_ptr))
        return path_ptr.value
    except Exception:
        return None

FFMPEG_PATH = shutil.which("ffmpeg")
if not FFMPEG_PATH:
    fallback_ffmpeg = r"C:\Program Files\VideoTools\ffmpeg.exe"
    if os.path.exists(fallback_ffmpeg):
        FFMPEG_PATH = fallback_ffmpeg
    else:
        messagebox.showerror("FFmpeg Not Found", "FFmpeg is not installed or not in PATH.")
        exit()

YT_DLP_PATH = shutil.which("yt-dlp")
if not YT_DLP_PATH:
    fallback_ytdlp = r"C:\Program Files\VideoTools\yt-dlp.exe"
    if os.path.exists(fallback_ytdlp):
        YT_DLP_PATH = fallback_ytdlp
    else:
        messagebox.showerror("yt-dlp Not Found", "yt-dlp is not installed or not in PATH.")
        exit()

videos_dir = get_windows_videos_folder()
if not videos_dir:
    videos_dir = os.path.join(os.path.expanduser("~"), "Videos")

DOWNLOAD_DIR = os.path.join(videos_dir, "YT-DLP Downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

base_bitrate_dict = {
    "Original": 1500,
    "480p": 1000,
    "720p": 1500,
    "1080p": 2500,
    "1440p": 4000,
    "4K": 8000
}
reference_quality = 23

def fetch_video_duration(url):
    try:
        result = subprocess.run(
            [YT_DLP_PATH, "--print", "duration", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            creationflags=CREATE_NO_WINDOW
        )
        return float(result.stdout.strip())
    except Exception:
        return 0

def update_estimated_size():
    url = url_entry.get().strip()
    if not url:
        estimated_label.config(text="Estimated Output Size: N/A (enter URL)")
        return

    duration = fetch_video_duration(url)
    if duration <= 0:
        estimated_label.config(text="Estimated Output Size: Unable to determine duration")
        return

    res = resolution_var.get() if not discord_var.get() else "720p"
    base_bitrate = base_bitrate_dict.get(res, 1500)
    crf = 28 if discord_var.get() else quality_var.get()

    multiplier = reference_quality / crf
    fudge_scaling = 0.028
    fudge = 1 - ((crf - 18) / 12) * fudge_scaling
    fudge = max(0.7, min(fudge, 1.0))

    estimated_video_bitrate = base_bitrate * multiplier * fudge
    audio_bitrate = 96 if discord_var.get() else 128
    total_bitrate = estimated_video_bitrate + audio_bitrate

    # More aggressive fudge when Static Image is checked
    if static_var.get():
        total_bitrate *= 0.20

    size_mb = (duration * total_bitrate) / 8000.0
    low = size_mb * 0.95
    high = size_mb * 1.25
    estimated_label.config(text=f"Estimated Output Size: {low:.1f} MB - {high:.1f} MB")

def start_estimation_thread():
    threading.Thread(target=update_estimated_size, daemon=True).start()

def try_download(cmd):
    try:
        subprocess.run(cmd, check=True, creationflags=CREATE_NO_WINDOW)
        return True
    except subprocess.CalledProcessError:
        return False

def download_and_convert(url, filename):
    # Build raw and final paths first, so we can check duplicates
    raw_path_base = os.path.join(DOWNLOAD_DIR, f"{filename}_raw")
    raw_path = raw_path_base + ".mkv"  # We'll merge everything into an mkv
    final_path = os.path.join(DOWNLOAD_DIR, f"{filename}.mp4")

    # DUPLICATE NAME CHECK (before starting progress bar)
    if os.path.exists(final_path):
        answer = messagebox.askyesno(
            "Duplicate Name Detected",
            f"'{final_path}' already exists.\n\nDo you want to overwrite it?"
        )
        if not answer:
            status_label.config(text="Canceled")
            return  # Stop here, don't download or convert

    try:
        # If we get here, user said "Yes" or file doesn't exist
        status_label.config(text="Downloading Video...")
        progress_bar.start()

        # 1) Try bestvideo*+bestaudio
        ytdlp_cmd_1 = [
            YT_DLP_PATH,
            "-f", "bestvideo*+bestaudio",
            "--merge-output-format", "mkv",
            "-o", raw_path,
            url
        ]

        # 2) Fallback: best
        ytdlp_cmd_2 = [
            YT_DLP_PATH,
            "-f", "best",
            "--merge-output-format", "mkv",
            "-o", raw_path,
            url
        ]

        if not try_download(ytdlp_cmd_1):
            if not try_download(ytdlp_cmd_2):
                raise Exception("yt-dlp failed to download the video with all attempted formats.")

        status_label.config(text="Converting Video...")

        res = resolution_var.get() if not discord_var.get() else "720p"
        if res == "Original":
            scale_filter = "scale=iw:ih:flags=lanczos"
        elif res == "4K":
            scale_filter = "scale=3840:2160:flags=lanczos"
        else:
            width = int(int(res.replace("p", "")) * 16 / 9)
            height = int(res.replace("p", ""))
            scale_filter = f"scale={width}:{height}:flags=lanczos"

        crf_value = "28" if discord_var.get() else str(quality_var.get())
        audio_bitrate = "96k" if discord_var.get() else "128k"

        # Add '-y' to overwrite without FFmpeg prompting again
        ffmpeg_cmd = [
            FFMPEG_PATH,
            "-y",
            "-i", raw_path,
            "-c:v", "libx264",
            "-crf", crf_value,
            "-preset", "slow",
            "-vf", scale_filter,
            "-c:a", "aac",
            "-b:a", audio_bitrate,
            final_path
        ]
        subprocess.run(ffmpeg_cmd, check=True, creationflags=CREATE_NO_WINDOW)

        if os.path.exists(raw_path):
            os.remove(raw_path)

        status_label.config(text="Done")
        messagebox.showinfo("Success", f"Saved to:\n{final_path}")
    except subprocess.CalledProcessError as e:
        status_label.config(text="Error")
        messagebox.showerror("Error", f"Command failed:\n\n{e}")
    except Exception as ex:
        status_label.config(text="Error")
        messagebox.showerror("Unexpected Error", str(ex))
    finally:
        progress_bar.stop()

def start_download():
    url = url_entry.get().strip()
    filename = filename_entry.get().strip()
    if not url:
        messagebox.showwarning("Missing URL", "Please enter a video platform URL.")
        return
    if not filename:
        messagebox.showwarning("Missing Filename", "Please enter a filename.")
        return
    filename = "".join(c for c in filename if c.isalnum() or c in (' ', '_', '-')).rstrip()
    threading.Thread(target=download_and_convert, args=(url, filename), daemon=True).start()

def on_discord_toggle(*args):
    if discord_var.get():
        resolution_menu.config(state="disabled")
        quality_slider.config(state="disabled")
        resolution_var.set("720p")
    else:
        resolution_menu.config(state="normal")
        quality_slider.config(state="normal")
    start_estimation_thread()

def update_quality_label(val=None):
    quality_value_label.config(text=f"{quality_var.get():.0f}")

root = tk.Tk()
root.title("Video Downloader & Converter")
root.resizable(False, False)

tk.Label(root, text="Video Platform URL:").pack(pady=(10, 0))
url_entry = tk.Entry(root, width=60)
url_entry.pack(pady=(0, 10))

tk.Label(root, text="Output Filename (no extension):").pack()
filename_entry = tk.Entry(root, width=60)
filename_entry.pack(pady=(0, 10))

tk.Label(root, text="Select Resolution:").pack()
resolution_options = ["Original", "480p", "720p", "1080p", "1440p", "4K"]
resolution_var = tk.StringVar(root)
resolution_var.set("720p")
resolution_menu = tk.OptionMenu(root, resolution_var, *resolution_options, command=lambda _: start_estimation_thread())
resolution_menu.pack(pady=(0, 10))

tk.Button(root, text="Estimate File Size", command=start_estimation_thread).pack(pady=(0, 5))
estimated_label = tk.Label(root, text="Estimated Output Size: N/A")
estimated_label.pack(pady=(0, 5))

static_var = tk.BooleanVar()
static_checkbox = tk.Checkbutton(root, text="Static Image (Less Motion)", variable=static_var, command=start_estimation_thread)
static_checkbox.pack(pady=(0, 10))

tk.Label(root, text="Video Quality Scale: (Low Quality - High Quality)").pack()
slider_frame = tk.Frame(root)
slider_frame.pack(fill="x", padx=10)
tk.Label(slider_frame, text="(Higher value = Smaller File)").pack(side="left", padx=(15, 5))

quality_var = tk.DoubleVar(value=23)
quality_slider = ttk.Scale(slider_frame, from_=30, to=18, orient=tk.HORIZONTAL, variable=quality_var, command=update_quality_label)
quality_slider.pack(side="left", fill="x", expand=True, padx=10)
quality_value_label = tk.Label(slider_frame, text=f"{quality_var.get():.0f}")
quality_value_label.pack(side="left", padx=(5, 15))
tk.Label(slider_frame, text="(Lower value = Larger File)").pack(side="left")

discord_var = tk.BooleanVar()
discord_checkbox = tk.Checkbutton(root, text="Discord Optimized (CRF 28, 720p max, 96k audio)", variable=discord_var)
discord_checkbox.pack(pady=(5, 10))
discord_var.trace("w", on_discord_toggle)

tk.Button(root, text="Download & Convert", command=start_download).pack(pady=5)
progress_bar = ttk.Progressbar(root, mode='indeterminate', length=350)
progress_bar.pack(pady=(5, 0))
status_label = tk.Label(root, text="Idle")
status_label.pack(pady=(5, 10))

root.mainloop()
