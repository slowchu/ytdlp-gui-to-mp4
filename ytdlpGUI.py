import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
import subprocess
import os
import threading
import ctypes
import shutil
import glob
import math

# Hide external windows when not showing progress
CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

# Buffer to hold all command output
command_output_buffer = []

def get_windows_videos_folder():
    try:
        FOLDERID_Videos = '{18989B1D-99B5-455-841C-AB7C74E4DDFC}'
        SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
        SHGetKnownFolderPath.argtypes = [
            ctypes.c_char_p, ctypes.c_uint32,
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_wchar_p)
        ]
        path_ptr = ctypes.c_wchar_p()
        SHGetKnownFolderPath(
            FOLDERID_Videos.encode('utf-8'),
            0, None, ctypes.byref(path_ptr)
        )
        return path_ptr.value
    except Exception:
        return None

# Locate ffmpeg & yt-dlp
FFMPEG_PATH = shutil.which("ffmpeg") or r"C:\Program Files\VideoTools\ffmpeg.exe"
if not os.path.exists(FFMPEG_PATH):
    messagebox.showerror("FFmpeg Not Found", "FFmpeg not installed or not in PATH.")
    exit(1)

YT_DLP_PATH = shutil.which("yt-dlp") or r"C:\Program Files\VideoTools\yt-dlp.exe"
if not os.path.exists(YT_DLP_PATH):
    messagebox.showerror("yt-dlp Not Found", "yt-dlp not installed or not in PATH.")
    exit(1)

videos_dir = get_windows_videos_folder() or os.path.join(os.path.expanduser("~"), "Videos")
DOWNLOAD_DIR = os.path.join(videos_dir, "YT-DLP Downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

base_bitrate_dict = {
    "Original": 1500, "480p": 1000, "720p": 1500,
    "1080p":    2500, "1440p": 4000,   "4K": 8000
}
reference_quality = 23

def run_command(cmd, out_widget=None):
    """
    Always capture stdout/stderr, but only write it into out_widget
    when showprogress_var.get() is True. Suppress the extra console
    window by passing CREATE_NO_WINDOW.
    """
    # Prepare STARTUPINFO to hide console on Windows
    startupinfo = None
    if os.name == 'nt':
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo = si

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=CREATE_NO_WINDOW,
        startupinfo=startupinfo
    )

    for line in proc.stdout:
        command_output_buffer.append(line)
        if out_widget and showprogress_var.get():
            out_widget.config(state='normal')
            out_widget.insert('end', line)
            out_widget.see('end')
            out_widget.config(state='disabled')

    proc.wait()
    footer = f"[exit code {proc.returncode}]\n\n"
    command_output_buffer.append(footer)
    if out_widget and showprogress_var.get():
        out_widget.config(state='normal')
        out_widget.insert('end', footer)
        out_widget.config(state='disabled')

    return proc.returncode == 0

def fetch_video_duration(url):
    try:
        result = subprocess.run(
            [YT_DLP_PATH, "--ffmpeg-location", os.path.dirname(FFMPEG_PATH),
             "--print", "duration", url],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, creationflags=CREATE_NO_WINDOW
        )
        return float(result.stdout.strip())
    except:
        return 0

def update_estimated_size():
    url = url_entry.get().strip()
    if not url:
        estimated_label.config(text="Estimated Output Size: N/A")
        return

    duration = fetch_video_duration(url)
    if duration <= 0:
        estimated_label.config(text="Estimated Output Size: Unable to determine duration")
        return

    res = resolution_var.get() if not discord_var.get() else "720p"
    base = base_bitrate_dict.get(res, 1500)
    crf  = 28 if discord_var.get() else quality_var.get()

    multiplier = reference_quality / crf
    fudge = 1 - ((crf - 18) / 12) * 0.028
    fudge = max(0.7, min(fudge, 1.0))

    vid_br = base * multiplier * fudge
    aud_br = 96 if discord_var.get() else 128
    total = vid_br + aud_br
    if static_var.get():
        total *= 0.20

    size_mb = (duration * total) / 8000.0
    low, high = size_mb * 0.95, size_mb * 1.25
    estimated_label.config(text=f"Estimated Output Size: {low:.1f} MB - {high:.1f} MB")

def start_estimation_thread():
    threading.Thread(target=update_estimated_size, daemon=True).start()

def download_and_convert(url, filename):
    # Clear buffer & console
    command_output_buffer.clear()
    if showprogress_var.get():
        console_text.config(state='normal')
        console_text.delete('1.0', 'end')
        console_text.config(state='disabled')

    raw_base   = os.path.join(DOWNLOAD_DIR, f"{filename}_raw")
    final_path = os.path.join(DOWNLOAD_DIR, f"{filename}.mp4")

    if os.path.exists(final_path):
        if not messagebox.askyesno("Duplicate Name Detected",
                                   f"'{final_path}' exists.\nOverwrite?"):
            status_label.config(text="Canceled")
            return

    try:
        status_label.config(text="Downloading...")
        progress_bar.start()

        cmd1 = [
            YT_DLP_PATH,
            "--ffmpeg-location", os.path.dirname(FFMPEG_PATH),
            "-f", "bestvideo*+bestaudio",
            "--merge-output-format", "mkv",
            "-o", raw_base, url
        ]
        cmd2 = [
            YT_DLP_PATH,
            "--ffmpeg-location", os.path.dirname(FFMPEG_PATH),
            "-f", "best",
            "--merge-output-format", "mkv",
            "-o", raw_base, url
        ]
        if not run_command(cmd1, console_text) and not run_command(cmd2, console_text):
            raise Exception("yt-dlp download failed.")

        # pick up the largest raw file
        candidates = glob.glob(raw_base + ".*")
        if not candidates:
            raise Exception("No raw file found.")
        raw_input = max(candidates, key=lambda f: os.path.getsize(f))

        status_label.config(text="Converting...")
        # build scale filter with even width
        res = resolution_var.get() if not discord_var.get() else "720p"
        if res == "Original":
            scale = "scale=iw:ih:flags=lanczos"
        elif res == "4K":
            scale = "scale=3840:2160:flags=lanczos"
        else:
            h = int(res.replace("p", ""))
            w = int(h * 16/9)
            w = (w // 2) * 2            # force even width
            scale = f"scale={w}:{h}:flags=lanczos"

        crf = "28" if discord_var.get() else str(quality_var.get())
        ab  = "96k" if discord_var.get() else "128k"

        ffmpeg_cmd = [
            FFMPEG_PATH,
            "-y", "-i", raw_input,
            "-c:v", "libx264", "-crf", crf, "-preset", "slow",
            "-vf", scale,
            "-c:a", "aac", "-b:a", ab,
            final_path
        ]
        if not run_command(ffmpeg_cmd, console_text):
            raise Exception("FFmpeg conversion failed.")

        # cleanup
        for f in candidates:
            try: os.remove(f)
            except: pass

        status_label.config(text="Done")
        messagebox.showinfo("Success", f"Saved to:\n{final_path}")

    except Exception as ex:
        status_label.config(text="Error")
        messagebox.showerror("Error", str(ex))
    finally:
        progress_bar.stop()

def start_download():
    url = url_entry.get().strip()
    fn  = filename_entry.get().strip()
    if not url:
        messagebox.showwarning("Missing URL", "Enter a video URL.")
        return
    if not fn:
        messagebox.showwarning("Missing Filename", "Enter a filename.")
        return
    fn = "".join(c for c in fn if c.isalnum() or c in (' ', '_')).rstrip()
    threading.Thread(target=download_and_convert, args=(url, fn), daemon=True).start()

def on_discord_toggle(*_):
    if discord_var.get():
        resolution_menu.config(state='disabled')
        quality_slider.config(state='disabled')
        resolution_var.set("720p")
    else:
        resolution_menu.config(state='normal')
        quality_slider.config(state='normal')
    start_estimation_thread()

def on_showprogress_toggle(*_):
    if showprogress_var.get():
        console_frame.pack(fill='both', expand=True, padx=10, pady=(5,10))
        console_text.config(state='normal')
        console_text.delete('1.0', 'end')
        console_text.insert('end', ''.join(command_output_buffer))
        console_text.config(state='disabled')
    else:
        console_frame.pack_forget()

def update_quality_label(val=None):
    quality_value_label.config(text=f"{quality_var.get():.0f}")

# — Build GUI —
root = tk.Tk()
root.title("Video Downloader & Converter")
root.resizable(False, False)

tk.Label(root, text="Video Platform URL:").pack(pady=(10,0))
url_entry = tk.Entry(root, width=60); url_entry.pack(pady=(0,10))

tk.Label(root, text="Output Filename (no extension):").pack()
filename_entry = tk.Entry(root, width=60); filename_entry.pack(pady=(0,10))

tk.Label(root, text="Select Resolution:").pack()
resolution_options = ["Original","480p","720p","1080p","1440p","4K"]
resolution_var = tk.StringVar(root); resolution_var.set("720p")
resolution_menu = tk.OptionMenu(root, resolution_var, *resolution_options,
                                command=lambda _: start_estimation_thread())
resolution_menu.pack(pady=(0,10))

tk.Button(root, text="Estimate File Size", command=start_estimation_thread).pack()
estimated_label = tk.Label(root, text="Estimated Output Size: N/A")
estimated_label.pack(pady=(5,10))

static_var = tk.BooleanVar()
tk.Checkbutton(root, text="Static Image (Less Motion)",
               variable=static_var, command=start_estimation_thread).pack()

showprogress_var = tk.BooleanVar()
tk.Checkbutton(root, text="Show progress",
               variable=showprogress_var).pack(pady=(5,10))
showprogress_var.trace_add('write', on_showprogress_toggle)

tk.Label(root, text="Video Quality Scale: (Low–High Quality)").pack()
slider_frame = tk.Frame(root); slider_frame.pack(fill='x', padx=10)
tk.Label(slider_frame, text="(Higher=Smaller File)").pack(side='left', padx=(5,5))
quality_var = tk.DoubleVar(value=23)
quality_slider = ttk.Scale(slider_frame, from_=30, to=18,
                           orient='horizontal',
                           variable=quality_var,
                           command=update_quality_label)
quality_slider.pack(side='left', fill='x', expand=True)
quality_value_label = tk.Label(slider_frame, text="23")
quality_value_label.pack(side='left', padx=(5,5))
tk.Label(slider_frame, text="(Lower=Larger File)").pack(side='left')

discord_var = tk.BooleanVar()
tk.Checkbutton(root, text="Discord Optimized (CRF28,720p max,96k audio)",
               variable=discord_var).pack(pady=(5,10))
discord_var.trace_add('write', on_discord_toggle)

tk.Button(root, text="Download & Convert", command=start_download).pack(pady=(5,10))
progress_bar = ttk.Progressbar(root, mode='indeterminate', length=400)
progress_bar.pack(pady=(0,10))
status_label = tk.Label(root, text="Idle")
status_label.pack()

console_frame = tk.Frame(root)
console_text = scrolledtext.ScrolledText(console_frame, height=12, state='disabled')
console_text.pack(fill='both', expand=True)
on_showprogress_toggle()  # initialize console hidden

root.mainloop()
