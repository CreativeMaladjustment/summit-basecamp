#!/usr/bin/env python3

import json
import sys

LEVEL_MAP = {"0": "note", "1": "warning", "2": "error", "3": "error"}
SEVERITY_MAP = {"0": "0.0", "1": "3.3", "2": "6.7", "3": "9.8"}


def ensure_list(value):
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def ensure_alert_list(value):
    if isinstance(value, dict) and "alertitem" in value:
        return ensure_list(value["alertitem"])
    return ensure_list(value)


def ensure_instance_list(value):
    if isinstance(value, dict) and "instance" in value:
        return ensure_list(value["instance"])
    return ensure_list(value)


def first_reference_url(reference_text: str) -> str:
    for candidate in str(reference_text).splitlines():
        candidate = candidate.strip()
        if candidate:
            return candidate.split()[0]
    return ""


def build_rule(alert: dict, risk_code: str) -> dict:
    rule_name = alert.get("name") or "ZAP alert"
    plugin_id = str(alert.get("pluginid") or alert.get("pluginId") or alert.get("id") or "").strip()
    rule_id = f"{plugin_id}:{rule_name}" if plugin_id else rule_name
    rule = {
        "id": rule_id,
        "name": rule_name,
        "shortDescription": {"text": rule_name},
        "fullDescription": {"text": alert.get("desc", rule_name)},
        "help": {
            "text": "\n\n".join(
                part for part in [alert.get("solution", ""), alert.get("otherinfo", "")] if part
            )
            or alert.get("desc", rule_name)
        },
        "properties": {"security-severity": SEVERITY_MAP.get(risk_code, "3.3")},
    }
    help_uri = first_reference_url(alert.get("reference", ""))
    if help_uri:
        rule["helpUri"] = help_uri
    return rule


def build_result(rule: dict, risk_code: str, site_uri: str, alert: dict, instance: dict) -> dict:
    message_parts = [rule["name"]]
    if instance.get("param"):
        message_parts.append(f"Parameter: {instance['param']}")
    if instance.get("evidence"):
        message_parts.append(f"Evidence: {instance['evidence']}")
    if alert.get("otherinfo"):
        message_parts.append(str(alert["otherinfo"]))

    result = {
        "ruleId": rule["id"],
        "level": LEVEL_MAP.get(risk_code, "warning"),
        "message": {"text": "\n".join(message_parts)},
    }

    location_uri = instance.get("uri") or site_uri
    if location_uri:
        result["locations"] = [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": location_uri}
                }
            }
        ]

    return result


def convert_report(input_path: str, output_path: str) -> int:
    with open(input_path, "r", encoding="utf-8") as fh:
        report = json.load(fh)

    rules = {}
    results = []

    for site in ensure_list(report.get("site", [])):
        site_uri = site.get("@name", "")
        for alert in ensure_alert_list(site.get("alerts", [])):
            risk_code = str(alert.get("riskcode") or alert.get("riskCode") or "0")
            rule = build_rule(alert, risk_code)
            rules.setdefault(rule["id"], rule)
            instances = ensure_instance_list(alert.get("instances")) or [{}]
            for instance in instances:
                results.append(build_result(rules[rule["id"]], risk_code, site_uri, alert, instance))

    sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "OWASP ZAP",
                        "informationUri": "https://www.zaproxy.org/",
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
            }
        ],
    }

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(sarif, fh, sort_keys=True, separators=(",", ":"))

    return 0


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: zap_report_to_sarif.py <input-json> <output-sarif>", file=sys.stderr)
        return 2

    return convert_report(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    raise SystemExit(main())
