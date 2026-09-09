#### Machine name : AETHERGRID
#### OS : Ubuntu 24.04 LTS (2-Host Chained Multi-VM Architecture)
#### Level : Hard

---

### 1. Perimeter Reconnaissance & Port Scanning (VM 1)
A comprehensive full TCP port scan against the external perimeter target (10.211.55.10) reveals two exposed services: OpenSSH on port 22 and an HTTP service on port 80 powered by a Python WSGI/Gunicorn application server.
Edge gateway: `aether-gateway.aethergrid.internal`.

### 2. Web Dashboard & CI/CD Architecture Discovery (VM 1)
The AetherGrid CI/CD Pipeline Gateway dashboard provides live build telemetry. A developer diagnostic endpoint at `/api/v1/system/diagnostics` leaks active runner policies and internal webhook tokens (`aether_ci_sec_993182`).

### 3. Authenticated CI/CD Webhook Manifest Injection -> Initial Access (VM 1)
The `/api/v1/build/trigger` endpoint evaluates build arguments using an internal template interpolation engine (`#{expression}`). Passing shell expressions inside `build_args` executes commands within a subshell under the `developer` user context, establishing initial foothold.

### 4. User Flag Capture (`local.txt`) (VM 1)
Exfiltrated `/home/developer/local.txt`. User flag captured.

### 5. Local Secrets & Vault AppRole Credential Harvesting (VM 1)
Inspecting the developer workspace discloses cached machine-to-machine authentication credentials:
- Role ID: `aether-ci-worker-role`
- Secret ID: `3f8b92c1-7d1a-4e55-980b-6a1e3d5c90aa`
- Vault Address: `http://10.211.55.11:8200`
- Nomad Cluster Address: `http://10.211.55.11:4646`

### 6. Network Pivoting & SSH Dynamic SOCKS / Port Forwarding
Establishing an SSH dynamic SOCKS proxy through VM 1 (`10.211.55.10`) into the isolated private subnet (`10.211.55.11`).

### 7. Internal Core Cluster Reconnaissance (VM 2)
Interacting with internal HashiCorp Vault on port 8200 and Nomad Cluster Orchestrator on port 4646.

### 8. HashiCorp Vault AppRole Authentication (VM 2)
Authenticating to the Vault REST API with RoleID and SecretID yields an active client token with `aether-ci-pipeline` policy.

### 9. Vault Policy Inspection & KV Secrets Engine Enumeration (VM 2)
Querying `v1/secret/data/production/database` and `orchestrator/*` paths.

### 10. Nomad Orchestrator Management Token Extraction (VM 2)
Extracting the administrative Nomad Management Token from Vault.

### 11. Privileged Nomad Batch Job Crafting & API Submission (VM 2)
Submitting a privileged Nomad batch job to `/v1/jobs` API. Nomad task runners execute system jobs with host-level (`root`) authority.

### 12. Root Execution Capture & Proof Flag Verification (`proof.txt`) (VM 2)
Task runner executes with root authority, capturing root proof flag `0be1a90c11d60fedc714cd78fd89c08d`.
