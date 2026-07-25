import os
import re
import sys
import subprocess
import threading
import time

try:
    from src.binary_manager import get_binary_paths, check_binaries_exist, get_python_interpreter
except ImportError:
    from binary_manager import get_binary_paths, check_binaries_exist, get_python_interpreter

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
        text_eta_match = ETA_RE.search(line)

        return {
            "percent": percent,
            "size": "Unknown",
            "speed": speed_match.group("speed") if speed_match else "N/A",
            "eta": text_eta_match.group("eta") if text_eta_match else "N/A"
        }

    return None


class DirectDownloader:
    """
    A single direct downloader running yt-dlp in a background thread.
    Streams real-time console logs and progress status back to the main UI thread.
    """
    def __init__(self, url, save_dir, preset, container, embed_thumbnail,
                 embed_subtitles, extract_audio, name_template,
                 progress_callback, log_callback, completion_callback):
        self.url = url
        self.save_dir = save_dir
        self.preset = preset
        self.container = container
        self.embed_thumbnail = embed_thumbnail
        self.embed_subtitles = embed_subtitles
        self.extract_audio = extract_audio
        self.name_template = name_template

        # Callbacks
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.completion_callback = completion_callback

        # Thread & Process state
        self.process = None
        self.thread = None
        self.is_cancelled = False

    def start(self):
        """Launches the download worker thread."""
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def cancel(self):
        """Cancels the current active download process securely."""
        self.is_cancelled = True
        if self.process:
            try:
                self.process.terminate()
            except Exception:
                pass

    def _run(self):
        if not check_binaries_exist():
            self.completion_callback("Failed", "yt-dlp and ffmpeg engine files are not ready.")
            return

        yt_dlp_path, ffmpeg_path, ffprobe_path = get_binary_paths()

        # Build standard argument list
        if sys.platform == "win32":
            cmd = [yt_dlp_path]
        else:
            python_interpreter = get_python_interpreter()
            cmd = [python_interpreter, yt_dlp_path]

        # Get directory containing ffmpeg and ffprobe
        ffmpeg_dir = os.path.dirname(ffmpeg_path)

        cmd.extend([
            "--ffmpeg-location", ffmpeg_dir,
            "--no-check-certificate",
            "--newline",              # Ensures output line spacing is clear
            "--progress"              # Forces progress log details
        ])

        # Set output template
        os.makedirs(self.save_dir, exist_ok=True)
        output_template = os.path.join(self.save_dir, self.name_template)
        cmd.extend(["-o", output_template])

        # Audio Extraction / Presets / Containers
        if self.extract_audio:
            cmd.append("-x")
            cmd.extend(["--audio-format", self.container])
        else:
            if self.preset == "Best Video + Audio":
                cmd.extend(["-f", "bv*+ba/b"])
            elif self.preset == "1080p":
                cmd.extend(["-f", "bv*[height<=1080]+ba/b[height<=1080]"])
            elif self.preset == "4K":
                cmd.extend(["-f", "bv*[height<=2160]+ba/b[height<=2160]"])
            elif self.preset == "720p":
                cmd.extend(["-f", "bv*[height<=720]+ba/b[height<=720]"])
            else:
                cmd.extend(["-f", "bv*+ba/b"])

            if self.container:
                cmd.extend(["--merge-output-format", self.container])

        # Subtitles, thumbnail, and metadata tags
        if self.embed_thumbnail:
            cmd.append("--embed-thumbnail")
        if self.embed_subtitles:
            cmd.extend(["--write-subs", "--embed-subs"])
        if not self.extract_audio:
            cmd.append("--embed-metadata")

        # Add URL
        cmd.append(self.url)

        # Log command start
        self.log_callback(f"Executing: {' '.join(cmd)}\n\n")

        # Spawn process
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=creationflags
            )
        except Exception as e:
            self.completion_callback("Failed", f"Failed to launch yt-dlp downloader: {str(e)}")
            return

        # Parse output line-by-line
        err_lines = []

        # Read stdout in a background loop
        while True:
            line = self.process.stdout.readline()
            if not line:
                break

            # Stream raw line to GUI log
            self.log_callback(line)

            # Parse progress metrics
            prog = parse_progress_line(line)
            if prog:
                self.progress_callback(prog)

        # Read stderr
        stderr_thread = threading.Thread(
            target=lambda: err_lines.extend(self.process.stderr.readlines()),
            daemon=True
        )
        stderr_thread.start()
        stderr_thread.join(timeout=1.0)

        # Wait for termination
        returncode = self.process.wait()

        if self.is_cancelled:
            self.completion_callback("Cancelled", "Download aborted by user.")
        elif returncode == 0:
            self.completion_callback("Completed", "")
        else:
            err_text = "".join(err_lines).strip()
            if not err_text:
                err_text = f"Process terminated with exit code {returncode}."
            self.completion_callback("Failed", err_text[:250])
