import os
import sys
import json
import base64
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

try:
    from src.binary_manager import check_binaries_exist, download_binaries
except ImportError:
    from binary_manager import check_binaries_exist, download_binaries

try:
    from src.metadata_service import fetch_metadata
except ImportError:
    from metadata_service import fetch_metadata

try:
    from src.downloader import DirectDownloader
except ImportError:
    from downloader import DirectDownloader

# Set system scaling and appearance
ctk.set_appearance_mode("Dark")  # Modes: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue", "green", "dark-blue"

CONFIG_PATH = os.path.expanduser("~/.yt_dlp_desktop_gui/config.json")

def load_config():
    """Loads application config or returns default settings."""
    default_save_dir = os.path.expanduser("~/Downloads/Media")
    default_config = {
        "save_dir": default_save_dir,
        "preset": "Best Video + Audio",
        "container": "mp4",
        "name_template": "%(title)s [%(id)s].%(ext)s",
        "embed_thumbnail": True,
        "embed_subtitles": False,
        "extract_audio": False
    }

    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                saved = json.load(f)
                # Merge missing keys
                for k, v in default_config.items():
                    if k not in saved:
                        saved[k] = v
                return saved
        except Exception:
            pass

    # Try to create dir if not exists
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    return default_config

def save_config(config):
    """Saves application config."""
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=4)
    except Exception:
        pass


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure window
        self.title("yt-dlp Desktop Studio")
        self.geometry("900x700")
        self.minsize(800, 600)

        # Set default window icon (Base64-encoded PNG)
        try:
            icon_data = "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABGdBTUEAALGPC/xhBQAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAAnElEQVQ4T2MYPcAOiL8D8X8gHgDE76EYm2AAn8GIYfX///8XgPgrEG8AYgZ0AegYpA7D//9QfB6I/wLxRSDmQBeEjv/9/6P278ehGYZhwF+C7fofCWA0DJC0//8fdfz/Y7gAn9FA2v79v78D8XcgZkAXYCgGoNivQPwdmU8vGLgD8W4gXgHEDOjkZgPEn4EYK6BiEIDpB8T/8YsBALC2T67iLpujAAAAAElFTkSuQmCC"
            icon_img = tk.PhotoImage(data=base64.b64decode(icon_data))
            self.iconphoto(True, icon_img)
        except Exception:
            pass

        # Load user configuration
        self.config = load_config()

        # Active Downloader instance
        self.active_downloader = None
        self.is_downloading = False
        self.is_inspecting = False

        # Build UI layout
        self.create_widgets()

        # Check and download binaries if needed
        self.after(100, self.check_and_bootstrap_binaries)

    def create_widgets(self):
        # Configure grid layout (4 rows: URL bar, Options, Execution/Progress Panel, Console Log Box)
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ------------------ Row 0: URL BAR ------------------
        self.url_frame = ctk.CTkFrame(self)
        self.url_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.url_frame.grid_columnconfigure(1, weight=1)

        self.url_label = ctk.CTkLabel(self.url_frame, text="Media URL:", font=ctk.CTkFont(weight="bold"))
        self.url_label.grid(row=0, column=0, padx=15, pady=15, sticky="w")

        self.url_entry = ctk.CTkEntry(
            self.url_frame,
            placeholder_text="Paste video or playlist URL here (YouTube, Vimeo, Soundcloud, etc.)..."
        )
        self.url_entry.grid(row=0, column=1, padx=(5, 10), pady=15, sticky="ew")

        self.paste_btn = ctk.CTkButton(self.url_frame, text="Paste", width=80, command=self.paste_clipboard)
        self.paste_btn.grid(row=0, column=2, padx=(0, 15), pady=15)

        # ------------------ Row 1: OPTIONS PANEL ------------------
        self.options_frame = ctk.CTkFrame(self)
        self.options_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.options_frame.grid_columnconfigure(1, weight=1)
        self.options_frame.grid_columnconfigure(3, weight=1)

        # Preset Quality dropdown
        self.preset_label = ctk.CTkLabel(self.options_frame, text="Preset:", font=ctk.CTkFont(weight="bold"))
        self.preset_label.grid(row=0, column=0, padx=(15, 5), pady=12, sticky="w")

        self.preset_var = ctk.StringVar(value=self.config["preset"])
        self.preset_dropdown = ctk.CTkOptionMenu(
            self.options_frame,
            values=["Best Video + Audio", "1080p", "720p", "4K"],
            variable=self.preset_var,
            command=self.on_setting_changed
        )
        self.preset_dropdown.grid(row=0, column=1, padx=(5, 15), pady=12, sticky="ew")

        # Container dropdown
        self.container_label = ctk.CTkLabel(self.options_frame, text="Container:", font=ctk.CTkFont(weight="bold"))
        self.container_label.grid(row=0, column=2, padx=(15, 5), pady=12, sticky="w")

        self.container_var = ctk.StringVar(value=self.config["container"])
        self.container_dropdown = ctk.CTkOptionMenu(
            self.options_frame,
            values=["mp4", "mkv", "webm", "mp3", "m4a", "flac"],
            variable=self.container_var,
            command=self.on_setting_changed
        )
        self.container_dropdown.grid(row=0, column=3, padx=(5, 15), pady=12, sticky="ew")

        # Save path browser
        self.save_label = ctk.CTkLabel(self.options_frame, text="Save To:", font=ctk.CTkFont(weight="bold"))
        self.save_label.grid(row=1, column=0, padx=(15, 5), pady=12, sticky="w")

        self.save_entry = ctk.CTkEntry(self.options_frame)
        self.save_entry.insert(0, self.config["save_dir"])
        self.save_entry.grid(row=1, column=1, columnspan=2, padx=(5, 10), pady=12, sticky="ew")

        self.browse_btn = ctk.CTkButton(self.options_frame, text="Browse...", width=90, command=self.browse_directory)
        self.browse_btn.grid(row=1, column=3, padx=(0, 15), pady=12, sticky="e")

        # Checkbox Settings row
        self.checkbox_frame = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        self.checkbox_frame.grid(row=2, column=0, columnspan=4, padx=15, pady=(5, 15), sticky="ew")

        self.thumb_var = ctk.BooleanVar(value=self.config["embed_thumbnail"])
        self.thumb_cb = ctk.CTkCheckBox(
            self.checkbox_frame, text="Embed Thumbnail", variable=self.thumb_var, command=self.on_setting_changed
        )
        self.thumb_cb.grid(row=0, column=0, padx=(0, 25), pady=5, sticky="w")

        self.subs_var = ctk.BooleanVar(value=self.config["embed_subtitles"])
        self.subs_cb = ctk.CTkCheckBox(
            self.checkbox_frame, text="Embed Subtitles", variable=self.subs_var, command=self.on_setting_changed
        )
        self.subs_cb.grid(row=0, column=1, padx=25, pady=5, sticky="w")

        self.audio_var = ctk.BooleanVar(value=self.config["extract_audio"])
        self.audio_cb = ctk.CTkCheckBox(
            self.checkbox_frame, text="Extract Audio Only", variable=self.audio_var, command=self.on_audio_toggle
        )
        self.audio_cb.grid(row=0, column=2, padx=25, pady=5, sticky="w")

        # ------------------ Row 2: EXECUTION & PROGRESS PANEL ------------------
        self.execution_frame = ctk.CTkFrame(self)
        self.execution_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.execution_frame.grid_columnconfigure(0, weight=1)

        # Start/Cancel Download Button
        self.start_btn = ctk.CTkButton(
            self.execution_frame,
            text="Start Download",
            fg_color="#2ecc71",
            hover_color="#27ae60",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            command=self.toggle_download_action
        )
        self.start_btn.grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 10), sticky="ew")

        # Active Title Label
        self.status_title_lbl = ctk.CTkLabel(
            self.execution_frame,
            text="Ready to download",
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.status_title_lbl.grid(row=1, column=0, columnspan=2, padx=15, pady=(5, 2), sticky="ew")

        # Single Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self.execution_frame)
        self.progress_bar.grid(row=2, column=0, columnspan=2, padx=15, pady=8, sticky="ew")
        self.progress_bar.set(0)

        # Real-time Metrics Info Label
        self.metrics_lbl = ctk.CTkLabel(
            self.execution_frame,
            text="Status: Idle",
            font=ctk.CTkFont(size=11),
            text_color="#aaaaaa"
        )
        self.metrics_lbl.grid(row=3, column=0, columnspan=2, padx=15, pady=(2, 15), sticky="w")

        # ------------------ Row 3: CONSOLE LOG BOX ------------------
        self.log_container = ctk.CTkFrame(self, fg_color="transparent")
        self.log_container.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="nsew")
        self.log_container.grid_rowconfigure(1, weight=1)
        self.log_container.grid_columnconfigure(0, weight=1)

        self.log_label = ctk.CTkLabel(self.log_container, text="DOWNLOAD CONSOLE LOG", font=ctk.CTkFont(size=12, weight="bold"))
        self.log_label.grid(row=0, column=0, padx=5, pady=(5, 5), sticky="w")

        self.log_textbox = ctk.CTkTextbox(self.log_container, font=ctk.CTkFont(family="Courier", size=11))
        self.log_textbox.grid(row=1, column=0, sticky="nsew")
        self.log_textbox.insert("1.0", "Welcome to yt-dlp Desktop Studio console.\nLogs will stream here in real time.\n")
        self.log_textbox.configure(state="disabled")

    # ------------------ Control Methods ------------------

    def check_and_bootstrap_binaries(self):
        """Checks if binaries exist, if not downloads them using a popup dialogue."""
        if check_binaries_exist():
            return

        # Spawn download popup overlay
        self.bootstrap_win = ctk.CTkToplevel(self)
        self.bootstrap_win.title("Auto-downloading dependencies")
        self.bootstrap_win.geometry("450x220")
        self.bootstrap_win.resizable(False, False)
        self.bootstrap_win.transient(self)
        self.bootstrap_win.grab_set()  # Modal window

        # Center the window relative to self
        self.bootstrap_win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 225
        y = self.winfo_y() + (self.winfo_height() // 2) - 110
        self.bootstrap_win.geometry(f"+{x}+{y}")

        lbl = ctk.CTkLabel(
            self.bootstrap_win,
            text="Downloading yt-dlp & ffmpeg binaries...\nThis is a one-time setup for zero dependencies.",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        lbl.pack(pady=(25, 15))

        self.bootstrap_status = ctk.CTkLabel(self.bootstrap_win, text="Starting...", font=ctk.CTkFont(size=11))
        self.bootstrap_status.pack(pady=5)

        self.bootstrap_progress = ctk.CTkProgressBar(self.bootstrap_win, width=350)
        self.bootstrap_progress.pack(pady=10)
        self.bootstrap_progress.set(0)

        threading.Thread(target=self._run_bootstrap, daemon=True).start()

    def _run_bootstrap(self):
        def progress_updater(msg, percent):
            self.bootstrap_status.configure(text=msg)
            self.bootstrap_progress.set(percent / 100.0)

        try:
            download_binaries(progress_updater)
            self.after(500, self._bootstrap_complete)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Download Error", f"Failed to download required engine files:\n{str(e)}"))
            self.after(0, self.bootstrap_win.destroy)

    def _bootstrap_complete(self):
        self.bootstrap_win.destroy()
        messagebox.showinfo("Ready!", "All dependencies fetched successfully! You are ready to download.")

    def paste_clipboard(self):
        try:
            clipboard_text = self.clipboard_get()
            if clipboard_text:
                self.url_entry.delete(0, tk.END)
                self.url_entry.insert(0, clipboard_text.strip())
        except Exception:
            pass

    def browse_directory(self):
        dir_path = filedialog.askdirectory(initialdir=self.save_entry.get())
        if dir_path:
            self.save_entry.delete(0, tk.END)
            self.save_entry.insert(0, dir_path)
            self.on_setting_changed()

    def on_setting_changed(self, *args):
        """Stores the configuration whenever changed."""
        self.config["save_dir"] = self.save_entry.get()
        self.config["preset"] = self.preset_var.get()
        self.config["container"] = self.container_var.get()
        self.config["embed_thumbnail"] = self.thumb_var.get()
        self.config["embed_subtitles"] = self.subs_var.get()
        self.config["extract_audio"] = self.audio_var.get()
        save_config(self.config)

    def on_audio_toggle(self):
        self.on_setting_changed()
        if self.audio_var.get():
            self.preset_dropdown.configure(state="disabled")
            if self.container_var.get() in ["mp4", "mkv", "webm"]:
                self.container_var.set("mp3")
                self.container_dropdown.configure(values=["mp3", "m4a", "flac"])
        else:
            self.preset_dropdown.configure(state="normal")
            self.container_dropdown.configure(values=["mp4", "mkv", "webm", "mp3", "m4a", "flac"])
            self.container_var.set("mp4")

        self.on_setting_changed()

    # ------------------ Execution Flow ------------------

    def toggle_download_action(self):
        """Toggles action between Start Download and Cancel Download."""
        if self.is_downloading:
            # Cancel active download
            if self.active_downloader:
                self.active_downloader.cancel()
            return

        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter or paste a valid media URL first.")
            return

        self.is_downloading = True
        self.is_inspecting = True
        self.start_btn.configure(text="Cancel Download", fg_color="#e74c3c", hover_color="#c0392b")
        self.status_title_lbl.configure(text="Inspecting URL...")
        self.progress_bar.set(0)
        self.metrics_lbl.configure(text="Status: Resolving URL metadata...", text_color="#3a7ebf")

        # Clear console log textbox
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", tk.END)
        self.log_textbox.insert(tk.END, "Starting metadata inspection...\n")
        self.log_textbox.configure(state="disabled")

        # Launch resolution in background thread
        threading.Thread(target=self._inspect_and_start_worker, args=(url,), daemon=True).start()

    def _inspect_and_start_worker(self, url):
        # Step 1: Inspect URL metadata
        video_title = url
        try:
            metadata = fetch_metadata(url)
            if metadata and "title" in metadata:
                video_title = metadata["title"]
        except Exception as e:
            # If inspection fails (e.g. offline, slight timeout), print notice to log but proceed anyway!
            self._write_to_log(f"URL inspection warning/failed: {str(e)}\nProceeding with direct download using URL...\n")

        # Step 2: Directly trigger the active downloader instance!
        if not self.is_downloading:
            # User clicked cancel during inspection
            return

        self.is_inspecting = False
        self.after(0, lambda: self.status_title_lbl.configure(text=f"Downloading: {video_title}"))

        save_dir = self.save_entry.get()
        preset = self.preset_var.get()
        container = self.container_var.get()
        embed_thumb = self.thumb_var.get()
        embed_subs = self.subs_var.get()
        extract_audio = self.audio_var.get()
        name_template = self.config["name_template"]

        self.active_downloader = DirectDownloader(
            url=url,
            save_dir=save_dir,
            preset=preset,
            container=container,
            embed_thumbnail=embed_thumb,
            embed_subtitles=embed_subs,
            extract_audio=extract_audio,
            name_template=name_template,
            progress_callback=self.on_progress_update,
            log_callback=self._write_to_log,
            completion_callback=self.on_download_complete
        )
        self.active_downloader.start()

    def on_progress_update(self, prog):
        """Callback triggered dynamically in real time."""
        percent = prog["percent"]
        speed = prog["speed"]
        eta = prog["eta"]
        size = prog["size"]

        self.after(0, lambda: self.progress_bar.set(percent / 100.0))
        self.after(0, lambda: self.metrics_lbl.configure(
            text=f"Progress: {percent}% | Speed: {speed} | ETA: {eta} | Size: {size}",
            text_color="#3a7ebf"
        ))

    def _write_to_log(self, text):
        """Thread-safe logging write to CTkTextbox console log."""
        self.after(0, lambda: self._append_textbox(text))

    def _append_textbox(self, text):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert(tk.END, text)
        self.log_textbox.see(tk.END)
        self.log_textbox.configure(state="disabled")

    def on_download_complete(self, status, error_msg):
        """Completion callback."""
        self.after(0, lambda: self._handle_complete_ui(status, error_msg))

    def _handle_complete_ui(self, status, error_msg):
        self.is_downloading = False
        self.is_inspecting = False
        self.active_downloader = None
        self.start_btn.configure(text="Start Download", fg_color="#2ecc71", hover_color="#27ae60")

        if status == "Completed":
            self.progress_bar.set(1.0)
            self.status_title_lbl.configure(text="Download completed successfully!")
            self.metrics_lbl.configure(text=f"Saved successfully to: {self.save_entry.get()}", text_color="#2ecc71")
            messagebox.showinfo("Success", "Download completed successfully!")
        elif status == "Cancelled":
            self.status_title_lbl.configure(text="Download Cancelled")
            self.metrics_lbl.configure(text="Status: Aborted by user.", text_color="#95a5a6")
            messagebox.showwarning("Cancelled", "Download process cancelled.")
        else:
            self.status_title_lbl.configure(text="Download Failed")
            self.metrics_lbl.configure(text=f"Failed: {error_msg}", text_color="#e74c3c")
            messagebox.showerror("Failed", f"Download failed:\n{error_msg}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
