"""Regression guards for config that isn't itself Python.

wrangler dev needs --env development to pick up the ENVIRONMENT=development
var, or the X-Dev-User bypass in src/auth.py rejects every request with 401
even though the docs say to use it -- see docs/backend.md.
"""

import json
import os
import re
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")


class DevScriptTests(unittest.TestCase):
    def test_the_dev_script_selects_the_development_environment(self):
        with open(os.path.join(ROOT, "package.json")) as handle:
            package = json.load(handle)
        self.assertIn("--env development", package["scripts"]["dev"])

    def test_wrangler_config_declares_a_development_environment(self):
        with open(os.path.join(ROOT, "wrangler.jsonc")) as handle:
            raw = handle.read()
        # wrangler.jsonc allows // comments, which json.loads rejects; strip
        # them rather than pull in a JSONC parser for one check.
        without_comments = re.sub(r"^\s*//.*$", "", raw, flags=re.MULTILINE)
        config = json.loads(without_comments)
        self.assertEqual(
            config["env"]["development"]["vars"]["ENVIRONMENT"], "development"
        )


if __name__ == "__main__":
    unittest.main()
