import os
import re
import sys
import signal
import subprocess
import threading
import time
from src.binary_manager import get_binary_paths, check_binaries_exist

# Regular expression to parse yt-dlp progress line
# Examples:
# [download]  45.1% of  124.50MiB at   12.41MiB/s ETA 00:15
# [download]   1.2% of ~50.2MiB at  850.3KiB/s ETA 01:02
PROGRESS_RE = re.compile(
    r"\[download\]\s+(?P<percent>\d+(?:\.\d+)?)%\s+of\s+~?(?P<size>\d+(?:\.\d+)?[a-zA-Z]+)\s+at\s+(?P<speed>[^\s]+)\s+ETA\s+(?P<eta>[^\s]+)"
)

# Resilient fallback regex if size or of is missing
PERCENT_RE = re.compile(r"\[download\]\s+(?P<percent>\d+(?:\.\d+)?)%")
SPEED_RE = re.compile(r"at\s+(?P<speed>[^\s]+)")
ETA_RE = re.compile(r"ETA\s+(?P<eta>[^\s]+)")

def parse_progress_line(line):
    """
    Parses a single line of yt-dlp output and returns a dictionary with progress info:
    { "percent": float, "speed": str, "eta": str, "size": str }
    Returns None if line does not match.
    """
    match = PROGRESS_RE.search(line)
    if match:
        return {
            "percent": float(match.group("percent")),
            "size": match.group("size"),
            "speed": match.group("speed"),
            "eta": match.group("eta")
        }

    # Fallback parsing
    pct_match = PERCENT_RE.search(line)
    if pct_match:
        percent = float(pct_match.group("percent"))
        speed_match = SPEED_RE.search(line)
        eta_match = ETA_RE.search(line)

        return {
            "percent": percent,
            "size": "Unknown",
            "speed": speed_match.group("speed") if speed_match else "N/A",
            "eta": eta_match.group("eta") if eta_match else "N/A"
        }

    return None

class DownloadItem:
    def __init__(self, item_id, url, title, preset, container, save_dir, name_template,
                 embed_thumbnail=False, embed_subtitles=False, extract_audio=False):
        self.id = item_id
        self.url = url
        self.title = title
        self.preset = preset
        self.container = container
        self.save_dir = save_dir
        self.name_template = name_template
        self.embed_thumbnail = embed_thumbnail
        self.embed_subtitles = embed_subtitles
        self.extract_audio = extract_audio

        # State
        self.status = "Waiting"  # Waiting, Downloading, Paused, Completed, Cancelled, Failed
        self.percent = 0.0
        self.speed = "0 KB/s"
        self.eta = "--:--"
        self.size = "Unknown"
        self.error_message = ""
        self.process = None
        self.thread = None

class DownloadManager:
    def __init__(self, max_concurrent=2):
        self.queue = []
        self.max_concurrent = max_concurrent
        self.lock = threading.Lock()
        self.is_running = True
        self.queue_thread = threading.Thread(target=self._process_queue_loop, daemon=True)
        self.queue_thread.start()

        # UI callback to update the screen
        self.update_callback = None

    def set_update_callback(self, callback):
        self.update_callback = callback

    def trigger_update(self):
        if self.update_callback:
            try:
                self.update_callback()
            except Exception:
                pass

    def add_item(self, url, title, preset, container, save_dir, name_template,
                 embed_thumbnail=False, embed_subtitles=False, extract_audio=False):
        with self.lock:
            item_id = str(len(self.queue) + 1)
            item = DownloadItem(
                item_id, url, title, preset, container, save_dir, name_template,
                embed_thumbnail, embed_subtitles, extract_audio
            )
            self.queue.append(item)
            self.trigger_update()
            return item

    def start_all(self):
        with self.lock:
            for item in self.queue:
                if item.status in ["Paused", "Cancelled", "Failed"]:
                    item.status = "Waiting"
                    item.percent = 0.0
                    item.speed = "0 KB/s"
                    item.eta = "--:--"
            self.trigger_update()

    def pause_all(self):
        with self.lock:
            for item in self.queue:
                if item.status == "Downloading":
                    self._pause_item_unlocked(item)
                elif item.status == "Waiting":
                    item.status = "Paused"
            self.trigger_update()

    def cancel_all(self):
        with self.lock:
            for item in self.queue:
                if item.status in ["Downloading", "Waiting", "Paused"]:
                    self._cancel_item_unlocked(item)
            self.trigger_update()

    def pause_item(self, item_id):
        with self.lock:
            item = self._get_item_unlocked(item_id)
            if item:
                self._pause_item_unlocked(item)
            self.trigger_update()

    def resume_item(self, item_id):
        with self.lock:
            item = self._get_item_unlocked(item_id)
            if item and item.status in ["Paused", "Cancelled", "Failed", "Waiting"]:
                item.status = "Waiting"
                item.error_message = ""
            self.trigger_update()

    def cancel_item(self, item_id):
        with self.lock:
            item = self._get_item_unlocked(item_id)
            if item:
                self._cancel_item_unlocked(item)
            self.trigger_update()

    def _get_item_unlocked(self, item_id):
        for item in self.queue:
            if item.id == item_id:
                return item
        return None

    def _pause_item_unlocked(self, item):
        if item.status == "Downloading" and item.process:
            # Terminate the process. The thread will handle the cleanup and set the status to "Paused".
            try:
                if sys.platform == "win32":
                    item.process.terminate()
                else:
                    item.process.terminate()
            except Exception:
                pass
        item.status = "Paused"
        item.speed = "Paused"
        item.eta = "--:--"

    def _cancel_item_unlocked(self, item):
        if item.status == "Downloading" and item.process:
            try:
                item.process.terminate()
            except Exception:
                pass
        item.status = "Cancelled"
        item.percent = 0.0
        item.speed = "Cancelled"
        item.eta = "--:--"

    def _process_queue_loop(self):
        while self.is_running:
            time.sleep(0.5)

            with self.lock:
                active_count = sum(1 for item in self.queue if item.status == "Downloading")

                if active_count < self.max_concurrent:
                    # Find next waiting item
                    next_item = None
                    for item in self.queue:
                        if item.status == "Waiting":
                            next_item = item
                            break

                    if next_item:
                        next_item.status = "Downloading"
                        next_item.thread = threading.Thread(
                            target=self._download_worker,
                            args=(next_item,),
                            daemon=True
                        )
                        next_item.thread.start()
                        self.trigger_update()

    def _download_worker(self, item):
        if not check_binaries_exist():
            item.status = "Failed"
            item.error_message = "Binaries are not ready."
            self.trigger_update()
            return

        yt_dlp_path, ffmpeg_path = get_binary_paths()

        # Build command
        # Standard: Output directory and format
        cmd = [
            yt_dlp_path,
            "--ffmpeg-location", ffmpeg_path,
            "--newline",              # Ensures status updates are written on separate lines
            "--progress",             # Forces progress output
            "--no-playlist"           # Make sure we only download this specific video if URL contains playlist ID too
        ]

        # Output directory and name template
        os.makedirs(item.save_dir, exist_ok=True)
        output_template = os.path.join(item.save_dir, item.name_template)
        cmd.extend(["-o", output_template])

        # Audio Extraction / Presets / Containers
        if item.extract_audio:
            cmd.append("-x")
            cmd.extend(["--audio-format", item.container])
        else:
            # Preset format selection
            if item.preset == "Best Video + Audio":
                cmd.extend(["-f", "bv*+ba/b"])
            elif item.preset == "1080p":
                cmd.extend(["-f", "bv*[height<=1080]+ba/b[height<=1080]"])
            elif item.preset == "4K":
                cmd.extend(["-f", "bv*[height<=2160]+ba/b[height<=2160]"])
            elif item.preset == "720p":
                cmd.extend(["-f", "bv*[height<=720]+ba/b[height<=720]"])
            else:
                cmd.extend(["-f", "bv*+ba/b"])

            # Merge format / container
            if item.container:
                cmd.extend(["--merge-output-format", item.container])

        # Subtitles, thumbnail, and metadata tagging
        if item.embed_thumbnail:
            cmd.append("--embed-thumbnail")
        if item.embed_subtitles:
            cmd.extend(["--write-subs", "--embed-subs"])
        if not item.extract_audio:  # Embed video metadata if not pure audio extraction
            cmd.append("--embed-metadata")

        # Add URL at the end
        cmd.append(item.url)

        # Spawn process
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW

        try:
            item.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=creationflags
            )
        except Exception as e:
            with self.lock:
                item.status = "Failed"
                item.error_message = f"Failed to start downloader: {str(e)}"
            self.trigger_update()
            return

        # Parse output line-by-line
        err_lines = []
        while True:
            line = item.process.stdout.readline()
            if not line:
                break

            # Check if state has changed from downloading (e.g. paused or cancelled externally)
            with self.lock:
                if item.status != "Downloading":
                    # Process was stopped/terminated already
                    break

            # Parse progress
            progress_data = parse_progress_line(line)
            if progress_data:
                with self.lock:
                    if item.status == "Downloading":
                        item.percent = progress_data["percent"]
                        item.speed = progress_data["speed"]
                        item.eta = progress_data["eta"]
                        item.size = progress_data["size"]
                self.trigger_update()

        # Read remaining stderr
        stderr_thread = threading.Thread(
            target=lambda: err_lines.extend(item.process.stderr.readlines()),
            daemon=True
        )
        stderr_thread.start()
        stderr_thread.join(timeout=1.0)

        # Wait for exit code
        returncode = item.process.wait()

        with self.lock:
            # If state was cancelled or paused externally, keep that state
            if item.status in ["Paused", "Cancelled"]:
                pass
            elif returncode == 0:
                item.status = "Completed"
                item.percent = 100.0
                item.speed = "Done"
                item.eta = "00:00"
            else:
                item.status = "Failed"
                # Extract some meaningful error from err_lines
                err_text = "".join(err_lines).strip()
                if "Unsupported URL" in err_text:
                    item.error_message = "Unsupported video site/URL."
                elif "Private video" in err_text:
                    item.error_message = "Video is private."
                elif "Sign in" in err_text:
                    item.error_message = "Requires authentication/sign-in."
                else:
                    # Provide short excerpt of the error
                    item.error_message = err_text[:200] if err_text else f"Exit code {returncode}"

        self.trigger_update()
