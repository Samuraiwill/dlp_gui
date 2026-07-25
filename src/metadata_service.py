import os
import subprocess
import json
import sys
from src.binary_manager import get_binary_paths, check_binaries_exist

def fetch_metadata(url):
    """
    Executes yt-dlp with --dump-json and --flat-playlist to fetch URL metadata.
    Returns a dictionary of parsed metadata, or raises an Exception if failed.
    """
    if not check_binaries_exist():
        raise Exception("yt-dlp and ffmpeg binaries are not ready yet.")

    yt_dlp_path, _ = get_binary_paths()

    # We use --flat-playlist so that for playlists, we get a quick flat listing
    # instead of downloading info for every single video.
    cmd = [
        yt_dlp_path,
        "--dump-json",
        "--flat-playlist",
        "--no-warnings",
        url
    ]

    # Run the process
    # On Windows, we use creationflags=subprocess.CREATE_NO_WINDOW to avoid flashing console windows.
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
        stdout, stderr = process.communicate()
    except Exception as e:
        raise Exception(f"Failed to start metadata inspector process: {str(e)}")

    if process.returncode != 0:
        err_msg = stderr.strip() if stderr else "Unknown error"
        raise Exception(f"yt-dlp failed to inspect URL: {err_msg}")

    if not stdout.strip():
        raise Exception("No metadata returned from yt-dlp.")

    # Standard output may contain multiple JSON lines if it returns multiple items.
    # Usually --dump-json --flat-playlist returns one JSON object for a single video,
    # or one JSON object representing the playlist (which contains flat entries).
    # Sometimes it returns multiple JSON lines (one per video). Let's support both.
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise Exception("No metadata returned from yt-dlp.")

    # Attempt to parse first line or multiple lines
    try:
        # If there's only one line, parse it.
        if len(lines) == 1:
            data = json.loads(lines[0])

            # If it's a playlist but flat-playlist entries are inline:
            if data.get("_type") == "playlist":
                # It's a playlist
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
                # It's a single video
                return {
                    "type": "video",
                    "title": data.get("title") or "Unnamed Video",
                    "duration": data.get("duration"),
                    "thumbnail": data.get("thumbnail"),
                    "url": data.get("webpage_url") or url,
                    "id": data.get("id")
                }
        else:
            # Multiple lines (e.g. individual items in playlist output)
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
