# Feature Request: Self-Contained Desktop GUI for yt-dlp

## 📌 Executive Summary
Build a lightweight, cross-platform desktop GUI wrapper for `yt-dlp` designed for immediate plug-and-play usability. The key requirement is that **the application must be completely self-contained**—it should **NOT** require the end-user to manually install system dependencies via package managers (e.g., `brew install yt-dlp` or `apt install ffmpeg`). All necessary binaries must be bundled or automatically managed behind the scenes.

---

## 🎯 Key Design & Architecture Requirements

### 1. Zero External Dependencies (Self-Contained Execution)
* **Embedded Binaries:** Embed `yt-dlp` and `ffmpeg` binaries within the application bundle, or implement a background auto-fetch mechanism on first launch that downloads platform-specific executable binaries into an application data folder.
* **Standalone Application Build:** Package the GUI application as portable distribution files:
  * **macOS:** `.dmg` / `.app` (universal binary or arm64/x64 builds)
  * **Windows:** Portable `.exe` or installer setup
  * **Linux:** `.AppImage` or standalone binary

### 2. Core Functional Requirements
* **Single & Playlist URL Parsing:** Text input field with auto-paste capability when a valid URL is copied to the clipboard.
* **Format & Quality Selector:**
  * Quick presets: "Best Video + Audio", "Audio Only (MP3)", "1080p", "4K", etc.
  * Granular dropdowns for container selection (`.mp4`, `.mkv`, `.webm`, `.mp3`, `.m4a`, `.flac`).
* **Interactive Download Manager:**
  * Active queue displaying progress bar, download speed (e.g., `MB/s`), ETA, and status indicator.
  * Pause, resume, and cancel buttons per item and for the global queue.
* **Output Configuration:**
  * Custom output folder selection with a persistent default preference.
  * File naming template selector (e.g., `%(title)s [%(id)s].%(ext)s`).
* **Subtitles & Metadata Embed:**
  * Toggle for embedding thumbnail artwork, video tags, and closed-caption subtitles into the output container.

---

## 🖥️ UI/UX Specification

```
+-----------------------------------------------------------------------+
|  yt-dlp Desktop Studio                                                |
+-----------------------------------------------------------------------+
|  Media URL: [ https://www.youtube.com/watch?v=...          ] [ Paste ]|
+-----------------------------------------------------------------------+
|  Preset: [ Video + Audio (Best) ▾ ]  Container: [ MP4 ▾ ]            |
|  Save To: [ ~/Downloads/Media                 ] [ Browse... ]          |
|  [x] Embed Thumbnail   [x] Embed Subtitles   [ ] Extract Audio Only  |
+-----------------------------------------------------------------------+
|  [ Add to Queue ]                                    [ Start All ]    |
+-----------------------------------------------------------------------+
|  ACTIVE QUEUE                                                         |
|  -------------------------------------------------------------------  |
|  1. Sample Video Title                                                |
|     Progress: [========================........] 68% | 12.4 MB/s      |
|  2. Audio Track - Ska / Pop Punk Demo                                 |
|     Progress: [ Waiting in queue...            ]                      |
+-----------------------------------------------------------------------+
```

---

## 🛠️ Technical Stack Recommendations

| Layer | Preferred Options | Rationale |
| :--- | :--- | :--- |
| **Framework** | **Tauri + React/TS** *or* **Electron** *or* **CustomTkinter/PyQt** | Tauri offers ultra-small binary sizes (<15MB) and native execution speed; Python solutions are fast to prototype wrapper scripts. |
| **Engine** | `yt-dlp` executable subprocess or wrapper bindings | Direct process invocation guarantees complete feature parity with upstream `yt-dlp`. |
| **Binary Bundling** | `sidecar` (Tauri) or PyInstaller spec bundling | Seamlessly packages `yt-dlp` and `ffmpeg` inside the compiled app bundle. |

---

## 📋 Implementation Checklist for Jules

- [ ] **Setup project structure** and build system.
- [ ] **Implement binary manager script** to bundle or auto-download native `yt-dlp` and `ffmpeg` binaries for target platforms.
- [ ] **Build URL parser & inspector service** to fetch metadata (`--dump-json`) prior to starting downloads.
- [ ] **Design frontend GUI interface** (URL bar, format dropdowns, progress queue).
- [ ] **Wire stdout/stderr parsing** from `yt-dlp` to drive the visual progress bar and velocity metric.
- [ ] **Package application into native installers** (`.dmg`, `.exe`, `.AppImage`).
