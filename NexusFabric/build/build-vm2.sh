#!/usr/bin/env bash

set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

HOSTNAME="nexus-broker"
LOW_PRIV_USER="worker-svc"
LOW_PRIV_PASS="WorkerSvc_Mesh_7712!"
APP_DIR="/opt/nexus-worker"

echo "[*] Setting up system..."

if [[ $EUID -ne 0 ]]; then
   echo "[-] Root privileges required. Aborting." 1>&2
   exit 1
fi

# hostname
hostnamectl set-hostname "${HOSTNAME}" || hostname "${HOSTNAME}"
echo "127.0.0.1 ${HOSTNAME}" >> /etc/hosts

# packages
apt-get update -y || true
apt-get install -y --no-install-recommends \
    redis-server \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    wget \
    net-tools \
    openssh-server \
    sudo \
    jq

# user setup
if ! id "${LOW_PRIV_USER}" &>/dev/null; then
    useradd -m -s /bin/bash "${LOW_PRIV_USER}"
fi
usermod -p "$(openssl passwd -6 "${LOW_PRIV_PASS}")" "${LOW_PRIV_USER}"
usermod -aG sudo "${LOW_PRIV_USER}" || true

# ssh config
sed -i 's/#\?PasswordAuthentication .*/PasswordAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/#\?AllowTcpForwarding .*/AllowTcpForwarding yes/' /etc/ssh/sshd_config
systemctl restart ssh || systemctl restart sshd

# redis config
CLUSTER_PASS="nexus_cluster_auth_8819"

sed -i 's/^bind .*/bind 0.0.0.0/' /etc/redis/redis.conf
sed -i 's/^protected-mode yes/protected-mode no/' /etc/redis/redis.conf
if grep -q "^# requirepass" /etc/redis/redis.conf; then
    sed -i "s/^# requirepass .*/requirepass ${CLUSTER_PASS}/" /etc/redis/redis.conf
elif ! grep -q "^requirepass" /etc/redis/redis.conf; then
    echo "requirepass ${CLUSTER_PASS}" >> /etc/redis/redis.conf
fi
systemctl restart redis-server

# worker service
mkdir -p "${APP_DIR}/secrets"
python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org redis

cat << 'PYEOF' > "${APP_DIR}/worker_daemon.py"
import os
import sys
import time
import json
import subprocess
import redis

REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_PASS = "nexus_cluster_auth_8819"
QUEUE_NAME = "nexus:tasks:queue"

def process_task(task_raw):
    try:
        task = json.loads(task_raw)
        action = task.get("action")
        payload = task.get("payload", {})
        
        print(f"[*] Processing task: {action} with payload {payload}")
        
        if action == "ping":
            return {"status": "pong"}
            
        elif action == "system_sync":
            
            cmd = payload.get("command")
            if cmd:
                output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True, timeout=10)
                return {"status": "completed", "output": output}
                
        elif action == "eval_metrics":
            expr = payload.get("expression", "1+1")
            res = eval(expr)
            return {"status": "success", "result": str(res)}
            
        return {"status": "unknown_action"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def main():
    print("[*] Nexus Worker Daemon started. Listening on Redis queue...")
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASS, decode_responses=True)
    
    while True:
        try:
            item = r.blpop(QUEUE_NAME, timeout=3)
            if item:
                _, task_data = item
                res = process_task(task_data)
                # Store result back
                r.lpush("nexus:tasks:results", json.dumps(res))
        except Exception as e:
            time.sleep(2)

if __name__ == "__main__":
    main()
PYEOF

# core access credentials
cat << 'EOF' > "${APP_DIR}/secrets/core_access.json"
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
EOF

chown -R "${LOW_PRIV_USER}:${LOW_PRIV_USER}" "${APP_DIR}"
chmod 600 "${APP_DIR}/secrets/core_access.json"

# systemd worker
cat << EOF > /etc/systemd/system/nexus-worker.service
[Unit]
Description=NexusFabric Distributed Task Worker Daemon
After=network.target redis-server.service

[Service]
Type=simple
User=${LOW_PRIV_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/venv/bin/python3 ${APP_DIR}/worker_daemon.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now nexus-worker.service

echo "[+] Done."
