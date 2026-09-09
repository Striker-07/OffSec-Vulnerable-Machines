# Offensive Security (OffSec) Vulnerable Machines & Labs Portfolio

> A curated collection of enterprise-grade vulnerable machines, multi-host cyber range environments, and threat-simulation challenges authored and submitted for **Offensive Security (OffSec) User Generated Content (UGC)**.

[![Author](https://img.shields.io/badge/Author-Ziyodullo%20Tolaganov-blue.svg)](https://www.linkedin.com/in/ziyodullo-to-laganov-681bab257/)
[![Certification](https://img.shields.io/badge/PortSwigger-BSCP%20Certified-orange.svg)](https://portswigger.net)
[![Platform](https://img.shields.io/badge/OffSec-Approved%20UGC%20Creator-red.svg)](https://www.offsec.com)

---

## 🎯 Executive Summary

This repository contains the architecture designs, provisioning code, automated exploit solvers, and technical walkthroughs for four enterprise-grade offensive security challenges and vulnerable machines. Each project has been engineered to mirror modern enterprise environments and cloud-native architectures, passing strict technical review and anti-cheat standards.

---

## 📁 Machine & Challenge Overview

| Project | Target Environment | Difficulty | Attack Vector Summary | Key Artifacts |
| :--- | :--- | :--- | :--- | :--- |
| **[NexusFabric](./NexusFabric/)** | Multi-VM Enterprise Infrastructure | **Hard** | API Logic Abuse, Internal Pivot, Service Misconfigurations | `autopwn.py`, `build-vm*.sh`, `walkthrough.pdf` |
| **[AetherGrid](./AetherGrid/)** | 2-Host CI/CD & Cluster Architecture | **Hard** | CI/CD Webhook RCE, HashiCorp Vault AppRole Abuse, Nomad Orchestrator Privileged Job | `autopwn.py`, `build-guide.md`, `walkthrough.pdf` |
| **[SynapseMesh](./SynapseMesh/)** | 3-VM Enterprise Network Architecture | **Hard** | Mesh Gateway Compromise, Lateral Network Pivoting, Multi-stage PrivEsc | `autopwn.py`, `build-vm[1-3].sh`, `walkthrough.pdf` |
| **[Grimoire: Kerberos Dust](./Grimoire_Kerberos_Dust/)** | Enterprise Active Directory & Forensics | **Medium / Hard** | Kerberos Traffic Analysis, AS-REP / TGS Abuse, Ticket Forgery Investigation | PCAP, Event Logs, Automated Compilers |

---

## 🛠️ Detailed Project Breakdowns

### 1. [NexusFabric](./NexusFabric/)
* **Architecture:** Multi-host distributed Linux network simulating a segmented corporate infrastructure.
* **Initial Access:** API gateway authentication bypass and parameter tampering.
* **Lateral Movement:** Internal routing across network boundaries via SSH tunneling and pivoting.
* **Privilege Escalation:** Automated privilege escalation chain targeting misconfigured internal daemons and credential stores.
* **Deliverables:** Full automated Python solver (`autopwn.py`), multi-VM setup scripts, and publication-ready technical walkthrough.

### 2. [AetherGrid](./AetherGrid/)
* **Architecture:** 2-Host chained cloud-native architecture running on Ubuntu 24.04 LTS.
* **VM 1 (Perimeter):** Gateway CI/CD engine exposing automated build webhooks. Template expression interpolation leads to subshell command execution under the `developer` context (`local.txt`).
* **Pivoting & Escalation:** Discovery of long-lived HashiCorp Vault AppRole credentials (`RoleID` & `SecretID`). SSH dynamic SOCKS routing into the private cluster (`10.211.55.11`).
* **VM 2 (Core):** Authenticating to HashiCorp Vault REST API to extract administrative Nomad Cluster Management Tokens.
* **Root Takeover:** Crafting a privileged Nomad batch job that executes on the host with `root` authority, exfiltrating `proof.txt`.

### 3. [SynapseMesh](./SynapseMesh/)
* **Architecture:** 3-Host enterprise mesh environment with segmented network zones (DMZ, Internal App, Core Database).
* **Engineering Standards:** Fully reproducible automated bash installation scripts (`build-vm1.sh`, `build-vm2.sh`, `build-vm3.sh`) allowing rapid local provisioning and cloud deployment.
* **Key Attack Paths:** Complex multi-stage compromise requiring chaining web exploitation, credential reuse, internal service abuse, and kernel/cron exploitation.

### 4. [Grimoire: Kerberos Dust](./Grimoire_Kerberos_Dust/)
* **Architecture:** Threat simulation and forensics challenge designed for OffSec's Grimoire track.
* **Scenario:** Investigation of a targeted Active Directory compromise.
* **Artifacts:** Real-world network capture (`kerberos_traffic.pcap`), Windows Security event logs (`Security_Events.json`), and Sysmon telemetry (`Sysmon_Events.json`).
* **Challenge Design:** Requires identifying initial roasting activity, reconstructing ticket forging mechanisms, and tracking the adversary's lateral movement.

---

## ⚡ Engineering & Quality Standards

All projects adhere strictly to modern cyber range and CTF standards:
- **Reproducible Automation:** Clean provisioning scripts with no manual configuration required.
- **Universal Networking:** Automatic DHCP resolution ensuring compatibility with Proving Grounds / PG Practice environments.
- **Automated Solvers:** End-to-end Python exploit scripts (`autopwn.py`) demonstrating 100% reliable exploit paths.
- **Publication-Ready Documentation:** High-resolution network architecture diagrams, step-by-step walkthroughs, and executive vulnerability summaries in both Markdown and PDF formats.

---

## 👤 Author

**Ziyodullo Tolaganov**
* PortSwigger Burp Suite Certified Practitioner (BSCP)
* Machine Author & Security Content Developer
* **LinkedIn:** [linkedin.com/in/ziyodullo-to-laganov-681bab257](https://www.linkedin.com/in/ziyodullo-to-laganov-681bab257/)

---
*Notice: These materials are authored by Ziyodullo Tolaganov for offensive security training and evaluation purposes. All challenge flags, configurations, and solution guides are protected intellectual property.*
