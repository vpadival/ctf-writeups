# Paper Ghost — DFIR Write-up

## Challenge Information

**Scenario:** Paper Ghost  
**Category:** Digital Forensics / DFIR  
**Event:** Sherlock / Holmes CTF 2026

The investigation focuses on the compromise of **Clara Voss's workstation** after a malicious USB device was planted at her desk.

The attacker, operating under the VON BORK operation, delivered a fake update package through the USB. Once executed, the payload gained access to the victim's microphone and webcam and exfiltrated information to a command-and-control server.

The supplied forensic collection contained several useful Windows artifacts, including:

- SYSTEM Registry hive
- SOFTWARE Registry hive
- `NTUSER.DAT`
- `UsrClass.dat`
- Windows Search database (`Windows.edb`)
- Windows Search transaction files
- Jump Lists
- LNK files
- RecentDocs artifacts
- SRUM database

---

# Questions and Answers

| # | Question | Answer |
|---|---|---|
| 1 | When did Clara Voss first connect the planted USB? | `2026-08-19 15:35:50` |
| 2 | What serial number did the USB leave behind? | `RS200000000627E4&0` |
| 3 | What is the full path of the malicious payload? | `E:\CO-LT-0469 update package\update.exe` |
| 4 | When did Voss execute the malicious package? | `2026-08-19 15:36:25` |
| 5 | What asset/device name was assigned to the USB? | `CO-USB-0091` |
| 6 | When did microphone capture begin? | `2026-08-19 15:38:08` |
| 7 | How long did the webcam stream? | `127` seconds |
| 8 | How many decimal MB were sent to the C2? | `172.064531` |
| 9 | What developer credentials were exposed? | `tainsworth:D10g3n3s_T1ck3ts#2026` |

---

# Investigation

## 1. Identifying the First USB Connection

The first objective was determining when Clara Voss connected the USB device planted by Elias Venn.

USB connection information can commonly be recovered from the Windows Registry, particularly from keys associated with USB storage devices and portable devices.

The relevant registry artifacts showed the Lexar flash drive appearing on the system at:

```text
2026-08-19 15:35:50
```

This represents the earliest evidence of the malicious USB being connected to Voss's workstation.

### Answer

```text
2026-08-19 15:35:50
```

---

## 2. Recovering the USB Serial Number

The SYSTEM hive contained an entry for a Lexar USB storage device.

The device instance appeared similar to:

```text
USBSTOR\Disk&Ven_Lexar&Prod_USB_Flash_Drive&Rev_2.00\RS200000000627E4&0
```

Initially, the underlying manufacturer serial appeared to be:

```text
RS200000000627E4
```

However, the challenge expected the complete device-instance serial value as recorded by Windows:

```text
RS200000000627E4&0
```

### Answer

```text
RS200000000627E4&0
```

---

## 3. Locating the Malicious Payload

Several execution and file-reference artifacts pointed toward a fake update package stored on the USB drive.

The package directory was:

```text
E:\CO-LT-0469 update package\
```

Inside it was the executable used by the attacker:

```text
update.exe
```

Therefore, the complete payload path was:

```text
E:\CO-LT-0469 update package\update.exe
```

### Answer

```text
E:\CO-LT-0469 update package\update.exe
```

---

## 4. Determining When the Malware Was Executed

Execution artifacts associated with `update.exe` were then examined.

Windows user-execution artifacts showed that Clara launched the program shortly after inserting the USB.

The malicious update was executed at:

```text
2026-08-19 15:36:25
```

The timeline therefore looked like:

```text
15:35:50  USB connected
15:36:25  update.exe executed
```

Only **35 seconds** separated insertion of the USB from execution of the malicious package.

### Answer

```text
2026-08-19 15:36:25
```

---

## 5. Recovering the USB Asset Name

The challenge mentioned that DIOGENES had assigned an internal asset name to the USB.

Device-related registry artifacts revealed the corresponding identifier:

```text
CO-USB-0091
```

This was associated with the malicious removable device when it was connected.

### Answer

```text
CO-USB-0091
```

---

# Spyware Activity

Once `update.exe` executed, Windows privacy/capability artifacts became especially important.

Windows maintains application access information for sensitive devices such as:

- Microphones
- Cameras
- Location services
- Other privacy-protected resources

The relevant records linked the suspicious activity directly to the malicious executable.

---

## 6. Microphone Capture Start Time

Microphone-access records showed that:

```text
E:\CO-LT-0469 update package\update.exe
```

accessed the microphone shortly after execution.

The microphone session began at:

```text
2026-08-19 15:38:08
```

This occurred roughly two minutes after initial execution.

### Timeline

```text
15:35:50  USB connected
15:36:25  Malware executed
15:38:08  Microphone activated
```

### Answer

```text
2026-08-19 15:38:08
```

---

## 7. Calculating the Webcam Streaming Duration

Camera-access artifacts showed a webcam session associated with the malware.

The timestamps were approximately:

```text
Start: 2026-08-19 15:42:28.681432
End:   2026-08-19 15:44:35.661982
```

Calculating the difference:

```text
15:44:35.661982
-
15:42:28.681432
----------------
126.98055 seconds
```

Rounded to the integer format requested by the challenge:

```text
127 seconds
```

### Answer

```text
127
```

---

# Network Exfiltration

## 8. Calculating Outbound C2 Traffic

The Windows **System Resource Usage Monitor (SRUM)** database was used to investigate application network activity.

SRUM records per-application network usage and can provide values such as:

```text
BytesSent
BytesReceived
```

The suspicious `update.exe` process had transmitted:

```text
172,064,531 bytes
```

The challenge specifically requested **decimal megabytes**, meaning:

```text
1 MB = 1,000,000 bytes
```

Therefore:

```text
172,064,531 / 1,000,000
= 172.064531 MB
```

### Answer

```text
172.064531
```

---

# Recovering the Leaked Developer Credentials

## 9. Identifying the DIOGENES Developer

This was the most interesting part of the investigation because the document containing the credentials was no longer directly available.

Initial artifacts showed that Clara had accessed files related to DIOGENES contractors.

One important filename was:

```text
DIOGENES_Contractor_Assignments.csv
```

Although the original CSV was no longer present, its metadata survived inside the Windows Search database.

The recovered indexed information identified:

```text
Name: Tom Ainsworth
Identifier: EXT-0419
Role: Software Developer
Assignment: DIOGENES Ticketing Support
Repository: parse_diogenese_tickets
```

This gave us the identity required to pivot toward another document:

```text
EXT-0419.pdf
```

---

## Windows Search Recovery

The supplied forensic collection included:

```text
Windows.edb
```

This is an ESE database used by Windows Search.

Even when the original file has been deleted, Windows Search may retain:

- File metadata
- Indexed text
- Search summaries
- Property values
- Cached fragments

The relevant document appeared in Windows Search as approximately:

```text
WorkID 89
EXT-0419.pdf
```

The standard file metadata did not directly expose the credentials.

However, the record contained a:

```text
System.Search.AutoSummary
```

value.

The AutoSummary content was stored using Windows Search's long-value structures and compressed data.

After resolving the corresponding long-value record and decompressing the cached data using XPRESS, text from the deleted `EXT-0419.pdf` could be recovered.

The resulting content included:

```text
Name: Tom Ainsworth
Title: Software Developer, DIOGENES Ticketing Support

Username: tainsworth
Password: D10g3n3s_T1ck3ts#2026
```

Therefore, the credentials exposed by VON BORK's surveillance were:

```text
tainsworth:D10g3n3s_T1ck3ts#2026
```

### Answer

```text
tainsworth:D10g3n3s_T1ck3ts#2026
```

---

# Attack Timeline

The recovered artifacts allow the attack to be reconstructed chronologically:

```text
2026-08-19 15:35:50
│
├── Malicious Lexar USB connected
│   ├── Serial: RS200000000627E4&0
│   └── Asset name: CO-USB-0091
│
2026-08-19 15:36:25
│
├── Clara executes:
│   E:\CO-LT-0469 update package\update.exe
│
2026-08-19 15:38:08
│
├── Malware accesses microphone
│
2026-08-19 15:42:28
│
├── Webcam surveillance begins
│
2026-08-19 15:44:35
│
├── Webcam surveillance ends
│   └── Duration: ~127 seconds
│
├── Malware communicates with C2
│   └── Outbound: 172.064531 MB
│
└── Sensitive DIOGENES contractor information exposed
    └── Tom Ainsworth
        └── tainsworth:D10g3n3s_T1ck3ts#2026
```

---

# Key Forensic Artifacts

The challenge demonstrates how several Windows artifacts can be correlated to reconstruct an intrusion.

### Registry

Useful for recovering:

```text
USB connection history
USB serial numbers
Device identifiers
User activity
Application capability access
```

### UserAssist / Execution Artifacts

Helped establish when:

```text
update.exe
```

was launched.

### CapabilityAccessManager

Provided evidence of access to privacy-sensitive hardware such as:

```text
Microphone
Webcam
```

This allowed the surveillance timeline to be reconstructed.

### SRUM

Used to determine network activity associated with the malicious executable.

Recovered outbound traffic:

```text
172,064,531 bytes
```

### Windows Search — Windows.edb

One of the most valuable artifacts in this challenge.

Even though the original contractor documents had been removed, indexed remnants remained inside Windows Search.

This allowed recovery of information from:

```text
DIOGENES_Contractor_Assignments.csv
EXT-0419.pdf
```

Eventually revealing the compromised developer credentials.

---

# Final Answers

```text
1. 2026-08-19 15:35:50

2. RS200000000627E4&0

3. E:\CO-LT-0469 update package\update.exe

4. 2026-08-19 15:36:25

5. CO-USB-0091

6. 2026-08-19 15:38:08

7. 127

8. 172.064531

9. tainsworth:D10g3n3s_T1ck3ts#2026
```

---

# Conclusion

Paper Ghost was a good example of why deleted files do not necessarily mean deleted evidence.

The attack could be reconstructed by correlating multiple independent Windows forensic sources:

```text
USB Registry artifacts
        ↓
Execution artifacts
        ↓
CapabilityAccessManager
        ↓
SRUM
        ↓
Windows Search / Windows.edb
```

The most interesting portion was recovering the final credentials. The original contractor documents were absent from the triage package, but Windows Search retained enough indexed information to identify the target contractor and ultimately reconstruct cached content from `EXT-0419.pdf`.

That led to the final exposed credential:

```text
tainsworth:D10g3n3s_T1ck3ts#2026
```

The challenge highlights how valuable **Windows Search, SRUM, Registry artifacts, and application capability records** can be when reconstructing activity from an otherwise incomplete forensic collection.