# Hacker Holidays 2026 — Byte Lotus Hotel: "Management Wants a Word"

**Category:** Forensics
**Difficulty:** Hard
**Points:** 120
**Platform:** TryHackMe

## Challenge Brief

> Housekeeping found a guest's laptop left behind after an early checkout, Room 214, registered to a "Vera." IT pulled a full triage before wiping it for the next guest.
>
> Hunt down the artifacts scattered across her machine and figure out how they fit together. Somewhere in that trail is a password she never meant to leave behind. Follow it, and it'll open a door to something she was keeping very quiet.

The provided task file was a KAPE triage collection (`KAPE/C/Users/vera/...`, `KAPE/C/Windows/System32/config/...`) pulled from Vera's Windows machine — registry hives, browser profile, and user files.

## Recon

Unzipping the task archive gave a full KAPE-style collection: SAM/SYSTEM/SECURITY hives, Vera's `AppData` (Chrome profile, DPAPI `Protect` folder), and a `Documents\backup` file:

```
KAPE/C/Windows/System32/config/{SAM,SYSTEM,SECURITY}
KAPE/C/Users/vera/AppData/Roaming/Microsoft/Protect/S-1-5-21-.../{Preferred, <mkguid>}
KAPE/C/Users/vera/AppData/Local/Google/Chrome For Testing/User Data/Local State
KAPE/C/Users/vera/AppData/Local/Google/Chrome For Testing/User Data/Default/Login Data
KAPE/C/Users/vera/Documents/backup      # 104,857,600 bytes, pure high-entropy data
```

The `backup` file was exactly 100 MiB of high-entropy data with no recognizable file signature — a strong signal it's an encrypted container of some kind, most likely a VeraCrypt volume.

The clue chain was clear: **crack the local account password → use it to decrypt DPAPI secrets → recover a saved browser credential → use that credential as the container passphrase.**

## Step 1 — Recovering Vera's Windows Password

Dumped local account hashes straight from the SAM/SYSTEM hives with `pypykatz`:

```bash
pypykatz registry --sam SAM SYSTEM
```

```
vera:1000:aad3b435b51404eeaad3b435b51404ee:1241186a4aac4f34f4bf7ace71b396a8:::
```

Cracked the NTLM hash offline against `rockyou.txt` using a small multiprocessing MD4 cracker (pycryptodome's `MD4` since Python's `hashlib` doesn't ship it):

```python
from Crypto.Hash import MD4
def ntlm(pw):
    h = MD4.new(); h.update(pw.encode('utf-16le')); return h.digest()
```

```
FOUND: minivera
```

**Vera's Windows password: `minivera`**

## Step 2 — Decrypting the DPAPI Masterkey

Windows protects saved browser credentials via DPAPI, and each user's masterkey blob (under `AppData\Roaming\Microsoft\Protect\<SID>\`) is itself encrypted with a key derived from the user's logon password. With the password from Step 1, `dpapick3` unlocks it directly:

```python
from dpapick3 import masterkey

sid = "S-1-5-21-2529683458-431225740-1723070931-1000"
pool = masterkey.MasterKeyPool()
pool.loadDirectory(f"AppData/Roaming/Microsoft/Protect/{sid}")
pool.try_credential(sid, "minivera")   # -> decrypts the masterkey
```

## Step 3 — Recovering the Saved Chrome Credential

Chrome (even "Chrome for Testing") stores its AES encryption key in `Local State`, itself wrapped in a DPAPI blob (`os_crypt.encrypted_key`, `DPAPI` prefix + blob). Decrypted it with the masterkey from Step 2:

```python
import json, base64
from dpapick3 import blob

raw = base64.b64decode(local_state["os_crypt"]["encrypted_key"])[5:]  # strip 'DPAPI' prefix
b = blob.DPAPIBlob(raw)
b.decrypt(mk.get_key())
chrome_aes_key = b.cleartext[:32]   # 32-byte AES-256 key
```

With that key, decrypted the saved password row in `Login Data` (SQLite), which uses Chrome's `v10` format — `AES-256-GCM` with a 12-byte nonce and 16-byte tag appended:

```python
from Crypto.Cipher import AES

blob = row["password_value"]
nonce, ct, tag = blob[3:15], blob[15:-16], blob[-16:]
cipher = AES.new(chrome_aes_key, AES.MODE_GCM, nonce=nonce)
pt = cipher.decrypt_and_verify(ct, tag)
```

```
origin:   http://bytelotus.thm:8080/
user:     VeraSecretVault
password: Wh4t1sV3raD0inG0nTh1sH0st
```

That password — clearly never meant to double as anything but a site login — turned out to be exactly what the challenge brief was pointing at: *"a password she never meant to leave behind."*

## Step 4 — Identifying and Opening the VeraCrypt Container

`Documents\backup` (100 MiB, no header signature) was the "door" the recovered password was meant to open. `cryptsetup --type tcrypt --veracrypt` couldn't be used directly in the sandbox (`Required kernel crypto interface not available` — no `algif_skcipher` / kernel module access), so the VeraCrypt volume header format was implemented by hand.

**VeraCrypt volume header layout (first 512 bytes):**

| Offset | Size | Field |
|---|---|---|
| 0 | 64 | Salt (plaintext) |
| 64 | 448 | Encrypted header (AES-XTS) |

Decrypted header fields (relative to the 448-byte decrypted buffer):

| Offset | Field |
|---|---|
| 0–3 | `VERA` signature |
| 8–11 | CRC32 of keypool (256–511) |
| 44–51 | Master key scope offset |
| 52–59 | Encrypted area length |
| 64–67 | Sector size |
| 192–447 | Master keypool (256 bytes: AES key1 \|\| key2) |

The header key is derived via PBKDF2 over the recovered password + volume salt. VeraCrypt's default PRF/iteration combos were brute-forced (SHA-512/500000, SHA-256/500000, legacy RIPEMD-160 counts, etc.):

```python
import hashlib
key = hashlib.pbkdf2_hmac('sha512', password, salt, 500000, 64)
key1, key2 = key[:32], key[32:]
```

AES-XTS isn't available in this build of pycryptodome (`AES.MODE_XTS` missing), so XTS was implemented manually per IEEE P1619 — AES-ECB on both the tweak and data keys, GF(2¹²⁸) "multiply-by-2" tweak stepping between blocks:

```python
def gf_double(t):
    t <<= 1
    if t >> 128:
        t ^= (1 << 128); t ^= 0x87
    return t & ((1 << 128) - 1)
```

Decrypting the 448-byte header with `sha512` @ 500,000 iterations produced a valid `VERA` signature with a matching CRC32 — confirming the password and KDF parameters:

```
sha512 500000 sig= b'VERA'
MATCH!!! sha512 500000
CRC match: True
```

## Step 5 — Walking the Filesystem Inside the Volume

The decrypted master keypool gave the AES-256-XTS key pair used to decrypt the actual volume data (not just the header). Decrypting the start of the data area revealed a **FAT32** filesystem (`MSDOS5.0` OEM string, `VERA` boot sector jump):

```
bytes/sector: 512   sectors/cluster: 2   reserved: 36
numFATs: 2           FATsz32: 798        rootCluster: 2
```

Decrypted the FAT table and root directory, reassembling long filenames from their UTF-16LE LFN fragments:

```
$RECYCLE.BIN
SECRET~1   -> "secret_financial_documents"   (dir, cluster 3)
SYSTEM~1   -> "System Volume Information"    (dir, cluster 33)
```

Inside `secret_financial_documents/`:

```
IMPORT~1.PDF -> "important_invoice_byte_lotus.pdf"   (26,747 bytes, cluster chain 6-32)
TRANSA~1.CSV -> "transactions_q3.csv"                (427 bytes, cluster 35)
```

Followed both files' cluster chains through the decrypted FAT table and reconstructed them from the decrypted cluster data.

## Step 6 — The Decoy and the Payload

`transactions_q3.csv` contained a set of plausible-looking hotel transactions — except for one line that stood out:

```
2026-07-12,TXN-10531,Internal Adjustment,Image asset correction,0.00,Archived
```

An "image asset correction" with a $0 amount, filed as *Archived* — a pointer straight at the PDF's embedded image. Pulling the embedded image out of `important_invoice_byte_lotus.pdf` with `pypdf`:

```python
from pypdf import PdfReader
page = PdfReader("important_invoice_byte_lotus.pdf").pages[0]
img = page.images[0]
open("invoice_image.png", "wb").write(img.data)
```

...revealed an invoice image with the flag sitting in plain sight as a line item:

```
NO.  DESCRIPTION                                    QTY   PRICE   TOTAL
1.   Flag: THM{1t_w4s_V3r4_A11_Al0ng?!}               1    $100    $100
```

## Flag

```
THM{1t_w4s_V3r4_A11_Al0ng?!}
```

Fitting payoff for the room's whole premise — "it was Vera all along."

## Chain Summary

```
SAM hash (pypykatz)
   │  crack (rockyou / NTLM-MD4)
   ▼
Windows password: minivera
   │  unlock DPAPI masterkey (dpapick3)
   ▼
DPAPI masterkey
   │  decrypt os_crypt key (Local State)
   ▼
Chrome AES-256 key
   │  decrypt Login Data (AES-GCM, v10)
   ▼
Saved credential: Wh4t1sV3raD0inG0nTh1sH0st
   │  derive VeraCrypt header key (PBKDF2-HMAC-SHA512, 500k iters)
   ▼
VeraCrypt volume header decrypted (manual AES-XTS)
   │  decrypt volume data with master keypool
   ▼
FAT32 filesystem → secret_financial_documents/
   │  transactions_q3.csv decoy points at the PDF
   ▼
important_invoice_byte_lotus.pdf → embedded PNG
   │
   ▼
THM{1t_w4s_V3r4_A11_Al0ng?!}
```

## Tools Used

- `pypykatz` — SAM/SYSTEM hive parsing, NTLM hash extraction
- Custom multiprocessing NTLM cracker (`pycryptodome` MD4) against `rockyou.txt`
- `dpapick3` — DPAPI masterkey and blob decryption
- `pycryptodome` (AES-GCM, AES-ECB) — Chrome credential decryption, hand-rolled AES-XTS
- Manual VeraCrypt volume header parser (PBKDF2-HMAC-SHA512, IEEE P1619 XTS)
- Manual FAT32 parser (boot sector, FAT table, long-filename reassembly)
- `pypdf` — embedded image extraction from PDF

## Key Takeaway

Every "layer" of this challenge was a real-world credential reuse and forensic-artifact chain rather than a single exploit: a cracked local password unlocked DPAPI, DPAPI unlocked a browser-saved credential, and that credential turned out to double as a full-disk-encryption passphrase. The hardest part wasn't any single crypto primitive — it was that the sandbox had no kernel crypto interface available, so the entire VeraCrypt XTS decryption and FAT32 filesystem walk had to be reimplemented from spec in pure Python rather than delegated to `cryptsetup`.
