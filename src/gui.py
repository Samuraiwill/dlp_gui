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
            icon_data = "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"
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
