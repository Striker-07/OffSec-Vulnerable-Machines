# Questions and Answers — Kerberos Dust (Grimoire Lab)

## Summary Table

| # | Question Prompt | Answer / Proof | Difficulty | Grading | Evidence Source |
|---|---|---|---|---|---|
| **1** | What is the IP address of the initial compromised workstation? | `10.10.10.50` | Easy | Classic | `kerberos_traffic.pcap`, `Sysmon_Events.json` |
| **2** | Which Active Directory user account was targeted for AS-REP Roasting? | `backup_admin` | Intermediate | Classic | `Security_Events.json` (Event 4768), `kerberos_traffic.pcap` |
| **3** | What Kerberos encryption type (in hexadecimal format) was downgraded in the ticket requests? | `0x17` | Intermediate | Classic | `Security_Events.json` (Event 4768), `kerberos_traffic.pcap` |
| **4** | What Service Principal Name (SPN) was queried in the targeted Kerberoasting attack? | `MSSQLSvc/db01.synapse.corp:1433` | Intermediate | Classic | `Security_Events.json` (Event 4769), `kerberos_traffic.pcap` |
| **5** | What is the underlying domain username associated with the Kerberoasted service? | `svc_sql` | Intermediate | Classic | `Security_Events.json` (Event 4769), `Sysmon_Events.json` |
| **6** | What is the full binary path of the offensive tool executed on WS01 to request tickets? | `C:\Users\j.doe\AppData\Local\Temp\Rubeus.exe` | Intermediate | Classic | `Sysmon_Events.json` (Event 1) |
| **7** | What Windows Logon Type number was recorded during Overpass-the-Hash? | `9` | Intermediate | Classic | `Security_Events.json` (Event 4624) |
| **8** | What Active Directory Extended Access Right GUID was invoked for the DCSync attack? | `1131f6aa-9c07-11d1-f79f-00c04fc2dcd2` | Hard | Classic | `Security_Events.json` (Event 4662) |
| **9** | Which domain account was targeted alongside Administrator for DCSync hash replication? | `krbtgt` | Hard | Classic | `Sysmon_Events.json` (Event 1), `Incident_Timeline.csv` |
| **10** | What is the name of the malicious scheduled task registered on DC01? | `\SynapseHealthCheck` | Intermediate | Classic | `Security_Events.json` (Event 4698), `Sysmon_Events.json` |

---

## Detailed Questions, Answers, and Forensic Evidence

### Question 1
* **Prompt:** What is the IP address of the initial compromised workstation?
* **Answer:** `10.10.10.50`
* **Difficulty:** Easy
* **Grading:** Classic (Static)
* **Evidence:** In `kerberos_traffic.pcap`, all Kerberos AS-REQ and TGS-REQ packets originate from source IP `10.10.10.50` (`WS01.synapse.corp`). In `Sysmon_Events.json`, the workstation executes offensive binaries under user `j.doe`.

---

### Question 2
* **Prompt:** Which Active Directory user account was targeted for AS-REP Roasting?
* **Answer:** `backup_admin`
* **Difficulty:** Intermediate
* **Grading:** Classic (Static)
* **Evidence:** In `Security_Events.json`, Event ID 4768 records `PreAuthType: "0"` (pre-authentication not required) for `TargetUserName: "backup_admin"`. In Wireshark, filter `kerberos.msg_type == 10` confirms an AS-REQ without `PA-ENC-TIMESTAMP`.

---

### Question 3
* **Prompt:** What Kerberos encryption type (in hexadecimal format) was downgraded in the ticket requests?
* **Answer:** `0x17`
* **Difficulty:** Intermediate
* **Grading:** Classic (Static)
* **Evidence:** In `Security_Events.json`, Event ID 4768 and Event ID 4769 indicate `TicketEncryptionType: "0x17"` (RC4-HMAC-MD5). Wireshark filter `kerberos.etype == 23` shows explicit downgrade from AES256 (`0x12`).

---

### Question 4
* **Prompt:** What Service Principal Name (SPN) was queried in the targeted Kerberoasting attack?
* **Answer:** `MSSQLSvc/db01.synapse.corp:1433`
* **Difficulty:** Intermediate
* **Grading:** Classic (Static)
* **Evidence:** In `Security_Events.json`, Event ID 4769 indicates `ServiceName: "MSSQLSvc/db01.synapse.corp:1433"`. In `kerberos_traffic.pcap`, Frame 15 contains a Kerberos TGS-REQ specifically requesting a ticket for this SPN.

---

### Question 5
* **Prompt:** What is the underlying domain username associated with the Kerberoasted service?
* **Answer:** `svc_sql`
* **Difficulty:** Intermediate
* **Grading:** Classic (Static)
* **Evidence:** Cross-referencing `Security_Events.json` Event ID 4769 reveals `TargetUserName: "svc_sql@SYNAPSE.CORP"`, matching the domain service account mapped to the SQL SPN.

---

### Question 6
* **Prompt:** What is the full binary path of the offensive tool executed on WS01 to request tickets?
* **Answer:** `C:\Users\j.doe\AppData\Local\Temp\Rubeus.exe`
* **Difficulty:** Intermediate
* **Grading:** Classic (Static)
* **Evidence:** In `Sysmon_Events.json`, Event ID 1 (Process Create) logged at 14:10:04 UTC records `Image: "C:\\Users\\j.doe\\AppData\\Local\\Temp\\Rubeus.exe"` executing `asreproast /user:backup_admin /format:hashcat`.

---

### Question 7
* **Prompt:** What Windows Logon Type number was recorded during Overpass-the-Hash?
* **Answer:** `9`
* **Difficulty:** Intermediate
* **Grading:** Classic (Static)
* **Evidence:** In `Security_Events.json`, Event ID 4624 (Successful Logon) recorded at 14:22:40 UTC displays `LogonType: 9` (`NewCredentials`), typical of Rubeus / Mimikatz `asktgt /ptt` overpass-the-hash execution.

---

### Question 8
* **Prompt:** What Active Directory Extended Access Right GUID was invoked for the DCSync attack?
* **Answer:** `1131f6aa-9c07-11d1-f79f-00c04fc2dcd2`
* **Difficulty:** Hard
* **Grading:** Classic (Static)
* **Evidence:** In `Security_Events.json`, Event ID 4662 (Directory Service Access) records `AccessMask: "0x100"` (Control Access) and lists Property GUID `1131f6aa-9c07-11d1-f79f-00c04fc2dcd2` (`DS-Replication-Get-Changes-All`), confirming a DCSync replication attack.

---

### Question 9
* **Prompt:** Which domain account was targeted alongside Administrator for DCSync hash replication?
* **Answer:** `krbtgt`
* **Difficulty:** Hard
* **Grading:** Classic (Static)
* **Evidence:** In `Sysmon_Events.json`, Event ID 1 at 14:30:14 UTC captures the command line:  
  `mimikatz.exe "lsadump::dcsync /domain:synapse.corp /user:krbtgt" "lsadump::dcsync /domain:synapse.corp /user:Administrator" exit`.

---

### Question 10
* **Prompt:** What is the name of the malicious scheduled task registered on DC01?
* **Answer:** `\SynapseHealthCheck`
* **Difficulty:** Intermediate
* **Grading:** Classic (Static)
* **Evidence:** In `Security_Events.json`, Event ID 4698 (A scheduled task was created) logged at 14:38:50 UTC identifies `TaskName: "\\SynapseHealthCheck"`, executing an obfuscated PowerShell payload under `NT AUTHORITY\SYSTEM`.
