# Build Guide for AetherGrid (Chained-Host Lab)

## Status

**NTP**: Off  
**Firewall**: On  
**Updates**: Off  
**ICMP**: On  
**IPv6**: Off  
**AV or Security**: Off

## Overview

**Lab Format**: Chain (2-Host VM)  
**OS (VM 1 & VM 2)**: Ubuntu 24.04 LTS / 22.04 LTS (x86_64 / arm64)  
**VM 1 Hostname**: aether-gateway (`10.211.55.10`)  
**VM 2 Hostname**: aether-core (`10.211.55.11`)  
**Vulnerability 1 (Initial Access)**: CI/CD Pipeline Diagnostic Token Leakage & Authenticated Template Expression Injection  
**Vulnerability 2 (Lateral Movement & PrivEsc)**: HashiCorp Vault AppRole Credential Extraction to Nomad Cluster Orchestration Root Execution  
**Admin Username**: root  
**Low Priv Username**: developer  
**Low Priv Password**: DevPortal_AutoSync_2024!  
**Location of local.txt (VM 1)**: `/home/developer/local.txt`  
**Location of proof.txt (VM 2)**: `/root/proof.txt`  

## Required Settings

**VM 1 (Gateway)**: 1 vCPU, 1GB RAM, 10GB Disk  
**VM 2 (Core)**: 1 vCPU, 1GB RAM, 10GB Disk  
**Network**: Private / bridged subnet between VM 1 and VM 2  

## Build Guide

1. Deploy two base Ubuntu 22.04 / 24.04 LTS instances (VM 1 and VM 2).
2. On **VM 1** (`aether-gateway`):
   - Upload `build-vm1.sh`
   - Run as root: `sudo bash build-vm1.sh`
3. On **VM 2** (`aether-core`):
   - Upload `build-vm2.sh`
   - Run as root: `sudo bash build-vm2.sh`
4. Verify services:
   - VM 1: Port 80 HTTP (`AetherGrid CI/CD Gateway`)
   - VM 2: Port 8200 HTTP (`Vault`), Port 4646 HTTP (`Nomad`)
