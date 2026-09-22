# Holmes CTF 2026 — Borrowed Name

## Scenario

**Challenge:** Borrowed Name  
**Category:** DFIR / Active Directory / C2 Analysis  
**Scenario:** DIOGENES Active Directory Incident

The investigation revolves around a compromised Windows workstation, command-and-control activity, Active Directory abuse, privilege escalation, and lateral movement.

The supplied evidence included:

- `capture.pcapng`
- `Q3_Salary_Review.img`
- `Microsoft-Windows-NTLM_Operational.evtx`
- Scenario PDF

The goal was to reconstruct the attack chain and answer questions covering the C2 framework, beacon encryption, Active Directory abuse, credential access, privilege escalation, and lateral movement.

---

# Final Answers

| # | Question | Answer |
|---|---|---|
| 1 | C2 used | `Adaptix` |
| 2 | SessionKey:EncryptionKey | `53fc4c03c7b461befe5dcb268e3d9208:4580221ac3fe51be1797524a048e552d` |
| 3 | Privilege escalation CVE | `CVE-2026-27912` |
| 4 | Custom BOF MD5 | `583236cc3ef2488fb133385bcd75825e` |
| 5 | ObjectSID | `S-1-5-21-2253468260-689643353-167204612-1125` |
| 6 | Password attack + timestamp | `Internal_Monologue:2026-09-09 20:44:11` |
| 7 | Credentials used | `afenwick:*Seash5lls*` |
| 8 | Target user + resulting password | `jreed:Aigohng8vai0seish4zi` |
| 9 | New token logon type | `9` |
| 10 | New agent upload path | `\\192.168.56.11\ADMIN$\svc_bkup` |
| 11 | Service group | `defragsvc` |
| 12 | New BeaconID:SessionKey | `ddc68fa7:289122cf1ec91c67eb89c30642adfea4` |

---

# Investigation

## 1. Identifying the C2 Framework

The network capture showed repeated HTTP communication between the compromised workstation and:

```text
192.168.56.1:8818
```

Inspection of the malware configuration revealed values such as:

```text
192.168.56.1
8818
POST
/api/v1/status
/updates/check.php
/content.html
X-Beacon-Id
```

The binaries and network traffic also contained Adaptix-specific HTTP beacon structures such as:

```text
ConnectorHTTP
X-Beacon-Id
```

This identified the command-and-control framework as:

```text
Adaptix
```

### Answer

```text
Adaptix
```

---

# 2. Recovering the Session and Encryption Keys

The initial Adaptix beacon registration traffic contained information required to track the compromised host and decrypt subsequent tasking.

The beacon session key was recovered as:

```text
53fc4c03c7b461befe5dcb268e3d9208
```

The associated encryption key was:

```text
4580221ac3fe51be1797524a048e552d
```

The challenge required both values in the format:

```text
SessionKey:EncryptionKey
```

### Answer

```text
53fc4c03c7b461befe5dcb268e3d9208:4580221ac3fe51be1797524a048e552d
```

---

# 3. Identifying the Privilege-Escalation Vulnerability

After decrypting the C2 task stream, one of the custom BOFs produced the following identifying information:

```text
Action: ResetNightmare
CVE-2026-27912
```

The operation involved modifying Active Directory attributes before obtaining access to another user's identity.

### Answer

```text
CVE-2026-27912
```

---

# 4. Finding the Custom BOF MD5

The operator deployed a custom Beacon Object File to perform the ResetNightmare attack.

The BOF was extracted from the decrypted C2 traffic and hashed.

```bash
md5sum <bof_file>
```

Result:

```text
583236cc3ef2488fb133385bcd75825e
```

### Answer

```text
583236cc3ef2488fb133385bcd75825e
```

---

# 5. Finding the Required Active Directory Object SID

The privilege-escalation attack required the compromised account to possess write rights over a particular Active Directory property.

ACL enumeration involving the compromised account showed a writable property on an AD object.

The associated SID was:

```text
S-1-5-21-2253468260-689643353-167204612-1125
```

The relevant permission was a `WriteProperty`-style permission used during the manipulation phase of the attack.

### Answer

```text
S-1-5-21-2253468260-689643353-167204612-1125
```

---

# 6. Determining How the Password Was Obtained

This was the trickiest question in the challenge.

The decrypted Adaptix traffic showed a credential-focused BOF containing strings such as:

```text
GetNTLMCreds
NTLMv1 Response:
NTLMv2 Response:
1122334455667788
```

The fixed NTLM challenge:

```text
1122334455667788
```

combined with the local NTLM authentication behavior identified the attack as **Internal Monologue**.

The agent returned a NetNTLMv2 response belonging to:

```text
afenwick
```

The corresponding NTLM Operational event occurred at:

```text
2026-09-09 20:44:11
```

One important detail was the exact format expected by the challenge checker.

The attack name had to use an underscore:

```text
Internal_Monologue
```

rather than:

```text
Internal Monologue
Internal-Monologue
InternalMonologue
```

### Answer

```text
Internal_Monologue:2026-09-09 20:44:11
```

---

# 7. Credentials Used for the Privilege-Escalation Attack

The credentials recovered for the compromised user were:

```text
afenwick
```

with password:

```text
*Seash5lls*
```

These credentials were later supplied directly to the ResetNightmare BOF.

### Answer

```text
afenwick:*Seash5lls*
```

---

# 8. Target User and Resulting Password

During execution of the ResetNightmare BOF, another domain user was targeted.

The decrypted output identified the target as:

```text
jreed
```

The password was reset to:

```text
Aigohng8vai0seish4zi
```

This enabled the attacker to authenticate as the target account.

### Answer

```text
jreed:Aigohng8vai0seish4zi
```

---

# 9. New Token Logon Type

Following privilege escalation, the attacker generated a new Windows access token.

The C2 output explicitly showed the resulting user and logon type:

```text
DIOCORE\jreed
logon: 9
```

Windows logon type `9` corresponds to a new-credentials style logon.

### Answer

```text
9
```

---

# 10. Lateral Movement Upload Path

After obtaining the higher-privileged identity, the attacker moved laterally to another Windows system.

The target was:

```text
DC02
```

which resolved in the evidence to:

```text
192.168.56.11
```

The operator copied a new Adaptix agent to the administrative share.

The original task referenced:

```text
\\dc02\ADMIN$\svc_bkup
```

However, the challenge requested the answer using the IP-address format.

### Answer

```text
\\192.168.56.11\ADMIN$\svc_bkup
```

---

# 11. Service Used to Start the New Agent

The attacker reused an existing service to launch the uploaded payload.

The C2 output showed the service name:

```text
defragsvc
```

The operator temporarily modified the service configuration so that its executable path pointed to the uploaded agent.

The service was then started, allowing code execution on the remote system.

### Answer

```text
defragsvc
```

---

# 12. Recovering the New Beacon ID and Session Key

Once the payload executed on DC02, a new Adaptix beacon registered with the command-and-control server.

The new host registration identified:

```text
Host: DC02
User: SYSTEM
Process: svc_bkup
```

The newly generated Beacon ID was:

```text
ddc68fa7
```

The associated session key was:

```text
289122cf1ec91c67eb89c30642adfea4
```

The challenge required:

```text
BeaconID:SessionKey
```

### Answer

```text
ddc68fa7:289122cf1ec91c67eb89c30642adfea4
```

---

# Attack Chain

The complete compromise can be reconstructed as:

```text
Initial compromise
        |
        v
winupdate.exe executed
        |
        v
Adaptix beacon established
192.168.56.1:8818
        |
        v
Credential reconnaissance
        |
        v
Internal_Monologue
        |
        v
afenwick NetNTLMv2 captured
        |
        v
afenwick:*Seash5lls*
        |
        v
AD permission abuse
WriteProperty
        |
        v
ResetNightmare
CVE-2026-27912
        |
        v
Target: jreed
Password reset:
Aigohng8vai0seish4zi
        |
        v
New token created
Logon Type 9
        |
        v
Lateral movement to DC02
192.168.56.11
        |
        v
Payload copied to:
\\192.168.56.11\ADMIN$\svc_bkup
        |
        v
defragsvc modified and started
        |
        v
New SYSTEM Adaptix beacon
Beacon ID: ddc68fa7
SessionKey: 289122cf1ec91c67eb89c30642adfea4
```

---

# Indicators of Compromise

## Network

```text
192.168.56.1:8818
```

Adaptix HTTP-related paths observed:

```text
/api/v1/status
/updates/check.php
/content.html
```

Header:

```text
X-Beacon-Id
```

Remote lateral-movement target:

```text
192.168.56.11
```

---

## Users

```text
afenwick
jreed
```

---

## Processes / Payloads

```text
winupdate.exe
svc_bkup
```

---

## Service

```text
defragsvc
```

---

## Remote Path

```text
\\192.168.56.11\ADMIN$\svc_bkup
```

---

## Credential Attack

```text
Internal_Monologue
```

Fixed NTLM challenge:

```text
1122334455667788
```

---

# Key Timeline

| Timestamp | Event |
|---|---|
| `2026-09-09 20:32` | Initial Adaptix activity observed |
| `2026-09-09 20:44:11` | Internal Monologue credential attack executed |
| `2026-09-09 20:44:11` | `afenwick` NetNTLMv2 response returned |
| `2026-09-09 20:46:39` | ResetNightmare privilege-escalation BOF executed |
| Later | `jreed` password reset |
| Later | Logon type 9 token created |
| Later | Agent uploaded to DC02 |
| Later | `defragsvc` used to launch payload |
| Later | New SYSTEM Adaptix beacon established |

---

# Useful Investigation Commands

## Hashing an Extracted BOF

```bash
md5sum payload.o
```

---

## Searching Extracted Artifacts

```bash
grep -RIna "GetNTLMCreds" .
grep -RIna "ResetNightmare" .
grep -RIna "1122334455667788" .
grep -RIna "defragsvc" .
grep -RIna "svc_bkup" .
```

---

## PCAP Investigation

Useful Wireshark filters included:

```text
http
```

```text
ip.addr == 192.168.56.1
```

```text
tcp.port == 8818
```

```text
ip.addr == 192.168.56.11
```

Search packet bytes for:

```text
X-Beacon-Id
```

and correlate requests and responses with recovered beacon session material.

---

# Important Challenge Gotchas

Several answers were sensitive to exact formatting.

### C2 Name

The challenge expected:

```text
Adaptix
```

not:

```text
AdaptixC2
192.168.56.1
192.168.56.1:8818
```

### Internal Monologue

The checker required:

```text
Internal_Monologue
```

not:

```text
Internal Monologue
Internal-Monologue
InternalMonologue
```

### Lateral Movement Path

The challenge expected the target IP rather than the hostname:

```text
\\192.168.56.11\ADMIN$\svc_bkup
```

instead of:

```text
\\dc02\ADMIN$\svc_bkup
```

These formatting differences were important even when the underlying forensic conclusion was correct.

---

# Conclusion

Borrowed Name combined several areas of Windows and Active Directory incident response:

- Malware and disk-image analysis
- Adaptix C2 traffic analysis
- Beacon session decryption
- NTLM authentication investigation
- Internal Monologue credential harvesting
- Active Directory ACL abuse
- Custom BOF analysis
- ResetNightmare exploitation
- Windows token manipulation
- SMB administrative-share lateral movement
- Service-based remote execution
- Secondary C2 beacon recovery

The compromise began with an Adaptix implant running as `afenwick`, progressed through credential extraction and Active Directory abuse, and culminated in the compromise of DC02 as `SYSTEM`.

The most important investigative lesson from this challenge was to correlate all three evidence sources rather than treating them independently. The PCAP exposed the C2 tasking, the NTLM Operational log validated authentication behavior, and the disk image provided host-level context for the initial compromise and malware chain.