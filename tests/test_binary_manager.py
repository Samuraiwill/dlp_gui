import os
import sys
import unittest
from src.binary_manager import get_platform_info, get_bin_dir, get_binary_paths

class TestBinaryManager(unittest.TestCase):
    def test_get_platform_info(self):
        os_name, arch = get_platform_info()
        self.assertIn(os_name, ["windows", "macos", "linux"])
        self.assertIn(arch, ["64", "arm64"])

    def test_get_bin_dir(self):
        bin_dir = get_bin_dir()
        self.assertTrue(os.path.isabs(bin_dir))
        # It should either be local bin or ~/.yt_dlp_desktop_gui/bin
        self.assertTrue(bin_dir.endswith("bin"))

    def test_get_binary_paths(self):
        yt_dlp_path, ffmpeg_path = get_binary_paths()
        self.assertTrue(os.path.isabs(yt_dlp_path))
        self.assertTrue(os.path.isabs(ffmpeg_path))

        os_name, _ = get_platform_info()
        if os_name == "windows":
            self.assertTrue(yt_dlp_path.endswith("yt-dlp.exe"))
            self.assertTrue(ffmpeg_path.endswith("ffmpeg.exe"))
        else:
            self.assertTrue(yt_dlp_path.endswith("yt-dlp"))
            self.assertTrue(ffmpeg_path.endswith("ffmpeg"))

if __name__ == '__main__':
    unittest.main()
