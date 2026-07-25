import os
import sys
import unittest
import json
import shutil
import tempfile
from src.downloader import parse_progress_line, DownloadManager, DownloadItem
from src.gui import load_config, save_config, CONFIG_PATH

class TestParserAndManager(unittest.TestCase):
    def setUp(self):
        # Setup clean environment for config tests
        self.temp_dir = tempfile.mkdtemp()
        self.old_config_path = CONFIG_PATH

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

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
        # Test line without exact matching structure of sizes
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

    def test_download_manager_queue_operations(self):
        # Create a DownloadManager with 0 active concurrency to test static queue state transitions
        manager = DownloadManager(max_concurrent=0)

        # Add item
        item = manager.add_item(
            url="https://www.youtube.com/watch?v=123",
            title="Test Video",
            preset="1080p",
            container="mp4",
            save_dir="/tmp",
            name_template="%(title)s.%(ext)s"
        )

        self.assertEqual(item.id, "1")
        self.assertEqual(item.title, "Test Video")
        self.assertEqual(item.status, "Waiting")
        self.assertEqual(len(manager.queue), 1)

        # Test pause item (when not Downloading, transitions to Paused)
        manager.pause_item("1")
        self.assertEqual(item.status, "Paused")

        # Test resume item
        manager.resume_item("1")
        self.assertEqual(item.status, "Waiting")

        # Test cancel item
        manager.cancel_item("1")
        self.assertEqual(item.status, "Cancelled")

        manager.is_running = False

if __name__ == '__main__':
    unittest.main()
