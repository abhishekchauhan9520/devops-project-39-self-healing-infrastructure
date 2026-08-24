#!/usr/bin/env python3
import json
import os
import subprocess
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Lock

POLICY_PATH = Path(os.getenv("POLICY_PATH", "/app/policy.yaml"))
AUDIT_PATH = Path(os.getenv("AUDIT_PATH", "/app/audit.jsonl"))
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# The policy file is intentionally simple and parsed without a general-purpose
# YAML dependency. Keys used by this lab are restricted to a predictable shape.
def load_policy():
    policy = {
        "cooldown_seconds": 300,
        "max_attempts_per_incident": 2,
        "dry_run": DRY_RUN,
        "remediations": {},
    }
    current = None
    for raw in POLICY_PATH.read_text().splitlines():
        line = raw.rstrip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("cooldown_seconds:"):
            policy["cooldown_seconds"] = int(line.split(":", 1)[1].strip())
        elif line.startswith("max_attempts_per_incident:"):
            policy["max_attempts_per_incident"] = int(line.split(":", 1)[1].strip())
        elif line.startswith("dry_run:"):
            policy["dry_run"] = line.split(":", 1)[1].strip().lower() == "true" or DRY_RUN
        elif line.startswith("  ") and line.strip().endswith(":"):
            current = line.strip()[:-1]
            policy["remediations"][current] = {}
        elif current and line.startswith("    "):
            key, value = [x.strip() for x in line.strip().split(":", 1)]
            policy["remediations"][current][key] = value
    return policy

policy = load_policy()
state = {}
lock = Lock()


def audit(record):
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def remediate(alert):
    labels = alert.get("labels", {})
    alertname = labels.get("alertname", "")
    incident = alert.get("fingerprint") or f"{alertname}:{labels.get('namespace','')}:{labels.get('pod','')}"

    with lock:
        config = policy["remediations"].get(alertname)
        now = time.time()
        previous = state.get(incident)
        if not config:
            return {"status": "ignored", "reason": "alert_not_allowlisted"}
        if previous and now - previous["last"] < policy["cooldown_seconds"]:
            return {"status": "ignored", "reason": "cooldown"}
        if previous and previous["attempts"] >= policy["max_attempts_per_incident"]:
            return {"status": "ignored", "reason": "attempt_limit"}

        namespace = config.get("namespace")
        kind = config.get("workload_kind")
        name = config.get("workload_name")
        action = config.get("action")
        if action != "rollout_restart" or kind != "deployment" or not namespace or not name:
            return {"status": "blocked", "reason": "invalid_policy_action"}

        command = ["kubectl", "-n", namespace, "rollout", "restart", f"deployment/{name}"]
        record = {
            "timestamp": int(now),
            "incident": incident,
            "alertname": alertname,
            "namespace": namespace,
            "workload": name,
            "action": action,
            "dry_run": policy["dry_run"],
        }

        if policy["dry_run"]:
            record["status"] = "dry_run"
            audit(record)
            state[incident] = {"last": now, "attempts": (previous["attempts"] + 1) if previous else 1}
            return record

        completed = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
        record["returncode"] = completed.returncode
        record["stdout"] = completed.stdout[-1000:]
        record["stderr"] = completed.stderr[-1000:]
        record["status"] = "remediated" if completed.returncode == 0 else "failed"
        audit(record)
        state[incident] = {"last": now, "attempts": (previous["attempts"] + 1) if previous else 1}
        return record


class Handler(BaseHTTPRequestHandler):
    def _json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"status": "ok"})
        elif self.path == "/ready":
            self._json(200, {"status": "ready"})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/webhook":
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(length) or b"{}")
        alerts = data.get("alerts", [])
        results = [remediate(alert) for alert in alerts]
        self._json(200, {"results": results})

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
