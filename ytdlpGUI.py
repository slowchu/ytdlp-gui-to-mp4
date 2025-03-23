import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import threading
import ctypes
from tkinter import ttk
import shutil

# Use CREATE_NO_WINDOW flag for Windows
CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

def get_windows_videos_folder():
    try:
        FOLDERID_Videos = '{18989B1D-99B5-455B-841C-AB7C74E4DDFC}'
        SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
        SHGetKnownFolderPath.argtypes = [
            ctypes.c_char_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_wchar_p)
        ]
        path_ptr = ctypes.c_wchar_p()
        result = SHGetKnownFolderPath(FOLDERID_Videos.encode('utf-8'), 0, None, ctypes.byref(path_ptr))
        return path_ptr.value
    except Exception:
        return None

# Find ffmpeg
FFMPEG_PATH = shutil.which("ffmpeg")
if not FFMPEG_PATH:
    fallback_ffmpeg = r"C:\Program Files\VideoTools\ffmpeg.exe"
    if os.path.exists(fallback_ffmpeg):
        FFMPEG_PATH = fallback_ffmpeg
    else:
        messagebox.showerror("FFmpeg Not Found", "FFmpeg is not installed or not in PATH.")
        exit()

# Find yt-dlp
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

def get_crf_fudge_factor_exponential(crf):
    """
    Returns a fudge factor that grows exponentially so that:
      - at CRF=30, factor ~1.0
      - at CRF=18, factor ~2.0
    """
    min_crf, max_crf = 18, 30
    # Clamp CRF value
    crf = max(min_crf, min(crf, max_crf))
    # We want b^(max_crf - CRF) = factor, with factor=2.0 at CRF=18 (difference 12 steps)
    # So b^12 = 2 -> b = 2^(1/12)
    b = 2 ** (1/12)
    exponent = (max_crf - crf)
    return b ** exponent

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

    if discord_var.get():
        # Discord Optimized: fixed settings (720p, CRF 28, 96k audio)
        res = "720p"
        base_bitrate = base_bitrate_dict.get(res, 1500)
        quality_val = 28
        multiplier = reference_quality / quality_val
        estimated_video_bitrate = base_bitrate * multiplier
        total_bitrate = estimated_video_bitrate + 96
        estimated_size = (duration * total_bitrate) / 8000.0
        lower_bound = estimated_size * 0.50
        upper_bound = estimated_size * 0.75
        estimated_label.config(
            text=f"Estimated Output Size: {lower_bound:.1f} MB - {upper_bound:.1f} MB (Discord Optimized)"
        )
    else:
        # Non-Discord: use CRF-based exponential fudge factor
        res = resolution_var.get()
        base_bitrate = base_bitrate_dict.get(res, 1500)
        quality_val = quality_var.get()
        multiplier = reference_quality / quality_val

        fudge_factor = get_crf_fudge_factor_exponential(quality_val)
        estimated_video_bitrate = base_bitrate * multiplier * fudge_factor

        total_bitrate = estimated_video_bitrate + 128
        estimated_size = (duration * total_bitrate) / 8000.0
        lower_bound = estimated_size * 0.50
        upper_bound = estimated_size * 0.75
        estimated_label.config(
            text=f"Estimated Output Size: {lower_bound:.1f} MB - {upper_bound:.1f} MB"
        )

def start_estimation_thread():
    threading.Thread(target=update_estimated_size, daemon=True).start()

def download_and_convert(url, filename):
    try:
        status_label.config(text="Downloading Video...")
        progress_bar.start()
        raw_path = os.path.join(DOWNLOAD_DIR, f"{filename}_raw.webm")
        final_path = os.path.join(DOWNLOAD_DIR, f"{filename}.mp4")
        ytdlp_cmd = [
            YT_DLP_PATH,
            "-f", "bv*[ext=webm]+ba[ext=webm]/best",
            "-o", raw_path,
            url
        ]
        subprocess.run(ytdlp_cmd, check=True, creationflags=CREATE_NO_WINDOW)
        status_label.config(text="Converting Video...")
        res = resolution_var.get()
        if discord_var.get():
            res = "720p"  # Force 720p for Discord

        if res == "Original":
            scale_filter = "scale=iw:-2:flags=lanczos"
        elif res == "4K":
            scale_filter = "scale=3840:-2:flags=lanczos"
        else:
            numeric = res.replace("p", "")
            scale_filter = f"scale={numeric}:-2:flags=lanczos"

        if discord_var.get():
            crf_value = "28"
            ffmpeg_cmd = [
                FFMPEG_PATH,
                "-i", raw_path,
                "-c:v", "libx264",
                "-crf", crf_value,
                "-preset", "slow",
                "-vf", scale_filter,
                "-c:a", "aac",
                "-b:a", "96k",
                final_path
            ]
        else:
            crf_value = str(quality_var.get())
            ffmpeg_cmd = [
                FFMPEG_PATH,
                "-i", raw_path,
                "-c:v", "libx264",
                "-crf", crf_value,
                "-preset", "slow",
                "-vf", scale_filter,
                "-c:a", "aac",
                "-b:a", "128k",
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

# === GUI ===
root = tk.Tk()
root.title("Video Downloader & Converter")
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
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
estimated_label.pack(pady=(0, 10))

tk.Label(root, text="Video Quality (Lower value = higher quality):").pack()
slider_frame = tk.Frame(root)
slider_frame.pack(fill="x", padx=10)
tk.Label(slider_frame, text="Low (Smaller File)").pack(side="left", padx=(15, 5))
quality_var = tk.DoubleVar(value=23)
quality_slider = ttk.Scale(slider_frame, from_=30, to=18, orient=tk.HORIZONTAL,
                           variable=quality_var, command=update_quality_label)
quality_slider.pack(side="left", fill="x", expand=True, padx=10)
quality_value_label = tk.Label(slider_frame, text=f"{quality_var.get():.0f}")
quality_value_label.pack(side="left", padx=(5, 15))
tk.Label(slider_frame, text="(Higher value = Larger File)").pack(side="left")

discord_var = tk.BooleanVar()
discord_checkbox = tk.Checkbutton(
    root,
    text="Discord Optimized (CRF 28, 720p max, 96k audio)",
    variable=discord_var
)
discord_checkbox.pack(pady=(5, 10))
discord_var.trace("w", on_discord_toggle)

tk.Button(root, text="Download & Convert", command=start_download).pack(pady=5)
progress_bar = ttk.Progressbar(root, mode='indeterminate', length=350)
progress_bar.pack(pady=(5, 0))
status_label = tk.Label(root, text="Idle")
status_label.pack(pady=(5, 10))

root.update_idletasks()
window_width = 500
window_height = root.winfo_reqheight()
x_position = (screen_width - window_width) // 2
y_position = (screen_height - window_height) // 3
root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
root.mainloop()
