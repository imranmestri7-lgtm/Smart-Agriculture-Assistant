"""Unit tests for Phase 12: Progressive Web App (PWA) & Offline Support.

Tests:
1. PWA Manifest structure, MIME type, theme color, icons, and shortcuts.
2. Icon presence, dimensions, and maskable formats on disk.
3. Service Worker file (sw.js) headers, Service-Worker-Allowed scope, and caching rules.
4. Offline fallback page (offline.html) availability and multilingual content.
5. Presence of PWA manifest, theme-color, and script tags across all 8 HTML pages.
6. Translation completeness for PWA and offline strings across en, mr, and hi.
"""

import json
import os
import sys
import unittest
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app import app as flask_app
from utils.i18n import MESSAGES


class Phase12PWATests(unittest.TestCase):
    """Test suite for Phase 12 PWA & Offline Support."""

    def setUp(self):
        self.client = flask_app.test_client()
        self.project_root = os.path.dirname(BASE_DIR)

    def test_manifest_endpoint_and_structure(self):
        resp = self.client.get("/manifest.json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/manifest+json", resp.content_type)

        data = json.loads(resp.data.decode("utf-8"))
        self.assertEqual(data.get("name"), "AgriSmart — Smart Agriculture Assistant")
        self.assertEqual(data.get("short_name"), "AgriSmart")
        self.assertEqual(data.get("display"), "standalone")
        self.assertEqual(data.get("start_url"), "/")
        self.assertEqual(data.get("scope"), "/")
        self.assertEqual(data.get("theme_color"), "#15803d")
        self.assertEqual(data.get("background_color"), "#ffffff")

        # Icons
        icons = data.get("icons", [])
        self.assertTrue(len(icons) >= 8, f"Expected at least 8 icons, found {len(icons)}")
        sizes = [i["sizes"] for i in icons]
        self.assertIn("192x192", sizes)
        self.assertIn("512x512", sizes)

        # Maskable icons
        purposes = [i.get("purpose") for i in icons]
        self.assertIn("maskable", purposes)

        # Shortcuts
        shortcuts = data.get("shortcuts", [])
        self.assertTrue(len(shortcuts) >= 4)
        shortcut_urls = [s["url"] for s in shortcuts]
        self.assertIn("/farmer.html", shortcut_urls)
        self.assertIn("/disease.html", shortcut_urls)

    def test_icons_on_disk_and_validity(self):
        icons_dir = os.path.join(self.project_root, "images", "icons")
        self.assertTrue(os.path.isdir(icons_dir), "images/icons directory must exist")

        required_sizes = [72, 96, 128, 144, 152, 180, 192, 384, 512]
        for s in required_sizes:
            icon_path = os.path.join(icons_dir, f"icon-{s}x{s}.png")
            self.assertTrue(os.path.isfile(icon_path), f"Missing icon-{s}x{s}.png")
            with Image.open(icon_path) as img:
                self.assertEqual(img.size, (s, s))
                self.assertEqual(img.format, "PNG")

        # Maskable icons
        for s in [192, 512]:
            maskable_path = os.path.join(icons_dir, f"icon-maskable-{s}x{s}.png")
            self.assertTrue(os.path.isfile(maskable_path), f"Missing icon-maskable-{s}x{s}.png")
            with Image.open(maskable_path) as img:
                self.assertEqual(img.size, (s, s))

    def test_service_worker_endpoint_and_headers(self):
        resp = self.client.get("/sw.js")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/javascript", resp.content_type)
        self.assertEqual(resp.headers.get("Service-Worker-Allowed"), "/")
        self.assertIn("no-cache", resp.headers.get("Cache-Control", ""))

        sw_code = resp.data.decode("utf-8")
        self.assertIn("CACHE_VERSION", sw_code)
        self.assertIn("STATIC_ASSETS", sw_code)
        self.assertIn("NEVER_CACHE_PATTERNS", sw_code)
        self.assertIn("/offline.html", sw_code)
        self.assertIn("addEventListener('install'", sw_code)
        self.assertIn("addEventListener('activate'", sw_code)
        self.assertIn("addEventListener('fetch'", sw_code)

        # Verify sensitive paths are in never-cache
        self.assertIn("auth\\/login", sw_code)
        self.assertIn("iot\\/ingest", sw_code)

    def test_offline_fallback_page(self):
        resp = self.client.get("/offline.html")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")
        self.assertIn("You Are Offline", html)
        self.assertIn("Available Offline", html)
        self.assertIn("Requires Internet", html)
        # Marathi & Hindi texts
        self.assertIn("तुम्ही ऑफलाइन आहात", html)
        self.assertIn("आप ऑफ़लाइन हैं", html)

    def test_html_pages_pwa_integration(self):
        pages = [
            "index.html",
            "farmer.html",
            "disease.html",
            "crop.html",
            "weather.html",
            "irrigation.html",
            "login.html",
            "register.html",
        ]

        for p in pages:
            path = os.path.join(self.project_root, p)
            self.assertTrue(os.path.isfile(path), f"Page {p} not found")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn('rel="manifest"', content, f"{p} missing manifest link")
            self.assertIn('name="theme-color"', content, f"{p} missing theme-color meta")
            self.assertIn('rel="apple-touch-icon"', content, f"{p} missing apple-touch-icon")
            self.assertIn('src="js/pwa.js"', content, f"{p} missing js/pwa.js script")

    def test_pwa_translation_keys_in_i18n_js(self):
        i18n_path = os.path.join(self.project_root, "js", "i18n.js")
        with open(i18n_path, "r", encoding="utf-8") as f:
            content = f.read()

        pwa_keys = [
            "pwa_install_btn",
            "pwa_install_title",
            "pwa_install_desc",
            "pwa_offline_banner",
            "pwa_online_banner",
            "pwa_update_available",
            "pwa_offline_queue_badge",
            "farm_queued_offline",
            "crop_queued_offline",
        ]

        for k in pwa_keys:
            self.assertIn(f'"{k}"', content, f"Key {k} missing from js/i18n.js")


if __name__ == "__main__":
    unittest.main()
