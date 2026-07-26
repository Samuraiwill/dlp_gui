import os
import sys
import subprocess

def run_build():
    print("=== Starting PyInstaller Build ===")

    # Entry point
    entry_point = os.path.join("src", "gui.py")
    if not os.path.exists(entry_point):
        print(f"Error: Entrypoint {entry_point} not found!")
        sys.exit(1)

    # Build options
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=yt-dlp-desktop-gui",
        "--collect-all=customtkinter",
        "--icon=assets/app_icon.png",
        entry_point
    ]

    print(f"Executing: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True)
        print("=== Build Completed Successfully! ===")
        print("You can find the standalone executable inside the 'dist' directory.")
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_build()
