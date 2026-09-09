#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

DB_NAME="synapse_ledger"
DB_USER="db_admin"
INSTALL_DIR="/opt/synapse"
CERTS_DIR="${INSTALL_DIR}/certs"
LOG_DIR="/var/log/synapse"
FLAG_ROOT_PATH="/root/proof.txt"

apt-get update -y
apt-get install -y --no-install-recommends \
    curl \
    wget \
    openssl \
    ca-certificates \
    net-tools \
    socat \
    postgresql \
    postgresql-contrib \
    python3 \
    python3-psycopg2 \
    jq

mkdir -p "${INSTALL_DIR}" "${CERTS_DIR}" "${LOG_DIR}"

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

server_crt = '''-----BEGIN CERTIFICATE-----
MIIDyzCCArOgAwIBAgIUJwlGhcSsuWGqUqq5dzAOjEZkbSswDQYJKoZIhvcNAQEL
BQAwUzELMAkGA1UEBhMCVVMxEDAOBgNVBAgMB0ZpbnRlY2gxFDASBgNVBAoMC1N5
bmFwc2VNZXNoMRwwGgYDVQQDDBNTeW5hcHNlTWVzaC1Sb290LUNBMB4XDTI2MDgy
NzA3MjU1OFoXDTM2MDgyNDA3MjU1OFowVTELMAkGA1UEBhMCVVMxEDAOBgNVBAgM
B0ZpbnRlY2gxFDASBgNVBAoMC1N5bmFwc2VNZXNoMR4wHAYDVQQDDBVzeW5hcHNl
LWNvcmUuaW50ZXJuYWwwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQCt
SXQrqDGGWMrZ+bs/Q36F7pcigFAV4qK+Tygyxtk08pl0WiPvCB1YriymHsOlDX/k
H8Hy8rlIywXWVykOE36wloNzjer9GKpnHY7WSbvFP84zvxk5vUS7uGP160hIXr1W
fHYA1LPLawm9G7SfDvxjQEB+tcBl2ekRCTJv/oWj7y0FG8H9/ritB7VEzWZctEOL
DLc1/+SUmK0q93I1pG4L0O3kDJSlcKWuYG3+AhUv8+qcyO/Dp+RTrMgOPr01ZyZZ
xxelFXW0a2Nyuf7j6kRwbFcUiOzGTHiEiyjOHW4gQjreyv9BqHgM73gosxvMA3+D
C7hgc4ZU7PLcagVJ8E65AgMBAAGjgZQwgZEwCQYDVR0TBAIwADALBgNVHQ8EBAMC
BeAwNwYDVR0RBDAwLoIVc3luYXBzZS1jb3JlLmludGVybmFsgglsb2NhbGhvc3SH
BArTNwyHBH8AAAEwHQYDVR0OBBYEFCjuwHsxADNXe8M84GQSJKr8bVVjMB8GA1Ud
IwQYMBaAFEsfZNSFNWJgIdnLnZxHcrUtfIUtMA0GCSqGSIb3DQEBCwUAA4IBAQCH
o9QbjH40ZPqX71NegvHXqE6lLSVdP3j3sKHdfMxYIwlaR1grCEmC8RxPv8S9n0Zl
U04bFZiL6j//BE1E8N2i5llPDXoCsaBvNhF+8vHxxcAX1u6+uWBVEn+Dg4Aunast
Jp0AEsVf23oXdAdnhXzV83v2M+hbkEczjhFq6aTzZc+JiKe2h3VQHKgi7M9+oH/p
aUveLIfMRoOXd6OokZiIUCgYIb126Q9Wtsx+zrEvHIBAwJJs8VVY570S8abNmYQ4
3g9XVvjI8i3qQNVf8X5CPjDVzq0EZVP69ALSWxv9thenJL09YQ+lG/EehFxfoVN1
lFSWZBLa7QN3R1gMXeUe
-----END CERTIFICATE-----
'''

server_key = '''-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCtSXQrqDGGWMrZ
+bs/Q36F7pcigFAV4qK+Tygyxtk08pl0WiPvCB1YriymHsOlDX/kH8Hy8rlIywXW
VykOE36wloNzjer9GKpnHY7WSbvFP84zvxk5vUS7uGP160hIXr1WfHYA1LPLawm9
G7SfDvxjQEB+tcBl2ekRCTJv/oWj7y0FG8H9/ritB7VEzWZctEOLDLc1/+SUmK0q
93I1pG4L0O3kDJSlcKWuYG3+AhUv8+qcyO/Dp+RTrMgOPr01ZyZZxxelFXW0a2Ny
uf7j6kRwbFcUiOzGTHiEiyjOHW4gQjreyv9BqHgM73gosxvMA3+DC7hgc4ZU7PLc
agVJ8E65AgMBAAECggEAFRCK6kQsugS46vCmPAlhu9juHxPrOE/Xoev4Klz8+ihb
8laDS/sn6xfoJkzy0jFvCJ16K4TpNFG2rNClVVhWFBQF2HIJ3Nim3ThM/NxTcqXA
FI8AO2I4NNwULaibXa3DlRv10cHJddq2ATqZFSVClbORq31/TPpFcExWiOHvH6dg
D4yu8KuJ7I/haY3t3P9DOA6W7ldfofjPe4Oobd3yVzHmsOo8Zj03HPEaevmmxPgY
+5N+coNQplIvQKC6j2jsGpwtPFR2lXqu9PoMhoseDAA2h2lQ1Ds0LDpwdic9mi2a
vrAfFERPhfzYZb0WZ7LqhX4qAu9T6mBvBxtU3hS9QQKBgQDYOkcBfmLxL+yeNxzn
3NGCcQ8TdmBqcu2x3wg955T7YYsCaf9XcrffRuTNy7IekHTbhNDbW2Opxte8mNLk
nvlKKmNpVbbAxaUATtigKa+V9qq6f0Eb0m+pKzglKWn87poDDATESkYYU3zKfBsE
uZH8uec2mCr9kf2NanxkyAp0+QKBgQDNKS9UhUwC7veTIAsGxkFbqgOFQ3ik1rBc
jU13pinzq7kzTmp/gOiF373fZMdXcW6yPJcw1WrgciRkuJgXteSZWWhekK0QfhaZ
lg99iHP3NAdyL6+Hef9AsirWJ5WiNYTCtqIaYtDkyjz7aW0mf84spjcHMRb33c7e
HHO/UZnXwQKBgHcucBLfsfOU4cw3PoSCjyxh2th0aCJkZKWk9GsCqXiBxFg5SpfN
0JGOBvFz9CKqpu6UX3Z5Ag8DXchDSALhqTB6+r6FkyzgA9mOnBJzx6dWBba0C5Ql
QoyxGMpK8HOMpHFHf50d/1LLOb5194J8Mn5ljY7nAtMvU91Ns3DtXe4pAoGBAJfM
kFueYTaOcBqpC9+QU42qRv6UhLCatVVVq+sKxGGqPtcKf1wmGmXrvcaL/77gjEJO
+KNGVdUKP4lS2B47FJCuib3mmFbqpHgxgvakPwG6uoOvatX323iYG3/nPB0QMlIL
5fdWBDA0v1hakkt5Jyj8Nx0YImF1+fl33eDCVO1BAoGAGJCSiix5yVXHIqNWtdtg
evHxFWNsXQTN+xYxROsZzwRHlWFKaM8ABBvegTaFJ5CqCXPKRMwmaI+ujArqZjiH
UtQph+kzs/qPrmXIf4JmUKiEfnuajTHlQKSFdEGYA0dOGlxDrXkfRO1M9F+D36MU
KwR2QHI1cvkFIwS0b1iZHPw=
-----END PRIVATE KEY-----
'''

with open('${CERTS_DIR}/ca.crt', 'w') as f: f.write(ca_crt.strip() + '\n')
with open('${CERTS_DIR}/server.crt', 'w') as f: f.write(server_crt.strip() + '\n')
with open('${CERTS_DIR}/server.key', 'w') as f: f.write(server_key.strip() + '\n')
"

chmod 755 "${INSTALL_DIR}" "${CERTS_DIR}"
chmod 600 "${CERTS_DIR}"/*.key
chmod 644 "${CERTS_DIR}"/*.crt
chown -R postgres:postgres "${CERTS_DIR}"

PG_CONF_DIR=$(find /etc/postgresql -name "postgresql.conf" | head -n 1 | xargs dirname)

cat << EOF >> "${PG_CONF_DIR}/postgresql.conf"
listen_addresses = '*'
ssl = on
ssl_cert_file = '${CERTS_DIR}/server.crt'
ssl_key_file = '${CERTS_DIR}/server.key'
ssl_ca_file = '${CERTS_DIR}/ca.crt'
EOF

cat << EOF > "${PG_CONF_DIR}/pg_hba.conf"
local   all             postgres                                peer
local   all             all                                     md5
hostssl ${DB_NAME}      ${DB_USER}      0.0.0.0/0               cert clientcert=verify-full
host    all             all             127.0.0.1/32            trust
EOF

systemctl restart postgresql

sudo -u postgres psql -c "CREATE USER ${DB_USER};" || true
sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};" || true
sudo -u postgres psql -d "${DB_NAME}" -c "
CREATE TABLE IF NOT EXISTS system_telemetry (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(64),
    metric_value VARCHAR(256),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS synapse_maintenance_tasks (
    task_id SERIAL PRIMARY KEY,
    command TEXT NOT NULL,
    status VARCHAR(32) DEFAULT 'PENDING',
    output TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP
);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${DB_USER};
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${DB_USER};

INSERT INTO system_telemetry (metric_name, metric_value) VALUES 
    ('cluster_health', 'OPTIMAL'),
    ('ledger_version', 'v4.2.0-hotfix3'),
    ('settlement_engine', 'ONLINE');
"

cat << 'EOF' > /usr/local/bin/synapse-db-maintenance.py
#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import psycopg2

def process_pending_tasks():
    try:
        conn = psycopg2.connect(
            dbname="synapse_ledger",
            user="postgres",
            host="127.0.0.1"
        )
        cur = conn.cursor()
        cur.execute("SELECT task_id, command FROM synapse_maintenance_tasks WHERE status = 'PENDING' ORDER BY task_id ASC LIMIT 1 FOR UPDATE;")
        row = cur.fetchone()
        if row:
            task_id, cmd = row
            try:
                res = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                output = res.stdout + res.stderr
                cur.execute(
                    "UPDATE synapse_maintenance_tasks SET status = 'COMPLETED', output = %s, executed_at = CURRENT_TIMESTAMP WHERE task_id = %s;",
                    (output, task_id)
                )
            except Exception as e:
                cur.execute(
                    "UPDATE synapse_maintenance_tasks SET status = 'FAILED', output = %s, executed_at = CURRENT_TIMESTAMP WHERE task_id = %s;",
                    (str(e), task_id)
                )
            conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass

if __name__ == "__main__":
    while True:
        process_pending_tasks()
        time.sleep(2)
EOF

chmod +x /usr/local/bin/synapse-db-maintenance.py

cat << 'EOF' > /etc/systemd/system/synapse-maintenance.service
[Unit]
Description=SynapseMesh Core Database Maintenance Worker
After=postgresql.service

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 /usr/local/bin/synapse-db-maintenance.py
Restart=always
RestartSec=2
StandardOutput=append:/var/log/synapse/maintenance.log
StandardError=append:/var/log/synapse/maintenance.err

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now synapse-maintenance.service

ROOT_FLAG_HASH=$(openssl rand -hex 16)
echo "${ROOT_FLAG_HASH}" > "${FLAG_ROOT_PATH}"
chmod 600 "${FLAG_ROOT_PATH}"

echo "[+] VM 3 (synapse-core) ready: PostgreSQL 5432 (mTLS) (Root Flag: ${ROOT_FLAG_HASH})"
