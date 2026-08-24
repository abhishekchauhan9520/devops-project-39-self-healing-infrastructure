from pathlib import Path

root = Path(__file__).parents[1]
controller = (root / 'controller/remediator.py').read_text()
policy = (root / 'controller/policy.yaml').read_text()
rba = (root / 'k8s/controller-rbac.yaml').read_text()
deploy = (root / 'k8s/controller-deployment.yaml').read_text()
alert = (root / 'monitoring/alertmanager.yaml').read_text()

assert 'rollout_restart' in controller
assert 'subprocess.run' in controller
assert 'command = ["kubectl", "-n", namespace, "rollout", "restart", f"deployment/{name}"]' in controller
assert 'exec_shell' not in policy
assert 'max_attempts_per_incident' in policy
assert 'cooldown_seconds' in policy
assert 'resources: ["deployments"]' in rba
assert 'verbs: ["get", "list", "patch"]' in rba
assert 'resources: ["pods"]' not in rba
assert 'kind: ClusterRole' not in rba
assert 'runAsNonRoot: true' in deploy
assert 'allowPrivilegeEscalation: false' in deploy
assert 'readOnlyRootFilesystem: true' in deploy
assert 'type: RuntimeDefault' in deploy
assert 'remediation-controller.self-healing.svc.cluster.local:8080/webhook' in alert

for path in [root / 'controller/policy.yaml', root / 'k8s', root / 'monitoring']:
    for item in path.rglob('*'):
        if item.is_file():
            text = item.read_text(errors='ignore').lower()
            assert 'password=' not in text
            assert 'api_key:' not in text

print('Project 39 manifest/security assertions passed.')
