import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "zap_report_to_sarif.py"
SPEC = importlib.util.spec_from_file_location("zap_report_to_sarif", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ZapReportToSarifTests(unittest.TestCase):
    def test_main_converts_multiple_sites_and_reuses_canonical_rule_name(self):
        report = {
            "site": [
                {
                    "@name": "https://one.example",
                    "alerts": [
                        {
                            "pluginid": "10001",
                            "name": "First name",
                            "riskcode": "1",
                            "desc": "First description",
                            "solution": "First solution",
                            "reference": "https://example.com/first",
                            "instances": [{"uri": "https://one.example/a", "param": "a"}],
                        }
                    ],
                },
                {
                    "@name": "https://two.example",
                    "alerts": [
                        {
                            "pluginid": "10001",
                            "name": "Second name",
                            "riskcode": "1",
                            "desc": "Second description",
                            "solution": "Second solution",
                            "instances": [{"uri": "https://two.example/b", "evidence": "match"}],
                        }
                    ],
                },
            ]
        }

        with tempfile.TemporaryDirectory() as td:
            input_path = Path(td) / "report.json"
            output_path = Path(td) / "report.sarif"
            input_path.write_text(json.dumps(report), encoding="utf-8")

            self.assertEqual(MODULE.convert_report(str(input_path), str(output_path)), 0)

            sarif = json.loads(output_path.read_text(encoding="utf-8"))

        rules = sarif["runs"][0]["tool"]["driver"]["rules"]
        results = sarif["runs"][0]["results"]
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["name"], "First name")
        self.assertEqual(results[0]["message"]["text"], "First name\nParameter: a")
        self.assertEqual(results[1]["message"]["text"], "First name\nEvidence: match")

    def test_build_rule_extracts_help_uri(self):
        rule = MODULE.build_rule(
            {
                "pluginid": "20002",
                "name": "Help Uri Rule",
                "riskcode": "2",
                "desc": "Description",
                "solution": "Solution",
                "reference": " https://example.com/help \nhttps://example.com/extra ",
            },
            "2",
        )
        self.assertEqual(rule["helpUri"], "https://example.com/help")

    def test_alert_without_instances_still_emits_result(self):
        result = MODULE.build_result(
            {"id": "30003", "name": "No instances"},
            "3",
            "https://site.example",
            {"otherinfo": "Details"},
            {},
        )
        self.assertEqual(result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"], "https://site.example")
        self.assertEqual(result["message"]["text"], "No instances\nDetails")

    def test_single_site_and_instance_objects_are_normalized(self):
        report = {
            "site": {
                "@name": "https://solo.example",
                "alerts": [
                    {
                        "pluginid": "40004",
                        "name": "Single site",
                        "riskcode": "2",
                        "desc": "Description",
                        "instances": {"uri": "https://solo.example/path", "param": "p"},
                    }
                ],
            }
        }

        with tempfile.TemporaryDirectory() as td:
            input_path = Path(td) / "report.json"
            output_path = Path(td) / "report.sarif"
            input_path.write_text(json.dumps(report), encoding="utf-8")

            self.assertEqual(MODULE.convert_report(str(input_path), str(output_path)), 0)
            sarif = json.loads(output_path.read_text(encoding="utf-8"))

        result = sarif["runs"][0]["results"][0]
        self.assertEqual(result["ruleId"], "40004")
        self.assertEqual(
            result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"],
            "https://solo.example/path",
        )


if __name__ == "__main__":
    unittest.main()
