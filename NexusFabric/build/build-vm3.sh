#!/usr/bin/env bash

set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

HOSTNAME="nexus-core"
CORE_USER="nexus-core"
CORE_PASS="NexusCore_Sec_9912#!"
ROOT_FLAG_PATH="/root/proof.txt"
APP_DIR="/opt/nexus-core"
HOOKS_DIR="/var/lib/nexus/hooks.d"

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
if ! id "${CORE_USER}" &>/dev/null; then
    useradd -m -s /bin/bash "${CORE_USER}"
fi
usermod -p "$(openssl passwd -6 "${CORE_PASS}")" "${CORE_USER}"

# ssh config
sed -i 's/#\?PasswordAuthentication .*/PasswordAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/#\?AllowTcpForwarding .*/AllowTcpForwarding yes/' /etc/ssh/sshd_config
systemctl restart ssh || systemctl restart sshd

# flags
ROOT_FLAG_HASH=$(openssl rand -hex 16)
echo "${ROOT_FLAG_HASH}" > "${ROOT_FLAG_PATH}"
ln -sf "${ROOT_FLAG_PATH}" "/root/root.txt" 2>/dev/null || true
chown root:root "${ROOT_FLAG_PATH}"
chmod 600 "${ROOT_FLAG_PATH}"

# rpc daemon
mkdir -p "${APP_DIR}"
mkdir -p "${HOOKS_DIR}"
chmod 777 "${HOOKS_DIR}"

python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org flask

cat << 'PYEOF' > "${APP_DIR}/core_rpc.py"
import os
import sys
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

MAINT_TOKEN = "maint_tok_9918274100"
HOOK_FILE = "/var/lib/nexus/hooks.d/pre-backup.sh"

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "nexus-core-ledger-rpc", "cluster_state": "isolated"})

@app.route("/api/v1/ledger/backup/config", methods=["GET", "POST"])
def configure_backup_hook():
    tok = request.headers.get("X-Nexus-Maintenance-Token") or request.args.get("token")
    if tok != MAINT_TOKEN:
        return jsonify({"status": "unauthorized", "message": "Invalid X-Nexus-Maintenance-Token"}), 401

    hook_script = request.args.get("hook_content") or (request.json.get("hook_content") if request.is_json else request.form.get("hook_content"))
    if not hook_script:
        return jsonify({"status": "error", "message": "hook_content required"}), 400

    with open(HOOK_FILE, "w") as f:
        f.write(hook_script)
    os.chmod(HOOK_FILE, 0o755)

    return jsonify({"status": "success", "message": "Pre-backup hook script registered successfully"})

@app.route("/api/v1/ledger/backup/trigger", methods=["GET", "POST"])
def trigger_backup():
    tok = request.headers.get("X-Nexus-Maintenance-Token") or request.args.get("token")
    if tok != MAINT_TOKEN:
        return jsonify({"status": "unauthorized", "message": "Invalid X-Nexus-Maintenance-Token"}), 401

    
    try:
        out = subprocess.check_output(["sudo", "/usr/local/bin/nexus-ledger-backup"], stderr=subprocess.STDOUT, text=True, timeout=15)
        return jsonify({"status": "success", "output": out})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "failed", "output": e.output}), 500
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9090)
PYEOF

chown -R "${CORE_USER}:${CORE_USER}" "${APP_DIR}"

# backup script
cat << 'EOF' > /usr/local/bin/nexus-ledger-backup
#!/usr/bin/env bash
set -euo pipefail

echo "[*] NexusFabric Core Ledger Automated Backup Task (ROOT)"

HOOK_PATH="/var/lib/nexus/hooks.d/pre-backup.sh"

if [[ -f "${HOOK_PATH}" && -x "${HOOK_PATH}" ]]; then
    echo "[*] Executing registered pre-backup hook: ${HOOK_PATH}"
    bash "${HOOK_PATH}" || true
fi

BACKUP_DEST="/var/backups/nexus-core-ledger-$(date +%s).tar.gz"
tar -czf "${BACKUP_DEST}" /opt/nexus-core 2>/dev/null || true
echo "[+] Backup successfully created at: ${BACKUP_DEST}"
EOF

chmod 755 /usr/local/bin/nexus-ledger-backup

# backup sudoers rule
cat << EOF > /etc/sudoers.d/nexus-core-backup
${CORE_USER} ALL=(root) NOPASSWD: /usr/local/bin/nexus-ledger-backup
EOF
chmod 440 /etc/sudoers.d/nexus-core-backup

# systemd service
cat << EOF > /etc/systemd/system/nexus-core-rpc.service
[Unit]
Description=NexusFabric Core Ledger RPC Daemon
After=network.target

[Service]
Type=simple
User=${CORE_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/venv/bin/python3 ${APP_DIR}/core_rpc.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now nexus-core-rpc.service

echo "[+] Done."
