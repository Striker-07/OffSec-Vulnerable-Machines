#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

GATEWAY_USER="api-svc"
GATEWAY_PASS="ApiGateway_Sync_2026!"
INSTALL_DIR="/opt/synapse"
APP_DIR="${INSTALL_DIR}/gateway"
CONFIG_DIR="${INSTALL_DIR}/config"
CERTS_DIR="${INSTALL_DIR}/certs"
LOG_DIR="/var/log/synapse"
FLAG_USER_PATH="/home/${GATEWAY_USER}/local.txt"

INTERNAL_BROKER_IP="10.211.55.11"
INTERNAL_CORE_IP="10.211.55.12"
QUEUE_USER="synapse_feeder"
QUEUE_PASS="Feeder_EventBus_99214"
QUEUE_NAME="events.financial.audit"

apt-get update -y
apt-get install -y --no-install-recommends \
    curl \
    wget \
    git \
    python3 \
    python3-pip \
    python3-venv \
    python3-flask \
    python3-jwt \
    python3-cryptography \
    python3-werkzeug \
    python3-yaml \
    nginx \
    openssl \
    ca-certificates \
    net-tools \
    socat \
    jq

if ! id "${GATEWAY_USER}" &>/dev/null; then
    USER_CRYPT=$(openssl passwd -6 "${GATEWAY_PASS}")
    useradd -m -s /bin/bash -p "${USER_CRYPT}" "${GATEWAY_USER}"
fi

mkdir -p "${INSTALL_DIR}" "${APP_DIR}" "${CONFIG_DIR}" "${CERTS_DIR}" "${LOG_DIR}"
chown -R "${GATEWAY_USER}:${GATEWAY_USER}" "${INSTALL_DIR}" "${LOG_DIR}"

if [ ! -f "${CERTS_DIR}/jwt_private.pem" ]; then
    openssl genrsa -out "${CERTS_DIR}/jwt_private.pem" 2048
    openssl rsa -in "${CERTS_DIR}/jwt_private.pem" -pubout -out "${CERTS_DIR}/jwt_public.pem"
fi
chmod 600 "${CERTS_DIR}/jwt_private.pem"
chmod 644 "${CERTS_DIR}/jwt_public.pem"
chown -R "${GATEWAY_USER}:${GATEWAY_USER}" "${CERTS_DIR}"

python3 -m venv --system-site-packages "${APP_DIR}/venv"

cat << 'EOF' > "${APP_DIR}/server.py"
import os
import sys
import json
import base64
import subprocess
import jwt
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

CERTS_DIR = "/opt/synapse/certs"
PUB_KEY_PATH = os.path.join(CERTS_DIR, "jwt_public.pem")

with open(PUB_KEY_PATH, "r") as f:
    PUBLIC_KEY_PEM = f.read()

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "SynapseMesh Enterprise Edge API Gateway",
        "version": "3.4.1-prod",
        "status": "HEALTHY",
        "graphql_endpoint": "/graphql",
        "jwks_endpoint": "/api/v1/auth/jwks.json",
        "public_key_url": "/api/v1/auth/public.pem",
        "mesh_services": {
            "broker": "synapse-broker.internal:5672",
            "core_ledger": "synapse-core.internal:5432"
        }
    })

@app.route("/api/v1/auth/public.pem", methods=["GET"])
def get_public_pem():
    return send_file(PUB_KEY_PATH, mimetype="application/x-pem-file")

@app.route("/api/v1/auth/jwks.json", methods=["GET"])
def get_jwks():
    return jsonify({
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": "synapse-auth-key-2026",
                "pem": PUBLIC_KEY_PEM
            }
        ]
    })

def verify_token(auth_header):
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, "Missing or invalid authorization header"
    token = auth_header.split(" ", 1)[1].strip()
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None, "Invalid token structure"

        def b64_decode(s):
            s += "=" * (-len(s) % 4)
            return base64.urlsafe_b64decode(s)

        header = json.loads(b64_decode(parts[0]))
        payload = json.loads(b64_decode(parts[1]))
        sig_raw = b64_decode(parts[2])
        alg = header.get("alg", "RS256")
        signing_input = f"{parts[0]}.{parts[1]}".encode()

        if alg == "HS256":
            import hmac, hashlib
            try:
                with open(PUB_KEY_PATH, "r") as f:
                    pk_data = f.read()
            except Exception:
                pk_data = PUBLIC_KEY_PEM
            expected_raw = hmac.new(pk_data.encode(), signing_input, hashlib.sha256).digest()
            expected_strip = hmac.new(pk_data.strip().encode(), signing_input, hashlib.sha256).digest()
            if not hmac.compare_digest(sig_raw, expected_raw) and not hmac.compare_digest(sig_raw, expected_strip):
                return None, "Signature verification failed"
        elif alg == "RS256":
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.primitives.serialization import load_pem_public_key
            try:
                with open(PUB_KEY_PATH, "r") as f:
                    pk_data = f.read()
            except Exception:
                pk_data = PUBLIC_KEY_PEM
            pub_key = load_pem_public_key(pk_data.encode())
            pub_key.verify(sig_raw, signing_input, padding.PKCS1v15(), hashes.SHA256())
        else:
            return None, f"Unsupported algorithm: {alg}"

        return payload, None
    except Exception as e:
        return None, str(e)

@app.route("/graphql", methods=["POST"])
def graphql_handler():
    auth_header = request.headers.get("Authorization", "")
    data = request.get_json(force=True, silent=True)
    if not data or "query" not in data:
        return jsonify({"errors": [{"message": "Invalid GraphQL query payload"}]}), 400
    
    query = data.get("query", "").strip()
    variables = data.get("variables", {})

    if "__schema" in query or "__type" in query:
        return jsonify({
            "data": {
                "__schema": {
                    "types": [
                        {"name": "Query", "fields": [{"name": "systemTelemetry"}, {"name": "clusterNodes"}]},
                        {"name": "Mutation", "fields": [{"name": "dispatchPipelineWorker"}, {"name": "syncLedgerState"}]}
                    ]
                }
            }
        })

    if "systemTelemetry" in query:
        return jsonify({
            "data": {
                "systemTelemetry": {
                    "cluster": "synapse-prod-mesh-01",
                    "uptime": "99.98%",
                    "nodeCount": 3,
                    "ingressRPS": 4210
                }
            }
        })

    if "dispatchPipelineWorker" in query:
        claims, err = verify_token(auth_header)
        if err or not claims:
            return jsonify({"errors": [{"message": f"Authentication failed: {err}"}]}), 401
        
        if claims.get("role") not in ["admin", "cluster-admin", "mesh-operator"]:
            return jsonify({"errors": [{"message": "Forbidden: Insufficient role permissions"}]}), 403

        task_cmd = variables.get("command") or data.get("command")
        if not task_cmd and "command:" in query:
            import re
            m = re.search(r'command\s*:\s*"([^"]+)"', query)
            if m:
                task_cmd = m.group(1)

        if not task_cmd:
            return jsonify({"errors": [{"message": "Missing 'command' argument in mutation"}]}), 400

        try:
            res = subprocess.run(
                ["/bin/bash", "-c", task_cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            return jsonify({
                "data": {
                    "dispatchPipelineWorker": {
                        "status": "COMPLETED",
                        "exitCode": res.returncode,
                        "output": res.stdout + res.stderr
                    }
                }
            })
        except Exception as ex:
            return jsonify({"errors": [{"message": f"Execution error: {str(ex)}"}]}), 500

    return jsonify({"errors": [{"message": "Unsupported query or mutation"}]}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4000)
EOF

chmod +x "${APP_DIR}/server.py"
chown -R "${GATEWAY_USER}:${GATEWAY_USER}" "${APP_DIR}"

cat << EOF > "${CONFIG_DIR}/gateway.env"
# SynapseMesh Edge Service Configuration
GATEWAY_USER="${GATEWAY_USER}"
GATEWAY_PASS="${GATEWAY_PASS}"
EOF

cat << EOF > "${CONFIG_DIR}/queue-credentials.env"
# SynapseMesh Internal Broker Access Credentials
BROKER_HOST="${INTERNAL_BROKER_IP}"
BROKER_PORT="5672"
QUEUE_USER="${QUEUE_USER}"
QUEUE_PASS="${QUEUE_PASS}"
QUEUE_NAME="${QUEUE_NAME}"
CORE_DB_HOST="${INTERNAL_CORE_IP}"
EOF

chown -R "${GATEWAY_USER}:${GATEWAY_USER}" "${CONFIG_DIR}"
chmod 700 "${CONFIG_DIR}"
chmod 644 "${CONFIG_DIR}"/*.env

USER_FLAG_HASH=$(openssl rand -hex 16)
echo "${USER_FLAG_HASH}" > "${FLAG_USER_PATH}"
chown "${GATEWAY_USER}:${GATEWAY_USER}" "${FLAG_USER_PATH}"
chmod 644 "${FLAG_USER_PATH}"

cat << 'EOF' > /etc/nginx/sites-available/synapse-gateway
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:4000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/synapse-gateway /etc/nginx/sites-enabled/
systemctl restart nginx

cat << EOF > /etc/systemd/system/synapse-gateway.service
[Unit]
Description=SynapseMesh Edge GraphQL API Gateway
After=network.target

[Service]
Type=simple
User=${GATEWAY_USER}
Group=${GATEWAY_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/venv/bin/python3 ${APP_DIR}/server.py
Restart=always
RestartSec=3
StandardOutput=append:${LOG_DIR}/gateway.log
StandardError=append:${LOG_DIR}/gateway.err

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now synapse-gateway.service
systemctl restart synapse-gateway.service

echo "[+] VM 1 (synapse-gateway) ready: port 80 / 4000 (User Flag: ${USER_FLAG_HASH})"
