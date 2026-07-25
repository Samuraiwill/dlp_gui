import os
import sys
import platform
import urllib.request
import zipfile
import stat

def get_platform_info():
    """
    Returns (os_name, arch) where os_name is 'windows', 'macos', or 'linux',
    and arch is '64' or 'arm64'.
    """
    system = platform.system().lower()
    machine = platform.machine().lower()

    if "win" in system:
        os_name = "windows"
    elif "darwin" in system:
        os_name = "macos"
    else:
        os_name = "linux"

    if "arm" in machine or "aarch64" in machine:
        arch = "arm64"
    else:
        arch = "64"

    return os_name, arch

def get_bin_dir():
    """
    Returns the path to the binary folder.
    First checks local `./bin/` directory, then defaults to `~/.yt_dlp_desktop_gui/bin/`.
    """
    local_bin = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin"))
    if os.path.exists(os.path.join(local_bin, "yt-dlp")) or os.path.exists(os.path.join(local_bin, "yt-dlp.exe")):
        return local_bin

    user_bin = os.path.expanduser("~/.yt_dlp_desktop_gui/bin")
    os.makedirs(user_bin, exist_ok=True)
    return user_bin

def get_binary_paths():
    """
    Returns (yt_dlp_path, ffmpeg_path) based on current platform.
    Does not guarantee they exist; call check_binaries_exist() for that.
    """
    bin_dir = get_bin_dir()
    os_name, _ = get_platform_info()

    if os_name == "windows":
        yt_dlp_path = os.path.join(bin_dir, "yt-dlp.exe")
        ffmpeg_path = os.path.join(bin_dir, "ffmpeg.exe")
    else:
        yt_dlp_path = os.path.join(bin_dir, "yt-dlp")
        ffmpeg_path = os.path.join(bin_dir, "ffmpeg")

    return yt_dlp_path, ffmpeg_path

def check_binaries_exist():
    """
    Returns True if both yt-dlp and ffmpeg are found and executable (if unix).
    """
    yt_dlp_path, ffmpeg_path = get_binary_paths()

    if not os.path.exists(yt_dlp_path) or not os.path.exists(ffmpeg_path):
        return False

    # Check permissions on Unix
    os_name, _ = get_platform_info()
    if os_name != "windows":
        try:
            yt_dlp_stat = os.stat(yt_dlp_path)
            ffmpeg_stat = os.stat(ffmpeg_path)
            # Ensure user executable bit is set
            if not (yt_dlp_stat.st_mode & stat.S_IXUSR) or not (ffmpeg_stat.st_mode & stat.S_IXUSR):
                return False
        except Exception:
            return False

    return True

def _download_file(url, target_path, progress_callback=None, step_name=""):
    """
    Downloads file from url to target_path with optional progress callback.
    """
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    )

    with urllib.request.urlopen(req) as response:
        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192
        downloaded = 0

        with open(target_path, 'wb') as out_file:
            while True:
                buffer = response.read(block_size)
                if not buffer:
                    break
                downloaded += len(buffer)
                out_file.write(buffer)
                if progress_callback and total_size > 0:
                    percent = int((downloaded / total_size) * 100)
                    progress_callback(f"{step_name}: {percent}%", percent)

def download_binaries(progress_callback=None):
    """
    Downloads yt-dlp and ffmpeg binaries for the current platform.
    Calls progress_callback(status_message, percent_complete).
    """
    bin_dir = get_bin_dir()
    os_name, arch = get_platform_info()
    yt_dlp_path, ffmpeg_path = get_binary_paths()

    # Define URLs
    if os_name == "windows":
        yt_dlp_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
        ffmpeg_url = "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffmpeg-4.4.1-win-64.zip"
    elif os_name == "macos":
        yt_dlp_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
        ffmpeg_url = "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffmpeg-4.4.1-osx-64.zip"
    else:  # Linux
        yt_dlp_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
        ffmpeg_url = "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffmpeg-4.4.1-linux-64.zip"

    # Download yt-dlp
    if not os.path.exists(yt_dlp_path):
        if progress_callback:
            progress_callback("Downloading yt-dlp...", 0)
        _download_file(yt_dlp_url, yt_dlp_path, progress_callback, "Downloading yt-dlp")

        # Make executable
        if os_name != "windows":
            st = os.stat(yt_dlp_path)
            os.chmod(yt_dlp_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # Download ffmpeg zip and extract
    if not os.path.exists(ffmpeg_path):
        ffmpeg_zip_path = os.path.join(bin_dir, "ffmpeg.zip")
        if progress_callback:
            progress_callback("Downloading ffmpeg...", 0)
        _download_file(ffmpeg_url, ffmpeg_zip_path, progress_callback, "Downloading ffmpeg")

        if progress_callback:
            progress_callback("Extracting ffmpeg...", 95)

        with zipfile.ZipFile(ffmpeg_zip_path, 'r') as zip_ref:
            zip_ref.extractall(bin_dir)

        # Clean up zip
        try:
            os.remove(ffmpeg_zip_path)
        except Exception:
            pass

        # Make executable
        if os_name != "windows":
            if os.path.exists(ffmpeg_path):
                st = os.stat(ffmpeg_path)
                os.chmod(ffmpeg_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    if progress_callback:
        progress_callback("Binaries ready!", 100)
    return True
