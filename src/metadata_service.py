import os
import subprocess
import json
import sys

try:
    from src.binary_manager import get_binary_paths, check_binaries_exist, get_python_interpreter
except ImportError:
    from binary_manager import get_binary_paths, check_binaries_exist, get_python_interpreter

def fetch_metadata(url):
    """
    Executes yt-dlp with --dump-json and --flat-playlist to fetch URL metadata.
    Returns a dictionary of parsed metadata, or raises an Exception if failed.
    """
    if not check_binaries_exist():
        raise Exception("yt-dlp and ffmpeg binaries are not ready yet.")

    yt_dlp_path, _, _ = get_binary_paths()

    # On macOS/Linux, running the downloaded 'yt-dlp' zipapp script directly can trigger
    # macOS Gatekeeper, Quarantine, or shebang/permission hangs. Running it through the system
    # Python interpreter completely bypasses these operating system restrictions.
    if sys.platform == "win32":
        cmd = [yt_dlp_path]
    else:
        python_interpreter = get_python_interpreter()
        cmd = [python_interpreter, yt_dlp_path]

    cmd.extend([
        "--no-check-certificate",
        "--dump-json",
        "--flat-playlist",
        "--no-warnings",
        url
    ])

    # Run the process
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore',
            creationflags=creationflags
        )
        # Add a 30-second timeout to prevent the process from hanging indefinitely
        stdout, stderr = process.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except Exception:
            pass
        raise Exception("Metadata inspection timed out (30 seconds). Please check your internet connection.")
    except Exception as e:
        raise Exception(f"Failed to start metadata inspector process: {str(e)}")

    if process.returncode != 0:
        err_msg = stderr.strip() if stderr else "Unknown error"
        raise Exception(f"yt-dlp failed to inspect URL: {err_msg}")

    if not stdout.strip():
        raise Exception("No metadata returned from yt-dlp.")

    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise Exception("No metadata returned from yt-dlp.")

    try:
        if len(lines) == 1:
            data = json.loads(lines[0])

            if data.get("_type") == "playlist":
                return {
                    "type": "playlist",
                    "title": data.get("title") or data.get("playlist_title") or "Unnamed Playlist",
                    "entries": [
                        {
                            "title": entry.get("title") or f"Video #{i+1}",
                            "url": entry.get("url") or entry.get("webpage_url") or f"https://youtube.com/watch?v={entry.get('id')}" if entry.get('id') else url,
                            "id": entry.get("id"),
                            "duration": entry.get("duration")
                        }
                        for i, entry in enumerate(data.get("entries", []))
                    ]
                }
            else:
                return {
                    "type": "video",
                    "title": data.get("title") or "Unnamed Video",
                    "duration": data.get("duration"),
                    "thumbnail": data.get("thumbnail"),
                    "url": data.get("webpage_url") or url,
                    "id": data.get("id")
                }
        else:
            entries = []
            playlist_title = "Multiple items"
            for i, line in enumerate(lines):
                try:
                    item = json.loads(line)
                    entries.append({
                        "title": item.get("title") or f"Video #{i+1}",
                        "url": item.get("url") or item.get("webpage_url") or f"https://youtube.com/watch?v={item.get('id')}" if item.get('id') else url,
                        "id": item.get("id"),
                        "duration": item.get("duration")
                    })
                except Exception:
                    continue
            return {
                "type": "playlist",
                "title": playlist_title,
                "entries": entries
            }
    except Exception as e:
        raise Exception(f"Failed to parse metadata JSON: {str(e)}")
