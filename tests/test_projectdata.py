import os
import unittest
from unittest import mock

from construction_ai import config
from construction_ai.projectdata import (
    ProjectDataError, ProjectProfile, profile_from_json, profile_to_json, table_summary)


class ProjectDataTests(unittest.TestCase):
    def test_profile_roundtrip_and_context(self):
        p = ProjectProfile(name="Villa", location="Bhopal", built_up_area=1500, floors=2)
        p2 = profile_from_json(profile_to_json(p).encode())
        self.assertEqual(p2, p)
        ctx = p.to_context()
        self.assertIn("Bhopal", ctx)
        self.assertIn("Floors: 2", ctx)

    def test_profile_invalid(self):
        for bad in (b"not json", b'{"floors": 0}', b'{"built_up_area": -4}', b"\xff\xfe\x00"):
            with self.assertRaises(ProjectDataError):
                profile_from_json(bad)

    def test_csv_summary_truncates_rows(self):
        rows = "task,qty\n" + "\n".join("t%d,%d" % (i, i) for i in range(100))
        s = table_summary(rows.encode(), "boq.csv", max_rows=5)
        self.assertIn("100 data rows", s)
        self.assertIn("t4,4", s)
        self.assertNotIn("t50,50", s)
        self.assertLessEqual(len(s), config.MAX_CONTEXT_CHARS)

    def test_json_and_errors(self):
        self.assertEqual(table_summary(b'{"a": [1, 2]}', "x.json"), '{"a":[1,2]}')
        for data, name in ((b"", "e.csv"), (b"{oops", "x.json"), (b"a,b", "notes.txt")):
            with self.assertRaises(ProjectDataError):
                table_summary(data, name)

    def test_latin1_csv(self):
        s = table_summary("item,note\ncement,caf\xe9".encode("latin-1"), "l.csv")
        self.assertIn("cement", s)


class SecretTests(unittest.TestCase):
    def test_env_lookup_and_default(self):
        with mock.patch.dict(os.environ, {"MY_KEY": "abc"}, clear=False):
            self.assertEqual(config.get_secret("MY_KEY"), "abc")
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(config.get_secret("NOPE_NOT_SET"))
            self.assertEqual(config.get_secret("NOPE_NOT_SET", "dflt"), "dflt")


if __name__ == "__main__":
    unittest.main()
