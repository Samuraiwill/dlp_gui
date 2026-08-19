import os
import sys
import unittest

try:
    from src.downloader import parse_progress_line, DirectDownloader
    from src.gui import load_config, save_config, CONFIG_PATH
except ImportError:
    from downloader import parse_progress_line, DirectDownloader
    from gui import load_config, save_config, CONFIG_PATH

class TestParserAndDownloader(unittest.TestCase):
    def test_parse_progress_line_standard(self):
        line = "[download]  45.1% of  124.50MiB at   12.41MiB/s ETA 00:15"
        res = parse_progress_line(line)
        self.assertIsNotNone(res)
        self.assertEqual(res["percent"], 45.1)
        self.assertEqual(res["size"], "124.50MiB")
        self.assertEqual(res["speed"], "12.41MiB/s")
        self.assertEqual(res["eta"], "00:15")

    def test_parse_progress_line_tilde(self):
        line = "[download]   1.2% of ~50.2MiB at  850.3KiB/s ETA 01:02"
        res = parse_progress_line(line)
        self.assertIsNotNone(res)
        self.assertEqual(res["percent"], 1.2)
        self.assertEqual(res["size"], "50.2MiB")
        self.assertEqual(res["speed"], "850.3KiB/s")
        self.assertEqual(res["eta"], "01:02")

    def test_parse_progress_line_fallback(self):
        line = "[download]  88.5% at  25.40MiB/s ETA 00:01"
        res = parse_progress_line(line)
        self.assertIsNotNone(res)
        self.assertEqual(res["percent"], 88.5)
        self.assertEqual(res["speed"], "25.40MiB/s")
        self.assertEqual(res["eta"], "00:01")

    def test_parse_progress_invalid(self):
        line = "[youtube] watch: Downloading webpage"
        res = parse_progress_line(line)
        self.assertIsNone(res)

    def test_direct_downloader_initialization(self):
        downloader = DirectDownloader(
            url="https://www.youtube.com/watch?v=123",
            save_dir="/tmp",
            preset="1080p",
            container="mp4",
            embed_thumbnail=False,
            embed_subtitles=False,
            extract_audio=False,
            name_template="%(title)s.%(ext)s",
            browser_cookies="none",
            progress_callback=None,
            log_callback=None,
            completion_callback=None
        )
        self.assertEqual(downloader.url, "https://www.youtube.com/watch?v=123")
        self.assertEqual(downloader.save_dir, "/tmp")
        self.assertFalse(downloader.is_cancelled)

if __name__ == '__main__':
    unittest.main()
