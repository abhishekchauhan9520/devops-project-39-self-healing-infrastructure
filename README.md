# Project 39 — Self-Healing Infrastructure

A guarded self-healing Kubernetes pattern using Prometheus/Alertmanager signals and an allowlisted remediation controller.

## Architecture

```text
Application
    |
    v
Prometheus
    |
    v
Alert rule
    |
    v
Alertmanager webhook
    |
    v
Remediation Controller
    |
    +--> policy allowlist
    +--> cooldown / attempt limit
    +--> audit log
    |
    v
kubectl rollout restart
    |
    v
Kubernetes Deployment
    |
    v
Health verification
```

## Design goals

- No arbitrary command execution from alerts
- Explicit alert-to-action allowlist
- Namespace/workload scoping
- Cooldown protection
- Maximum remediation attempts per incident
- Dry-run mode for testing
- Structured audit records
- Least-privilege Kubernetes RBAC
- Recovery verification after remediation

## Example remediation

An approved `HighErrorRate` alert for `self-healing-demo` can request:

```text
rollout_restart -> deployment/self-healing-demo
```

The controller refuses unknown alerts, unknown actions, unknown workloads, and repeated remediation inside the cooldown window.

## Limitations

A live Prometheus/Kubernetes integration requires a real cluster. CI validates the controller, policy, manifests, and state-machine behavior without creating external infrastructure.

## License

MIT
