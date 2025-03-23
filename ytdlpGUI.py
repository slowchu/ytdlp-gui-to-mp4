import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import threading
import ctypes
from tkinter import ttk

# Use CREATE_NO_WINDOW flag for Windows; on other OSes, this is 0.
CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

def get_windows_videos_folder():
    try:
        FOLDERID_Videos = '{18989B1D-99B5-455B-841C-AB7C74E4DDFC}'
        SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
        SHGetKnownFolderPath.argtypes = [ctypes.c_char_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_wchar_p)]
        path_ptr = ctypes.c_wchar_p()
        result = SHGetKnownFolderPath(FOLDERID_Videos.encode('utf-8'), 0, None, ctypes.byref(path_ptr))
        return path_ptr.value
    except Exception:
        return None

FFMPEG_PATH = "ffmpeg"     # Update if ffmpeg.exe isn't in PATH
YT_DLP_PATH = "yt-dlp"     # Update if yt-dlp.exe isn't in PATH

videos_dir = get_windows_videos_folder()
if not videos_dir:
    videos_dir = os.path.join(os.path.expanduser("~"), "Videos")

DOWNLOAD_DIR = os.path.join(videos_dir, "YT-DLP Downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def download_and_convert(url, filename):
    try:
        # Update status to "Downloading Video"
        status_label.config(text="Downloading Video...")
        progress_bar.start()

        raw_path = os.path.join(DOWNLOAD_DIR, f"{filename}_raw.webm")
        final_path = os.path.join(DOWNLOAD_DIR, f"{filename}.mp4")

        # Run yt-dlp to download the video
        ytdlp_cmd = [
            YT_DLP_PATH,
            "-f", "bv*[ext=webm]+ba[ext=webm]/best",
            "-o", raw_path,
            url
        ]
        subprocess.run(ytdlp_cmd, check=True, creationflags=CREATE_NO_WINDOW)

        # Update status to "Converting Video"
        status_label.config(text="Converting Video...")

        # Run ffmpeg to convert the video
        if discord_var.get():
            crf_value = "28"
            ffmpeg_cmd = [
                FFMPEG_PATH,
                "-i", raw_path,
                "-c:v", "libx264",
                "-crf", crf_value,
                "-preset", "slow",
                "-vf", "scale='min(1280,iw)':'min(720,ih)':force_original_aspect_ratio=decrease",
                "-c:a", "aac",
                "-b:a", "96k",
                final_path
            ]
        else:
            crf_value = str(quality_slider.get())
            ffmpeg_cmd = [
                FFMPEG_PATH,
                "-i", raw_path,
                "-c:v", "libx264",
                "-crf", crf_value,
                "-preset", "slow",
                "-c:a", "aac",
                "-b:a", "128k",
                final_path
            ]
        subprocess.run(ffmpeg_cmd, check=True, creationflags=CREATE_NO_WINDOW)

        if os.path.exists(raw_path):
            os.remove(raw_path)

        # Update status to "Done"
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

# === GUI Layout ===
root = tk.Tk()
root.title("Video Downloader & Converter")
root.geometry("460x330")
root.resizable(False, False)

tk.Label(root, text="Video Platform URL:").pack(pady=(10, 0))
url_entry = tk.Entry(root, width=55)
url_entry.pack(pady=(0, 10))

tk.Label(root, text="Output Filename (no extension):").pack()
filename_entry = tk.Entry(root, width=55)
filename_entry.pack(pady=(0, 10))

# Quality slider
tk.Label(root, text="Video Quality:").pack()
slider_frame = tk.Frame(root)
slider_frame.pack()

tk.Label(slider_frame, text="Low (Smaller File)").pack(side="left", padx=(15, 5))
quality_slider = tk.Scale(slider_frame, from_=30, to=18, orient=tk.HORIZONTAL)
quality_slider.set(23)
quality_slider.pack(side="left")
tk.Label(slider_frame, text="High (Larger File)").pack(side="left", padx=(5, 15))

# Discord optimized checkbox
discord_var = tk.BooleanVar()
discord_checkbox = tk.Checkbutton(root, text="Discord Optimized (CRF 28, 720p max, 96k audio)", variable=discord_var)
discord_checkbox.pack(pady=(5, 10))

tk.Button(root, text="Download & Convert", command=start_download).pack(pady=5)

# Progress bar (indeterminate / busy animation)
progress_bar = ttk.Progressbar(root, mode='indeterminate', length=300)
progress_bar.pack(pady=(5, 0))

# Status label to show current process
status_label = tk.Label(root, text="Idle")
status_label.pack(pady=(5, 10))

root.mainloop()
