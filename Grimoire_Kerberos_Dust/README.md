# Kerberos Dust — Blue Team Threat Hunting & DFIR Investigation

## Scenario Overview
* **Incident ID:** `INC-2026-0881`
* **Target Organization:** Synapse Financial Technologies Ltd (`synapse.corp`)
* **Classification:** High / Critical (Active Directory Domain Compromise)
* **Domain Controller:** `DC01.synapse.corp` (`10.10.10.5`)
* **Compromised Endpoint:** `WS01.synapse.corp` (`10.10.10.50`)
* **Discipline:** Defend / Digital Forensics & Incident Response (DFIR)
* **Difficulty:** Hard

## Incident Background
On August 28, 2026, at approximately 14:10 UTC, the Security Operations Center (SOC) detected abnormal Kerberos ticket requests and domain replication operations originating from internal workstation `10.10.10.50` (`WS01`). 

A complete forensic telemetry package was captured from Domain Controller `DC01.synapse.corp` and endpoint `WS01.synapse.corp` to support an end-to-end incident response investigation.

## Artifacts Archive & Password
The forensic evidence is bundled inside `artifacts.zip`.
* **Archive Password:** `offsec`

### Included Artifacts:
1. `kerberos_traffic.pcap`: Full packet capture containing DNS SRV lookups, LDAP queries, Kerberos AS-REQ/AS-REP (RC4 downgrade), TGS-REQ/TGS-REP (targeted Kerberoasting), and MSRPC DRSUAPI replication calls.
2. `Security_Events.json`: Windows Security Event Log (`Security.evtx` export from `DC01.synapse.corp`), including Events 4768, 4769, 4624 (Logon Type 9), 4662, and 4698.
3. `Sysmon_Events.json`: Microsoft-Windows-Sysmon process and command line execution telemetry from `WS01.synapse.corp` (`Rubeus.exe`, `mimikatz.exe`, `schtasks.exe`).
4. `Incident_Timeline.csv`: Cross-correlated chronological SIEM timeline of all events across the environment in UTC.

## Investigation Objective
Analyze the provided artifacts, answer the 10 investigation questions in `questions_and_answers.md`, and reconstruct the complete adversary killchain from initial foothold to domain persistence.
