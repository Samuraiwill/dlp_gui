# yt-dlp Desktop Studio 🚀

A modern, fast, and **completely self-contained** desktop GUI application for `yt-dlp` designed for cross-platform plug-and-play usability. Built with **CustomTkinter** (Python) and bundled with **PyInstaller**, the application manages its own dependencies (`yt-dlp` and `ffmpeg`) automatically, ensuring users never have to run terminal package installation commands.

---

## ✨ Features
* **Zero System Dependencies:** Automatically downloads and configures target-platform compatible `yt-dlp` and `ffmpeg` static binaries upon first launch.
* **Modern GUI Layout:** Sleek dark/light theme, built-in clipboard auto-pasting, custom download directory chooser, and format/preset selector.
* **Granular Options & Containers:** Toggle subtitles, thumbnail embedding, video metadata tag embedding, or audio-only extraction format (MP3, FLAC, M4A).
* **Interactive Active Queue:** Real-time download progress bar, downloading speeds (e.g. `MB/s`), accurate ETA, individual controls ([Pause], [Resume], [Cancel]) and global action buttons ([Start All], [Pause All], [Cancel All]).
* **Multi-threaded Core:** Background worker queues prevent any UI freezing during URL inspection or download progress.

---

## 🛠️ Tech Stack & Architecture
* **Frontend/GUI:** [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) (a modern wrapper for Tkinter offering custom styles, dark mode, widgets, and canvas elements).
* **Downloader Engine:** Native `yt-dlp` binary invoked via secure asynchronous subprocess pipes.
* **Binary Manager:** Auto-fetches up-to-date compiled binaries:
  * `yt-dlp` from official releases.
  * `ffmpeg` static builds from the precompiled `ffbinaries` release distributions.
* **Build System:** `PyInstaller` packages the entire environment into a standalone, single-file native executable (`.exe`, `.app`, or binary).

---

## 📂 Project Structure
```text
├── .github/workflows/
│   └── build.yml               # GitHub Actions CI/CD cross-platform release pipeline
├── src/
│   ├── binary_manager.py       # Detects OS/arch, auto-downloads and permissions engine binaries
│   ├── metadata_service.py     # Invokes --dump-json in background to parse URL elements & titles
│   ├── downloader.py           # Constructs yt-dlp arguments, regex-parses stdout logs, manages threads
│   └── gui.py                  # Main CustomTkinter UI & thread-safe state reconciliation
├── tests/
│   ├── test_binary_manager.py  # Tests architecture resolution and platform detection
│   └── test_parser.py          # Tests regex progress parsing and queue status operations
├── .gitignore                  # Git exclusions for builds and caches
├── requirements.txt            # Project dependencies
├── build.py                    # Build orchestration script executing PyInstaller commands
└── README.md                   # Project documentation
```

---

## 🚀 Running locally

### Prerequisites
Make sure you have **Python 3.10+** installed on your system.

### Setup & Run
1. **Clone the repository:**
   ```bash
   git clone https://github.com/Samuraiwill/dlp_gui.git
   cd dlp_gui
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Launch the Application:**
   ```bash
   python -m src.gui
   ```

---

## 🧪 Testing
The project includes a robust test suite covering binary downloading structures, regex progress stdout line parsing, and background queue managers.

To execute the tests:
```bash
python -m pytest
```

---

## 📦 Building Standalone Executables
We package the application into platform-native executable binaries using PyInstaller:

```bash
python build.py
```
After completion, your standalone executable will be located in the `dist/` directory:
* **Windows:** `dist/yt-dlp-desktop-gui.exe`
* **macOS:** `dist/yt-dlp-desktop-gui` (Mac package)
* **Linux:** `dist/yt-dlp-desktop-gui` (Standalone binary)

---

## ⚙️ CI/CD Build Automation
A full GitHub Actions workflow is provided under `.github/workflows/build.yml`. On every push or pull request to the main branches, the pipeline automatically compiles platform-native standalone releases for Windows, macOS, and Linux, saving them as downloadable build artifacts.
