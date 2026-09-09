#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

BROKER_USER="celery-worker"
BROKER_PASS="CeleryBroker_TaskSync_99214!"
INSTALL_DIR="/opt/synapse"
APP_DIR="${INSTALL_DIR}/broker"
CONFIG_DIR="${INSTALL_DIR}/config"
CERTS_DIR="${INSTALL_DIR}/certs"
LOG_DIR="/var/log/synapse"

CORE_DB_HOST="10.211.55.12"
CORE_DB_PORT="5432"
CORE_DB_USER="db_admin"
CORE_DB_NAME="synapse_ledger"

apt-get update -y
apt-get install -y --no-install-recommends \
    curl \
    wget \
    python3 \
    python3-pip \
    python3-venv \
    python3-flask \
    python3-yaml \
    openssl \
    ca-certificates \
    net-tools \
    socat \
    postgresql-client \
    jq

if ! id "${BROKER_USER}" &>/dev/null; then
    USER_CRYPT=$(openssl passwd -6 "${BROKER_PASS}")
    useradd -m -s /bin/bash -p "${USER_CRYPT}" "${BROKER_USER}"
fi

mkdir -p "${INSTALL_DIR}" "${APP_DIR}" "${CONFIG_DIR}" "${CERTS_DIR}" "${LOG_DIR}"
chown -R "${BROKER_USER}:${BROKER_USER}" "${INSTALL_DIR}" "${LOG_DIR}"

python3 -c "
ca_crt = '''-----BEGIN CERTIFICATE-----
MIIDhzCCAm+gAwIBAgIUAZh6QsK9n4+VNgX+9Of1iKRNoVEwDQYJKoZIhvcNAQEL
BQAwUzELMAkGA1UEBhMCVVMxEDAOBgNVBAgMB0ZpbnRlY2gxFDASBgNVBAoMC1N5
bmFwc2VNZXNoMRwwGgYDVQQDDBNTeW5hcHNlTWVzaC1Sb290LUNBMB4XDTI2MDgy
NzA3MjQwNVoXDTM2MDgyNDA3MjQwNVowUzELMAkGA1UEBhMCVVMxEDAOBgNVBAgM
B0ZpbnRlY2gxFDASBgNVBAoMC1N5bmFwc2VNZXNoMRwwGgYDVQQDDBNTeW5hcHNl
TWVzaC1Sb290LUNBMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAqwSD
fto9tRTsdEBwWqfPXOv8ytKRXUWeiP5jUL0KBR6P1Hcv6AJ5rfXNzNfwDgtahkQS
ax/sRfWkoAZOcFsnNDY6AbwebcI0jU8scvNUt/PqR4wn2BQCXDOqf9MQEfrRwKwa
DR/dXXXU/60TgHQW6CFGP1FKyPzcKXJZaL1jx+0xnZ+0KojqUykQZzJbCs0FZtWU
/yHBnzbjpz05Ix63Y1qHNlbTeky2vyod0MZR7b7lQdgNKkmgI7+ugKJkCZN4OQdc
RpqMe4PmJYmK5JWnPYDjCw+0xZsYG9yyZets2GKqzWHZjzm5o4luBixihHuFc2XS
ZiuMCwSern35adefkwIDAQABo1MwUTAdBgNVHQ4EFgQUSx9k1IU1YmAh2cudnEdy
tS18hS0wHwYDVR0jBBgwFoAUSx9k1IU1YmAh2cudnEdytS18hS0wDwYDVR0TAQH/
BAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAQEAMOfQ4hs6dImUN9t1gfgL5XpyFMnX
rqcplvdQjI103vi/fGJx4TPr6BIAFHGIWCvJp7q6DuqxKheU+X23vk5hkV0EnFps
QpcHQCYNdw+NZSl0LJUJhqCVsBETOfrbFJnTnTtM6x3HBoCaYQuE+iVZrbf/0qoN
h045zEziXsBhie1s/fXN6iof3IjLhnRs1j1oSvtCELrZAVFjlwzhi5Wo1CCNAkcc
VY81vh4uc9xUokvkOrEeR8DzHzpuF3QtQqTUCst3XRZmA1bPtE7xDlfombJ/wjM2
mzHf4DOMWpPCf1twRW4sT5RloYzJQLwqNjoCTk8VFZZtn+kmG/ZTiICJKA==
-----END CERTIFICATE-----
'''

db_admin_crt = '''-----BEGIN CERTIFICATE-----
MIIDazCCAlOgAwIBAgIUJwlGhcSsuWGqUqq5dzAOjEZkbSowDQYJKoZIhvcNAQEL
BQAwUzELMAkGA1UEBhMCVVMxEDAOBgNVBAgMB0ZpbnRlY2gxFDASBgNVBAoMC1N5
bmFwc2VNZXNoMRwwGgYDVQQDDBNTeW5hcHNlTWVzaC1Sb290LUNBMB4XDTI2MDgy
NzA3MjQwNVoXDTM2MDgyNDA3MjQwNVowSDELMAkGA1UEBhMCVVMxEDAOBgNVBAgM
B0ZpbnRlY2gxFDASBgNVBAoMC1N5bmFwc2VNZXNoMREwDwYDVQQDDAhkYl9hZG1p
bjCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALuyc8d8tdH4wtrun9gt
I/Xi/EdB4tF578ad/+6cn+6svO8U2lWzlwjleKRm2SC212VfJTlIB3nauAvURw7P
EVcs9vz7KYXUEY+FN5HW5Al9ngu/+q/ZMoUe2X3sw3E2hpae4fkn3/KxmDLj5sLW
4n/AmDhAZERRAOKcL2I5Aa+9eLQjayNvQ/k4L/gj8DLRSXZfkL2GOzua3bmMq6ri
k+dhSgCUGJ3ISjBPJlCkM1/z1u8fBFg82kFzs33fNplyV+wHzhSpCgBfMDzICHan
ZoHHWfOt0pa01bs/klyVUNxo4hoUAueiWwXSjU6DF9EpXFPZ/LSKW2cM7zFT1Rb4
vIsCAwEAAaNCMEAwHQYDVR0OBBYEFFTumt1Gx+iweXAOn4yuSRbGUPGQMB8GA1Ud
IwQYMBaAFEsfZNSFNWJgIdnLnZxHcrUtfIUtMA0GCSqGSIb3DQEBCwUAA4IBAQCL
pqtwUsCPN4Bf7PqRAujhkXJMmYyve9y2uQENNxBEzXRTkIuRqjkH8ENCTVY8JSIy
BD616Pa8MgWqiswmf547GYMSHt94x7/AM2L7lmkBPEk3+jg53vJ0jMqb1Ox1yk3+
GQJmSl9JjPkQtMAjWz/IKee55XriB0Ed6BMX0YTitaX5T6Zrvymw8dAtIKvnT40/
Q+KTaLqk1i8qrXwCT5XUbHGjbAmWSmV1125cfvIe9Y+mD3anI7YgOgsj8eNOGlE5
y4p2rKdF6IDHP6mPZULexoVl4jHZnmv42UzV0RpLzXQp+z2TOgvLaciishozWvtX
jc0wud6zMKR4QkYInc0z
-----END CERTIFICATE-----
'''

db_admin_key = '''-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7snPHfLXR+MLa
7p/YLSP14vxHQeLRee/Gnf/unJ/urLzvFNpVs5cI5XikZtkgttdlXyU5SAd52rgL
1EcOzxFXLPb8+ymF1BGPhTeR1uQJfZ4Lv/qv2TKFHtl97MNxNoaWnuH5J9/ysZgy
4+bC1uJ/wJg4QGREUQDinC9iOQGvvXi0I2sjb0P5OC/4I/Ay0Ul2X5C9hjs7mt25
jKuq4pPnYUoAlBidyEowTyZQpDNf89bvHwRYPNpBc7N93zaZclfsB84UqQoAXzA8
yAh2p2aBx1nzrdKWtNW7P5JclVDcaOIaFALnolsF0o1OgxfRKVxT2fy0iltnDO8x
U9UW+LyLAgMBAAECggEAD75qYhTEBtlCtZd8y+a5afdrVCoiyucF+ux82mMZMoLF
vu4frumcpRqOZzKDSvBbRT2uWHgsvFwMF7NAxJgPgHbylAoYk7OpR2xpWq/M5T48
ArNMj/HRgC4JbeZtXF0yUTGsNbh9BeqUoCF9VTbYvSuGo81EO8tpnhhzYbNIwMNT
EEJKMVWgc3PkwYmQlnWjl2psbswu+2qQneeqk5oht7ZIkh0dEJAHQseoRgpaAY8d
LIWamye6zyoa0Ya7vsVYp6ZriF44CcYTX2xoJ18I2Pfv+TONP4ASWG0p3Y7tvrxL
FKo7CVF/zdUlApuZedowsE3po09ky/6LtQ1hqaGYeQKBgQDvo1C924BoGgmOGPFl
jGzSG7QX5K1qRv7QGcoZDtSn3vo2Ir0spGrjmHNEGFgVoYLneVLE+ja4SR7PXo8b
MwmsKEJOk92+ftP6D/flOjRfdaZIqPOVKwJ/9ksUONj7p7D7cIwdEPK0ej2cXj1L
vLxtZx6wlb28SL4L4Ayjx9u+AwKBgQDIg0A71vy9Idx/VAxrLvRdCjZvQE+iBj3f
a7qSRWb4nyHisarnxFFi5GBXF52CeFNEf1TmTIWAdOSyxqBzMOV1DbZmqw1LxTA5
P6kf1tF5x2EgY7P8iBDY3sUGXkCDiuqnne2mgnitag/cW8/ZMPr52HQkVPVFjhcE
vfWT0X7k2QKBgB/aHlZOAcBUjaaUjCmKQ8CdrA9s9tvkeeQhOWqhPQTfL3TYozp2
1DpSPifz8GlXoXWw+55w/6r5FR5NHEpqO0PlygJ1xwiWBQj87F9MoD97/NE1m8Ld
B6UIkKwsbjLs9CpHqGgIo6n3gY7yO8WAXa9RAJRKIwEOziv36NYwL3YPAoGAOT2m
165fBkslXEANL4f/AJSKx6WvVgy8Gwzw/RLM+4rKLKIVrQZRSY7ypco7D+TzuGk1
Pm136xzzsMmdQmUiDBF3EcYhDJFlW+J9kHZN5JrzckCkQCJD1PV7f37moebFaEZg
cplqg+70Si73ngQqkaqmNTz/q/SNQ7BK7ADxXbkCgYEA0yJI34Z0vs4ETTXPbbIV
XiEmcz1gw7S5hHA+tlehcDIlwUom8OOGUnkd6JpKCHRzbkDX7F0AMYe+lQ7FUjAd
rj5YDsOkEKVP1B2mNmIGHuZwVN4xwPyMffLfMEndopAiTQov0/xEx7MgSEAkkX4L
RNbFUTYYorfzeGVQwu4MbiA=
-----END PRIVATE KEY-----
'''

with open('${CERTS_DIR}/ca.crt', 'w') as f: f.write(ca_crt.strip() + '\n')
with open('${CERTS_DIR}/db-admin.crt', 'w') as f: f.write(db_admin_crt.strip() + '\n')
with open('${CERTS_DIR}/db-admin.key', 'w') as f: f.write(db_admin_key.strip() + '\n')
"

chmod 755 "${INSTALL_DIR}" "${CERTS_DIR}"
chmod 600 "${CERTS_DIR}"/*.key
chmod 644 "${CERTS_DIR}"/*.crt
chown -R "${BROKER_USER}:${BROKER_USER}" "${CERTS_DIR}"

python3 -m venv --system-site-packages "${APP_DIR}/venv"

cat << 'EOF' > "${APP_DIR}/broker_daemon.py"
import os
import sys
import json
import base64
import socket
import threading
import pickle
import yaml
from flask import Flask, jsonify

app = Flask(__name__)

VALID_USER = "synapse_feeder"
VALID_PASS = "Feeder_EventBus_99214"
QUEUE_NAME = "events.financial.audit"

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "service": "SynapseMesh Financial Event Broker",
        "status": "OPERATIONAL",
        "broker_port": 5672,
        "queue": QUEUE_NAME,
        "supported_formats": ["json", "pyyaml", "pickle"]
    })

def handle_client_connection(client_socket):
    try:
        raw_data = b""
        client_socket.settimeout(5.0)
        while True:
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            raw_data += chunk
            if b"\n\n" in raw_data or len(raw_data) > 65536:
                break

        if not raw_data:
            client_socket.close()
            return

        try:
            msg = json.loads(raw_data.decode("utf-8", errors="ignore").strip())
            auth = msg.get("auth", "")
            if auth != f"{VALID_USER}:{VALID_PASS}":
                client_socket.sendall(b"ERR: Unauthorized broker credentials\n")
                client_socket.close()
                return

            fmt = msg.get("format", "json")
            payload_data = msg.get("payload", "")

            if fmt == "pickle":
                decoded = base64.b64decode(payload_data)
                obj = pickle.loads(decoded)
                client_socket.sendall(b"OK: Event batch evaluated successfully\n")
            elif fmt == "pyyaml":
                obj = yaml.unsafe_load(payload_data)
                client_socket.sendall(b"OK: YAML event payload ingested\n")
            else:
                client_socket.sendall(b"OK: Standard JSON event acknowledged\n")

        except Exception as e:
            if raw_data.startswith(b"PICKLE:"):
                payload_part = raw_data[7:].strip()
                decoded = base64.b64decode(payload_part)
                pickle.loads(decoded)
                client_socket.sendall(b"OK: Direct stream processed\n")
            else:
                client_socket.sendall(f"ERR: {str(e)}\n".encode())
    except Exception:
        pass
    finally:
        try:
            client_socket.close()
        except Exception:
            pass

def run_tcp_broker():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", 5672))
    server.listen(10)
    while True:
        client_sock, _ = server.accept()
        t = threading.Thread(target=handle_client_connection, args=(client_sock,), daemon=True)
        t.start()

if __name__ == "__main__":
    broker_thread = threading.Thread(target=run_tcp_broker, daemon=True)
    broker_thread.start()
    app.run(host="0.0.0.0", port=8080)
EOF

chmod +x "${APP_DIR}/broker_daemon.py"
chown -R "${BROKER_USER}:${BROKER_USER}" "${APP_DIR}"

cat << EOF > "${CONFIG_DIR}/database.env"
# SynapseMesh Core Ledger Database Connection Profile
DB_HOST="${CORE_DB_HOST}"
DB_PORT="${CORE_DB_PORT}"
DB_NAME="${CORE_DB_NAME}"
DB_USER="${CORE_DB_USER}"
SSL_MODE="verify-full"
SSL_CERT="${CERTS_DIR}/db-admin.crt"
SSL_KEY="${CERTS_DIR}/db-admin.key"
SSL_ROOT_CA="${CERTS_DIR}/ca.crt"
EOF

chown -R "${BROKER_USER}:${BROKER_USER}" "${CONFIG_DIR}"
chmod 700 "${CONFIG_DIR}"
chmod 644 "${CONFIG_DIR}/database.env"

cat << EOF > /etc/systemd/system/synapse-broker.service
[Unit]
Description=SynapseMesh Financial Event Bus and Celery Pipeline Broker
After=network.target

[Service]
Type=simple
User=${BROKER_USER}
Group=${BROKER_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/venv/bin/python3 ${APP_DIR}/broker_daemon.py
Restart=always
RestartSec=3
StandardOutput=append:${LOG_DIR}/broker.log
StandardError=append:${LOG_DIR}/broker.err

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now synapse-broker.service

echo "[+] VM 2 (synapse-broker) ready: broker port 5672 / health port 8080"
