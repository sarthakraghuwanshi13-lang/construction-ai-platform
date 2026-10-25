"""Real Streamlit startup test (uses streamlit.testing.v1.AppTest).

Skipped automatically when Streamlit is not installed. It needs no API key and no network.
"""
import os
import sys
import unittest
from unittest import mock

try:
    from streamlit.testing.v1 import AppTest

    HAVE_STREAMLIT = True
except Exception:  # pragma: no cover
    HAVE_STREAMLIT = False

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@unittest.skipUnless(HAVE_STREAMLIT, "streamlit is not installed")
class AppStartupTests(unittest.TestCase):
    def test_app_starts_without_api_key(self):
        sys.path.insert(0, ROOT)
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with mock.patch.dict(os.environ, env, clear=True):
            at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=60).run()
        self.assertEqual(len(at.exception), 0, [e.value for e in at.exception])
        self.assertEqual([e.value for e in at.error if "unexpected error" in e.value], [])
        self.assertEqual(len(at.tabs), 9)
        self.assertTrue(any("not configured" in i.value for i in at.info), "missing 'AI not configured' notice")


if __name__ == "__main__":
    unittest.main()
