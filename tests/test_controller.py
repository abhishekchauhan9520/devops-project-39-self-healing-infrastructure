import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

# Import the module with temporary policy/audit locations.
with tempfile.TemporaryDirectory() as td:
    policy = Path(td) / "policy.yaml"
    audit = Path(td) / "audit.jsonl"
    policy.write_text(
        "cooldown_seconds: 30\n"
        "max_attempts_per_incident: 2\n"
        "dry_run: true\n"
        "remediations:\n"
        "  HighErrorRate:\n"
        "    action: rollout_restart\n"
        "    namespace: self-healing\n"
        "    workload_kind: deployment\n"
        "    workload_name: self-healing-demo\n",
        encoding="utf-8",
    )
    os.environ["POLICY_PATH"] = str(policy)
    os.environ["AUDIT_PATH"] = str(audit)
    os.environ["DRY_RUN"] = "true"
    import sys
    sys.path.insert(0, str(Path(__file__).parents[1] / "controller"))
    import remediator


class ControllerTests(unittest.TestCase):
    def setUp(self):
        remediator.state.clear()
        if remediator.AUDIT_PATH.exists():
            remediator.AUDIT_PATH.unlink()

    def alert(self, fingerprint="abc"):
        return {"fingerprint": fingerprint, "labels": {"alertname": "HighErrorRate"}}

    def test_allowlisted_alert_is_remediated_in_dry_run(self):
        result = remediator.remediate(self.alert())
        self.assertEqual(result["status"], "dry_run")
        self.assertTrue(result["dry_run"])
        self.assertEqual(remediator.state["abc"]["attempts"], 1)

    def test_cooldown_blocks_repeat(self):
        remediator.remediate(self.alert())
        result = remediator.remediate(self.alert())
        self.assertEqual(result["reason"], "cooldown")

    def test_unknown_alert_is_ignored(self):
        alert = {"fingerprint": "x", "labels": {"alertname": "Unknown"}}
        self.assertEqual(remediator.remediate(alert)["status"], "ignored")

    def test_invalid_action_is_blocked(self):
        original = remediator.policy["remediations"]["HighErrorRate"]["action"]
        remediator.policy["remediations"]["HighErrorRate"]["action"] = "exec_shell"
        try:
            self.assertEqual(remediator.remediate(self.alert())["status"], "blocked")
        finally:
            remediator.policy["remediations"]["HighErrorRate"]["action"] = original

    def test_audit_record_is_json(self):
        remediator.remediate(self.alert())
        record = json.loads(remediator.AUDIT_PATH.read_text().splitlines()[-1])
        self.assertEqual(record["alertname"], "HighErrorRate")
        self.assertTrue(record["dry_run"])


if __name__ == "__main__":
    unittest.main()
