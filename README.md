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

## State-safety decision

The lab controller runs as a **single replica** because cooldown and attempt state is intentionally in memory. Scaling it horizontally without shared state could allow duplicate remediation.

A production implementation should replace this with a durable coordination mechanism such as a Kubernetes Lease, Redis, or another strongly consistent state store before running multiple replicas.

## Container image

CI publishes the controller to GHCR using the commit SHA. The Kubernetes manifest uses the `dev` tag for local/lab use; for deployment, update the image through the Kustomize bundle to the immutable SHA tag produced by CI.

## Limitations

A live Prometheus/Kubernetes integration requires a real cluster. CI validates the controller, policy, manifests, and state-machine behavior without creating external infrastructure.

## License

MIT
