# Build Guide for SYNAPSE-MESH (3-Host Chained Enterprise Lab)

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
**VM 1 Hostname**: synapse-gateway (`10.211.55.10` / Dynamic)  
**VM 2 Hostname**: synapse-broker (`10.211.55.11` / Dynamic)  
**VM 3 Hostname**: synapse-core (`10.211.55.12` / Dynamic)  
**Vulnerability 1 (Perimeter Foothold)**: GraphQL API & JWT Key Confusion (RS256 to HS256 Public Key Signature Bypass)  
**Vulnerability 2 (1st Pivot & Worker Compromise)**: RabbitMQ Asynchronous Event Bus Insecure Object Deserialization  
**Vulnerability 3 (2nd Pivot & Root Takeover)**: PostgreSQL 16 mTLS Mutual Authentication to Root Maintenance Daemon Execution  
**Admin Username**: root  
**Low Priv Username (VM 1)**: api-svc  
**Low Priv Password (VM 1)**: ApiGateway_Sync_2026!  
**Location of local.txt (VM 1)**: `/home/api-svc/local.txt`  
**Location of proof.txt (VM 3)**: `/root/proof.txt`  

## Machine Ordering & Network Layout

1. **VM 1 (Edge Gateway):** Exposes Port 80 (HTTP) and Port 4000 (GraphQL API) to external attackers. Connected to internal subnet `10.211.55.0/24`.
2. **VM 2 (Event Broker):** Internal message bus on Port 5672 and Port 8080. Reachable only via pivoting through VM 1.
3. **VM 3 (Core Database):** Isolated ledger database on Port 5432 with strict mTLS enforcement. Reachable via double-hop pivoting through VM 2.

## Required Settings

* **VM 1 (Gateway):** 1 vCPU, 1 GB RAM, 10 GB Disk
* **VM 2 (Broker):** 1 vCPU, 1 GB RAM, 10 GB Disk
* **VM 3 (Core):** 1 vCPU, 1 GB RAM, 10 GB Disk
* **Total Cluster Footprint:** 3 vCPUs, 3 GB RAM (Lightweight & High Performance)

## Build Guide

1. Deploy three base Ubuntu 22.04 / 24.04 LTS instances (VM 1, VM 2, VM 3).
2. On **VM 1** (`synapse-gateway`):
   * Upload `build-vm1.sh`
   * Run as root: `sudo bash build-vm1.sh`
3. On **VM 2** (`synapse-broker`):
   * Upload `build-vm2.sh`
   * Run as root: `sudo bash build-vm2.sh`
4. On **VM 3** (`synapse-core`):
   * Upload `build-vm3.sh`
   * Run as root: `sudo bash build-vm3.sh`
5. Verify services:
   * VM 1: `curl -s http://10.211.55.10/` (HTTP 200) & `http://10.211.55.10:4000/graphql`
   * VM 2: `curl -s http://10.211.55.11:8080/health` (HTTP 200)
   * VM 3: Port 5432 (PostgreSQL with SSL enabled)
6. Automated Solvability Validation:
   ```bash
   python3 autopwn.py <VM1_IP>
   ```

