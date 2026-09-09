#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

HOSTNAME="nexus-edge"
LOW_PRIV_USER="nexus-app"
LOW_PRIV_PASS="NexusEdge_Pass_2026!"
LOCAL_FLAG_PATH="/home/${LOW_PRIV_USER}/local.txt"
APP_DIR="/opt/nexus-edge"

if [[ $EUID -ne 0 ]]; then
   echo "[-] Root privileges required." 1>&2
   exit 1
fi

echo "[*] Configuring ${HOSTNAME}..."

# hostname
hostnamectl set-hostname "${HOSTNAME}" || hostname "${HOSTNAME}"
echo "127.0.0.1 ${HOSTNAME}" >> /etc/hosts

# packages
apt-get update -y || true
apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    curl \
    wget \
    git \
    net-tools \
    openssh-server \
    sudo \
    ufw \
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

# user flag
USER_FLAG_HASH=$(openssl rand -hex 16)
echo "${USER_FLAG_HASH}" > "${LOCAL_FLAG_PATH}"
ln -sf "${LOCAL_FLAG_PATH}" "/home/${LOW_PRIV_USER}/user.txt" 2>/dev/null || true
chown "${LOW_PRIV_USER}:${LOW_PRIV_USER}" "${LOCAL_FLAG_PATH}"
chmod 644 "${LOCAL_FLAG_PATH}"

# app setup
mkdir -p "${APP_DIR}"
python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org flask requests gunicorn

cat << 'EOF_EDGE' > "${APP_DIR}/edge_app.py"
import os
import re
import json
import urllib.request
import urllib.parse
import subprocess
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>NexusFabric — Financial Service Mesh Gateway</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 40px; }
        .container { max-width: 800px; margin: 0 auto; background: #1e293b; padding: 30px; border-radius: 12px; border: 1px solid #334155; }
        h1 { color: #38bdf8; margin-top: 0; }
        p { color: #94a3b8; line-height: 1.6; }
        input[type="text"] { width: 100%; padding: 12px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; box-sizing: border-box; font-family: monospace; }
        button { background: #0284c7; color: white; border: none; padding: 12px 24px; border-radius: 6px; font-weight: 600; cursor: pointer; margin-top: 12px; }
        button:hover { background: #0369a1; }
        .output { margin-top: 20px; background: #0f172a; padding: 15px; border-radius: 6px; font-family: monospace; border: 1px solid #334155; white-space: pre-wrap; word-break: break-all; }
        .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; background: #0369a1; font-size: 12px; font-weight: 600; }
    </style>
</head>
<body>
    <div class="container">
        <span class="badge">NexusFabric v2.4-Enterprise</span>
        <h1>Financial Service Mesh Gateway</h1>
        <p>Welcome to the NexusFabric Financial Edge node. Registered enterprise partners can validate microservice webhooks and inspect delivery latency.</p>
        <hr style="border: 0; border-top: 1px solid #334155; margin: 20px 0;">
        <h3>Webhook Diagnostic Sandbox</h3>
        <p>Enter an external callback URL to simulate an outbound telemetry dispatch:</p>
        <form method="POST" action="/api/v1/webhook/test">
            <input type="text" name="url" placeholder="https://api.partner.com/nexus/callback" required>
            <button type="submit">Dispatch Test Probe</button>
        </form>
    </div>
</body>
</html>
"""

def is_safe_url(url):
    low = url.lower()
    if "localhost" in low or "127.0.0.1" in low:
        return False
    return True

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_PAGE)

@app.route("/api/v1/webhook/test", methods=["POST"])
def webhook_test():
    target_url = request.form.get("url") or (request.json.get("url") if request.is_json else "")
    if not target_url:
        return jsonify({"status": "error", "message": "Missing url parameter"}), 400

    if not is_safe_url(target_url):
        return jsonify({"status": "forbidden", "message": "Loopback references to localhost or 127.0.0.1 are restricted by policy."}), 403

    try:
        req = urllib.request.Request(target_url, headers={"User-Agent": "NexusFabric-Probe/2.4"})
        with urllib.request.urlopen(req, timeout=4) as response:
            content = response.read(2048).decode('utf-8', errors='replace')
            return jsonify({
                "status": "success",
                "code": response.status,
                "remote_server": response.headers.get("Server", "Unknown"),
                "preview": content
            })
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
EOF_EDGE

cat << 'EOF_MGMT' > "${APP_DIR}/internal_mgmt.py"
import os
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

ADMIN_KEY = "nexus_adm_sec_9938177"
CLUSTER_TOKEN = "nexus_cluster_auth_8819"

@app.route("/internal/config", methods=["GET"])
def get_config():
    return jsonify({
        "service": "nexus-edge-internal-daemon",
        "version": "2.4.1",
        "mesh_cluster": {
            "broker_host": "10.211.55.11",
            "broker_redis_port": 6379,
            "core_host": "10.211.55.12",
            "core_vault_port": 8200
        },
        "admin_credentials": {
            "admin_api_key": ADMIN_KEY,
            "cluster_token": CLUSTER_TOKEN
        }
    })

@app.route("/api/v1/plugins/execute", methods=["GET", "POST"])
def exec_plugin():
    provided_key = request.headers.get("X-Nexus-Admin-Key") or request.args.get("key")
    if provided_key != ADMIN_KEY:
        return jsonify({"status": "unauthorized", "message": "Invalid X-Nexus-Admin-Key"}), 401

    cmd = request.args.get("command")
    if not cmd:
        cmd = request.json.get("command") if request.is_json else request.form.get("command")
    if not cmd:
        return jsonify({"status": "error", "message": "Command parameter required"}), 400

    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True, timeout=8)
        return jsonify({"status": "success", "output": output})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "failed", "output": e.output}), 500
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8081)
EOF_MGMT

chown -R "${LOW_PRIV_USER}:${LOW_PRIV_USER}" "${APP_DIR}"

# services
cat << EOF_SVC1 > /etc/systemd/system/nexus-edge.service
[Unit]
Description=NexusFabric Edge Gateway
After=network.target

[Service]
Type=simple
User=${LOW_PRIV_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/venv/bin/python3 ${APP_DIR}/edge_app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF_SVC1

cat << EOF_SVC2 > /etc/systemd/system/nexus-internal-mgmt.service
[Unit]
Description=NexusFabric Internal Management Service
After=network.target

[Service]
Type=simple
User=${LOW_PRIV_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/venv/bin/python3 ${APP_DIR}/internal_mgmt.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF_SVC2

# nginx config
cat << 'EOF_NGINX' > /etc/nginx/sites-available/nexus-edge
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name _;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF_NGINX

rm -f /etc/nginx/sites-enabled/*
ln -sf /etc/nginx/sites-available/nexus-edge /etc/nginx/sites-enabled/default
systemctl daemon-reload
systemctl enable --now nexus-edge.service
systemctl enable --now nexus-internal-mgmt.service
systemctl restart nginx

echo "[+] Done."
