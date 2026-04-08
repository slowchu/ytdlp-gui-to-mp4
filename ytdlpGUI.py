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
        import ctypes.wintypes

        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", ctypes.wintypes.DWORD),
                ("Data2", ctypes.wintypes.WORD),
                ("Data3", ctypes.wintypes.WORD),
                ("Data4", ctypes.c_byte * 8),
            ]

        # {18989B1D-99B5-455B-841C-AB7C74E4DDFC} — Videos known folder
        folderid_videos = GUID()
        folderid_videos.Data1 = 0x18989B1D
        folderid_videos.Data2 = 0x99B5
        folderid_videos.Data3 = 0x455B
        folderid_videos.Data4[:] = [0x84, 0x1C, 0xAB, 0x7C, 0x74, 0xE4, 0xDD, 0xFC]

        SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
        SHGetKnownFolderPath.argtypes = [
            ctypes.POINTER(GUID), ctypes.wintypes.DWORD,
            ctypes.wintypes.HANDLE, ctypes.POINTER(ctypes.c_wchar_p)
        ]
        SHGetKnownFolderPath.restype = ctypes.HRESULT

        path_ptr = ctypes.c_wchar_p()
        hr = SHGetKnownFolderPath(
            ctypes.byref(folderid_videos),
            0, None, ctypes.byref(path_ptr)
        )
        if hr != 0:
            return None

        result = path_ptr.value
        # Free the COM-allocated string
        ctypes.windll.ole32.CoTaskMemFree(path_ptr)
        return result
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

# Tooltip descriptions for tuning options
TUNE_DESCRIPTIONS = {
    "None (Default)": "No special tuning \u2014 works well for most content.",
    "Film": "Optimized for live-action video. Preserves grain and detail, but may increase file size.",
    "Animation": "Optimized for cartoons and anime. Boosts color fidelity on flat areas, often reduces file size.",
}

class ToolTip:
    """Simple hover tooltip for any widget."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if self.tipwindow:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("Segoe UI", 9))
        label.pack(ipadx=4, ipady=2)

    def hide(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

    def update_text(self, text):
        self.text = text

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

def fetch_video_info(url):
    """Fetch duration, source video bitrate, source height, and filesize from yt-dlp."""
    try:
        # Get info for best video and best audio separately
        result = subprocess.run(
            [YT_DLP_PATH, "--ffmpeg-location", os.path.dirname(FFMPEG_PATH),
             "--print", "%(duration)s|%(filesize,filesize_approx)s|%(vbr,tbr)s|%(height)s",
             "-f", "bv*+ba/b", url],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, creationflags=CREATE_NO_WINDOW
        )
        # With bv*+ba/b, yt-dlp may print two lines (video, audio) or one (pre-merged)
        lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
        if not lines:
            return 0, 0, 0, 0

        parts = lines[0].split("|")
        duration = float(parts[0]) if parts[0] and parts[0] != "NA" else 0
        filesize = float(parts[1]) if len(parts) > 1 and parts[1] and parts[1] != "NA" else 0
        vbr = float(parts[2]) if len(parts) > 2 and parts[2] and parts[2] != "NA" else 0
        src_height = int(float(parts[3])) if len(parts) > 3 and parts[3] and parts[3] != "NA" else 0

        # If there's a second line (audio), add its filesize
        if len(lines) > 1:
            audio_parts = lines[1].split("|")
            audio_size = float(audio_parts[1]) if len(audio_parts) > 1 and audio_parts[1] and audio_parts[1] != "NA" else 0
            filesize += audio_size

        return duration, vbr, src_height, filesize
    except:
        return 0, 0, 0, 0

def update_estimated_size():
    url = url_entry.get().strip()
    if not url:
        estimated_label.config(text="Estimated Output Size: N/A")
        return

    estimated_label.config(text="Estimating...")

    duration, src_video_kbps, src_height, src_filesize = fetch_video_info(url)
    if duration <= 0:
        estimated_label.config(text="Estimated Output Size: Unable to determine duration")
        return

    is_discord = discord_var.get()
    is_extreme = extreme_var.get()

    res = "720p" if is_discord else resolution_var.get()
    crf = 28 if is_discord else quality_var.get()

    # Determine target height
    height_map = {"Original": src_height, "480p": 480, "720p": 720,
                  "1080p": 1080, "1440p": 1440, "4K": 2160}
    target_height = height_map.get(res, 720)

    # Audio size estimate (constant, independent of video)
    aud_kbps = 64 if is_extreme else (96 if is_discord else 128)
    audio_size_mb = (duration * aud_kbps) / 8000.0

    if src_filesize > 0 and src_height > 0:
        # Use source filesize as the base — most reliable anchor
        src_size_mb = src_filesize / (1024 * 1024)

        # Subtract estimated audio from source to isolate video portion
        src_audio_mb = (duration * 128) / 8000.0
        src_video_mb = max(src_size_mb - src_audio_mb, src_size_mb * 0.8)

        # Scale by resolution change (pixel area ratio)
        if target_height < src_height:
            res_ratio = (target_height / src_height) ** 1.5  # empirical, not pure area
        else:
            res_ratio = 1.0

        # CRF scaling: YouTube sources are roughly CRF 22-24 equivalent
        # Re-encoding at the same CRF produces ~same size (slight overhead)
        # Each +6 CRF roughly halves bitrate from there
        effective_src_crf = 23
        crf_diff = crf - effective_src_crf
        if crf_diff > 0:
            crf_ratio = 2 ** (-crf_diff / 6)
        else:
            crf_ratio = 2 ** (-crf_diff / 6)

        video_size_mb = src_video_mb * res_ratio * crf_ratio

    elif src_video_kbps > 0 and src_height > 0:
        # Fallback: use reported bitrate if filesize wasn't available
        if target_height < src_height:
            res_ratio = (target_height / src_height) ** 1.5
        else:
            res_ratio = 1.0

        effective_src_crf = 23
        crf_diff = crf - effective_src_crf
        crf_ratio = 2 ** (-crf_diff / 6)

        vid_br = src_video_kbps * res_ratio * crf_ratio
        video_size_mb = (duration * vid_br) / 8000.0
    else:
        # Last resort fallback: fixed bitrate table
        base = base_bitrate_dict.get(res, 1500)
        multiplier = reference_quality / crf
        fudge = max(0.7, min(1.0, 1 - ((crf - 18) / 12) * 0.028))
        vid_br = base * multiplier * fudge
        video_size_mb = (duration * vid_br) / 8000.0

    if static_var.get():
        video_size_mb *= 0.20

    # Extreme mode uses veryslow which is ~10% more efficient
    if is_extreme:
        video_size_mb *= 0.90

    total_mb = video_size_mb + audio_size_mb
    low, high = total_mb * 0.85, total_mb * 1.15
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

        dl_cmd = [
            YT_DLP_PATH,
            "--ffmpeg-location", os.path.dirname(FFMPEG_PATH),
            "-f", "bv*+ba/b",
            "--merge-output-format", "mkv",
            "-o", raw_base, url
        ]
        if not run_command(dl_cmd, console_text):
            raise Exception("yt-dlp download failed.")

        # pick up the raw file (may have extension like .mkv or no extension at all)
        candidates = glob.glob(raw_base + ".*")
        if os.path.isfile(raw_base):
            candidates.append(raw_base)
        if not candidates:
            raise Exception("No raw file found.")
        raw_input = max(candidates, key=lambda f: os.path.getsize(f))

        status_label.config(text="Converting...")

        # Determine settings based on mode
        is_discord = discord_var.get()
        is_extreme = extreme_var.get()

        # Resolution & CRF: Discord locks these, otherwise user controls
        res = "720p" if is_discord else resolution_var.get()
        crf = "28" if is_discord else str(int(quality_var.get()))

        # Audio: Extreme overrides to 64k, else Discord uses 96k, else 128k
        ab = "64k" if is_extreme else ("96k" if is_discord else "128k")

        # Preset: Extreme uses veryslow, otherwise slow
        preset = "veryslow" if is_extreme else "slow"

        # build scale filter
        if res == "Original":
            scale = "scale=trunc(iw/2)*2:trunc(ih/2)*2:flags=lanczos"
        elif res == "4K":
            scale = "scale=3840:2160:flags=lanczos"
        else:
            h = int(res.replace("p", ""))
            scale = f"scale=-2:{h}:flags=lanczos"

        # build tune argument
        tune_selection = tune_var.get()
        tune_map = {"None (Default)": None, "Film": "film", "Animation": "animation"}
        tune_value = tune_map.get(tune_selection)

        ffmpeg_cmd = [
            FFMPEG_PATH,
            "-y", "-i", raw_input,
            "-c:v", "libx264", "-crf", crf, "-preset", preset,
            "-vf", scale,
            "-c:a", "aac", "-b:a", ab,
            "-movflags", "+faststart",
            final_path
        ]

        # insert -tune before the output path if a tune is selected
        if tune_value:
            ffmpeg_cmd.insert(-1, "-tune")
            ffmpeg_cmd.insert(-1, tune_value)

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

def on_extreme_toggle(*_):
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

# Tune selection as radio buttons with inline descriptions
tune_outer_frame = tk.LabelFrame(root, text="Encoder Tuning", padx=10, pady=5)
tune_outer_frame.pack(pady=(0,10), padx=10, fill='x')
tune_var = tk.StringVar(root); tune_var.set("None (Default)")

for option, desc in TUNE_DESCRIPTIONS.items():
    frame = tk.Frame(tune_outer_frame)
    frame.pack(anchor='w', pady=1)
    tk.Radiobutton(frame, text=option, variable=tune_var,
                   value=option).pack(side='left')
    tk.Label(frame, text=f"— {desc}", font=("Segoe UI", 8),
             fg="gray").pack(side='left', padx=(2,0))

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

tk.Label(root, text="Video Quality Scale: (Low\u2013High Quality)").pack()
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
discord_cb = tk.Checkbutton(root, text="Discord Optimized (CRF28, 720p, 96k audio)",
                            variable=discord_var)
discord_cb.pack(pady=(5,0))
discord_var.trace_add('write', on_discord_toggle)
ToolTip(discord_cb, "Locks resolution to 720p and CRF to 28.\nGood starting point for Discord file limits.")

extreme_var = tk.BooleanVar()
extreme_cb = tk.Checkbutton(root, text="Extreme Optimized (veryslow preset, 64k audio)",
                            variable=extreme_var)
extreme_cb.pack(pady=(0,10))
extreme_var.trace_add('write', on_extreme_toggle)
ToolTip(extreme_cb, "Uses the veryslow encoder preset and 64kbps audio\nfor maximum compression at any resolution/quality.\nCan be combined with Discord Optimized.\nEncoding will take significantly longer.")

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
