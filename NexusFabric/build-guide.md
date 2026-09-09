# Build Guide for NEXUS-FABRIC (3-Host Chained Enterprise Lab)

## Status

**NTP**: Off  
**Firewall**: On  
**Updates**: Off  
**ICMP**: On  
**IPv6**: Off  
**AV or Security**: Off

## Overview

**Lab Format**: Chain (3-Host Multi-VM Enterprise Mesh)  
**OS (VM 1, VM 2, VM 3)**: Ubuntu 24.04 LTS / 22.04 LTS (x86_64 / aarch64)  
**VM 1 Hostname**: nexus-edge (`10.211.55.10` / Dynamic)  
**VM 2 Hostname**: nexus-broker (`10.211.55.11` / Dynamic)  
**VM 3 Hostname**: nexus-core (`10.211.55.12` / Dynamic)  
**Vulnerability 1 (Perimeter Foothold)**: Webhook Diagnostic Engine Server-Side Request Forgery (SSRF) & Internal Management API Key Extraction  
**Vulnerability 2 (1st Pivot & Worker Compromise)**: Authenticated Redis Mesh Task Queue Command Injection via Async Worker Daemon  
**Vulnerability 3 (2nd Pivot & Root Takeover)**: Core Ledger RPC Pre-Backup Hook Injection & Sudo Orchestrator Privilege Escalation  
**Admin Username**: root  
**Low Priv Username (VM 1)**: nexus-app  
**Low Priv Password (VM 1)**: NexusEdge_Pass_2026!  
**Low Priv Username (VM 2)**: worker-svc  
**Low Priv Password (VM 2)**: WorkerSvc_Mesh_7712!  
**Location of local.txt (VM 1)**: `/home/nexus-app/local.txt`  
**Location of proof.txt (VM 3)**: `/root/proof.txt`  

## Machine Ordering & Network Layout

1. **VM 1 (Edge Gateway):** Exposes Port 80 (HTTP) to external attackers. Connected to internal management subnet `10.211.55.0/24`.
2. **VM 2 (Task Broker & Worker):** Internal Redis message bus on Port 6379. Reachable only by pivoting through VM 1.
3. **VM 3 (Core Ledger & Vault):** Isolated ledger database on Port 9090. Reachable via double-hop pivoting through VM 2.

## Required Settings

* **VM 1 (Edge):** 1 vCPU, 1 GB RAM, 10 GB Disk
* **VM 2 (Broker):** 1 vCPU, 1 GB RAM, 10 GB Disk
* **VM 3 (Core):** 1 vCPU, 1 GB RAM, 10 GB Disk
* **Total Cluster Footprint:** 3 vCPUs, 3 GB RAM (Lightweight & High Performance)

## Build Guide

1. Deploy three base Ubuntu 22.04 / 24.04 LTS instances (VM 1, VM 2, VM 3).
2. On **VM 1** (`nexus-edge`):
   * Upload `build-vm1.sh`
   * Run as root: `sudo bash build-vm1.sh`
3. On **VM 2** (`nexus-broker`):
   * Upload `build-vm2.sh`
   * Run as root: `sudo bash build-vm2.sh`
4. On **VM 3** (`nexus-core`):
   * Upload `build-vm3.sh`
   * Run as root: `sudo bash build-vm3.sh`
5. Verify services:
   * VM 1: `curl -s http://10.211.55.10/` (HTTP 200)
   * VM 2: `redis-cli -h 10.211.55.11 -a "nexus_cluster_auth_8819" ping` (PONG)
   * VM 3: `curl -s http://10.211.55.12:9090/health` (HTTP 200)
6. Automated Solvability Validation:
   ```bash
   python3 autopwn.py <VM1_IP>
   ```
