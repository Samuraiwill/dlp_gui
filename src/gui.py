import os
import sys
import json
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from src.binary_manager import check_binaries_exist, download_binaries
from src.metadata_service import fetch_metadata
from src.downloader import DownloadManager

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
        self.geometry("900x680")
        self.minimum_size(800, 600)

        # Load user configuration
        self.config = load_config()

        # Initialize Downloader Engine
        self.manager = DownloadManager()
        self.manager.set_update_callback(self.on_queue_updated)

        # GUI state
        self.is_resolving_url = False

        # Build UI layout
        self.create_widgets()

        # Check and download binaries if needed
        self.after(100, self.check_and_bootstrap_binaries)

    def create_widgets(self):
        # Configure grid layout (4 rows: URL bar, Options, Queue Actions, Active Queue)
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

        # ------------------ Row 2: QUEUE CONTROLS ------------------
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.controls_frame.grid_columnconfigure(0, weight=1)

        self.add_queue_btn = ctk.CTkButton(
            self.controls_frame,
            text="Add to Queue",
            fg_color="#1f538d",
            hover_color="#14375e",
            font=ctk.CTkFont(weight="bold"),
            command=self.add_url_to_queue
        )
        self.add_queue_btn.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")

        self.start_all_btn = ctk.CTkButton(self.controls_frame, text="Start All", command=self.manager.start_all)
        self.start_all_btn.grid(row=0, column=1, padx=5, pady=5)

        self.pause_all_btn = ctk.CTkButton(self.controls_frame, text="Pause All", command=self.manager.pause_all)
        self.pause_all_btn.grid(row=0, column=2, padx=5, pady=5)

        self.cancel_all_btn = ctk.CTkButton(self.controls_frame, text="Cancel All", fg_color="#B22222", hover_color="#8B0000", command=self.manager.cancel_all)
        self.cancel_all_btn.grid(row=0, column=3, padx=(5, 0), pady=5)

        # ------------------ Row 3: ACTIVE QUEUE ------------------
        self.queue_label_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.queue_label_frame.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="nsew")
        self.queue_label_frame.grid_rowconfigure(1, weight=1)
        self.queue_label_frame.grid_columnconfigure(0, weight=1)

        self.queue_title = ctk.CTkLabel(self.queue_label_frame, text="ACTIVE DOWNLOAD QUEUE", font=ctk.CTkFont(size=14, weight="bold"))
        self.queue_title.grid(row=0, column=0, padx=5, pady=(5, 10), sticky="w")

        self.queue_scroll = ctk.CTkScrollableFrame(self.queue_label_frame, label_text="")
        self.queue_scroll.grid(row=1, column=0, sticky="nsew")
        self.queue_scroll.grid_columnconfigure(0, weight=1)

        # Map of queue item UI elements to prevent redrawing the entire screen every time
        self.queue_widgets = {}

    # ------------------ Logic Methods ------------------

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

        # Setup info labels
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

        # Start download thread
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
            # If Extract Audio Only is ticked:
            # - Disable Video quality preset dropdown (or switch values)
            self.preset_dropdown.configure(state="disabled")
            # - Switch standard containers to audio only format if it was video
            if self.container_var.get() in ["mp4", "mkv", "webm"]:
                self.container_var.set("mp3")
                self.container_dropdown.configure(values=["mp3", "m4a", "flac"])
        else:
            self.preset_dropdown.configure(state="normal")
            self.container_dropdown.configure(values=["mp4", "mkv", "webm", "mp3", "m4a", "flac"])
            self.container_var.set("mp4")

        self.on_setting_changed()

    def add_url_to_queue(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter or paste a valid media URL first.")
            return

        if self.is_resolving_url:
            return

        # Start a beautiful URL inspection in the background to avoid freezing the UI
        self.is_resolving_url = True
        self.add_queue_btn.configure(text="Inspecting URL...", state="disabled")

        threading.Thread(target=self._resolve_url_worker, args=(url,), daemon=True).start()

    def _resolve_url_worker(self, url):
        try:
            metadata = fetch_metadata(url)
            self.after(0, lambda: self._resolve_url_success(metadata))
        except Exception as e:
            self.after(0, lambda: self._resolve_url_failed(str(e), url))

    def _resolve_url_success(self, metadata):
        self.is_resolving_url = False
        self.add_queue_btn.configure(text="Add to Queue", state="normal")
        self.url_entry.delete(0, tk.END)

        # Extract setting values to create download items
        save_dir = self.save_entry.get()
        preset = self.preset_var.get()
        container = self.container_var.get()
        embed_thumb = self.thumb_var.get()
        embed_subs = self.subs_var.get()
        extract_audio = self.audio_var.get()
        name_template = self.config["name_template"]

        if metadata["type"] == "playlist":
            entries = metadata["entries"]
            count = len(entries)
            confirm = messagebox.askyesno(
                "Playlist Detected",
                f"URL contains a playlist with {count} videos.\nDo you want to add ALL {count} items to the download queue?"
            )
            if confirm:
                for entry in entries:
                    self.manager.add_item(
                        url=entry["url"],
                        title=entry["title"],
                        preset=preset,
                        container=container,
                        save_dir=save_dir,
                        name_template=name_template,
                        embed_thumbnail=embed_thumb,
                        embed_subtitles=embed_subs,
                        extract_audio=extract_audio
                    )
            else:
                # Add only the playlist url as a single aggregate fallback
                self.manager.add_item(
                    url=url,
                    title=metadata["title"],
                    preset=preset,
                    container=container,
                    save_dir=save_dir,
                    name_template=name_template,
                    embed_thumbnail=embed_thumb,
                    embed_subtitles=embed_subs,
                    extract_audio=extract_audio
                )
        else:
            # Single video
            self.manager.add_item(
                url=url,
                title=metadata["title"],
                preset=preset,
                container=container,
                save_dir=save_dir,
                name_template=name_template,
                embed_thumbnail=embed_thumb,
                embed_subtitles=embed_subs,
                extract_audio=extract_audio
            )

        messagebox.showinfo("Success", "Media item(s) added to the Active Queue.")

    def _resolve_url_failed(self, error_msg, url):
        self.is_resolving_url = False
        self.add_queue_btn.configure(text="Add to Queue", state="normal")

        confirm = messagebox.askyesno(
            "Metadata Inspection Failed",
            f"Failed to fetch video details from this URL.\nError: {error_msg}\n\nDo you want to add the raw URL to the queue anyway?"
        )
        if confirm:
            save_dir = self.save_entry.get()
            preset = self.preset_var.get()
            container = self.container_var.get()
            embed_thumb = self.thumb_var.get()
            embed_subs = self.subs_var.get()
            extract_audio = self.audio_var.get()
            name_template = self.config["name_template"]

            # Use URL as title
            self.manager.add_item(
                url=url,
                title=url,
                preset=preset,
                container=container,
                save_dir=save_dir,
                name_template=name_template,
                embed_thumbnail=embed_thumb,
                embed_subtitles=embed_subs,
                extract_audio=extract_audio
            )

    # ------------------ Active Queue UI Render Logic ------------------

    def on_queue_updated(self):
        """Thread-safe trigger to update/refresh the queue scroll container."""
        self.after(0, self.refresh_queue_view)

    def refresh_queue_view(self):
        # We want to reconcile the queue items securely and efficiently.
        with self.manager.lock:
            active_items = list(self.manager.queue)

        # Step A: Delete widgets of items that are no longer in queue (if items are removed)
        existing_ids = {item.id for item in active_items}
        for item_id in list(self.queue_widgets.keys()):
            if item_id not in existing_ids:
                for widget in self.queue_widgets[item_id]["widgets"]:
                    widget.destroy()
                self.queue_widgets[item_id]["frame"].destroy()
                del self.queue_widgets[item_id]

        # Step B: Render / Update elements for active items
        for idx, item in enumerate(active_items):
            # Check if this item already has created widgets
            if item.id not in self.queue_widgets:
                # Create a frame for the row
                item_frame = ctk.CTkFrame(self.queue_scroll)
                item_frame.grid(row=idx, column=0, padx=5, pady=5, sticky="ew")
                item_frame.grid_columnconfigure(0, weight=1)

                # Title label
                title_lbl = ctk.CTkLabel(
                    item_frame,
                    text=f"{item.id}. {item.title}",
                    anchor="w",
                    font=ctk.CTkFont(size=12, weight="bold")
                )
                title_lbl.grid(row=0, column=0, columnspan=2, padx=12, pady=(10, 2), sticky="ew")

                # Progress bar
                prog_bar = ctk.CTkProgressBar(item_frame)
                prog_bar.grid(row=1, column=0, padx=12, pady=5, sticky="ew")
                prog_bar.set(0)

                # Info label (Progress%, speed, eta)
                info_lbl = ctk.CTkLabel(item_frame, text="Waiting in queue...", font=ctk.CTkFont(size=11), text_color="#aaaaaa")
                info_lbl.grid(row=2, column=0, padx=12, pady=(2, 10), sticky="w")

                # Action Buttons container (on the right of row, grid alignment)
                btns_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
                btns_frame.grid(row=1, column=1, rowspan=2, padx=12, pady=5, sticky="e")

                pause_btn = ctk.CTkButton(
                    btns_frame,
                    text="Pause",
                    width=70,
                    command=lambda i=item.id: self.manager.pause_item(i)
                )
                pause_btn.grid(row=0, column=0, padx=5, pady=2)

                cancel_btn = ctk.CTkButton(
                    btns_frame,
                    text="Cancel",
                    width=70,
                    fg_color="#B22222",
                    hover_color="#8B0000",
                    command=lambda i=item.id: self.manager.cancel_item(i)
                )
                cancel_btn.grid(row=0, column=1, padx=5, pady=2)

                self.queue_widgets[item.id] = {
                    "frame": item_frame,
                    "title_lbl": title_lbl,
                    "prog_bar": prog_bar,
                    "info_lbl": info_lbl,
                    "pause_btn": pause_btn,
                    "cancel_btn": cancel_btn,
                    "widgets": [title_lbl, prog_bar, info_lbl, pause_btn, cancel_btn, btns_frame]
                }

            # Always update current properties of widgets
            widget_bundle = self.queue_widgets[item.id]

            # Position the frame correctly if list orders shift
            widget_bundle["frame"].grid(row=idx, column=0, padx=5, pady=5, sticky="ew")

            # Update title in case it resolved later
            widget_bundle["title_lbl"].configure(text=f"{item.id}. {item.title}")

            # Update progress bar
            widget_bundle["prog_bar"].set(item.percent / 100.0)

            # Set Info line
            if item.status == "Downloading":
                info_text = f"Downloading: {item.percent}% | {item.speed} | ETA: {item.eta}"
                info_color = "#3a7ebf"
            elif item.status == "Paused":
                info_text = "Paused"
                info_color = "#e59866"
            elif item.status == "Completed":
                info_text = f"Completed successfully! Saved to {item.save_dir}"
                info_color = "#2ecc71"
            elif item.status == "Cancelled":
                info_text = "Cancelled"
                info_color = "#95a5a6"
            elif item.status == "Failed":
                info_text = f"Failed: {item.error_message}"
                info_color = "#e74c3c"
            else:  # Waiting
                info_text = "Waiting in queue..."
                info_color = "#aaaaaa"

            widget_bundle["info_lbl"].configure(text=info_text, text_color=info_color)

            # Update Pause/Resume button state
            if item.status == "Downloading":
                widget_bundle["pause_btn"].configure(text="Pause", state="normal", command=lambda i=item.id: self.manager.pause_item(i))
            elif item.status in ["Paused", "Cancelled", "Failed"]:
                widget_bundle["pause_btn"].configure(text="Resume", state="normal", command=lambda i=item.id: self.manager.resume_item(i))
            else:
                # Waiting or Completed
                widget_bundle["pause_btn"].configure(text="Pause", state="disabled")


if __name__ == "__main__":
    app = App()
    app.mainloop()
