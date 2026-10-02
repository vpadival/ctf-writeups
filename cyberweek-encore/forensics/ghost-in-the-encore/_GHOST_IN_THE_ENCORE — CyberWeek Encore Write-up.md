# _GHOST_IN_THE_ENCORE

**Category:** Forensics  
**Difficulty:** Hard  
**Points:** 500  
**Flag Format:** `cyberweek{...}`

---

## Challenge Description

> During CyberWeek Encore, an insider at Encore Events Ltd. leaked a confidential message.
>
> The SOC couldn't seize the suspect's machine. All they captured was the network traffic from the workstation.
>
> Recover what was stolen. Nothing here is what it first appears to be, and deleting something is not the same as destroying it.
>
> **Tip:** keep notes. Something you find early will matter again at the very end.

The challenge provides a network capture:

```text
encore_capture.pcapng
```

The goal is to reconstruct the attack chain from network traffic, recover deleted data, and eventually identify the leaked message.

---

# Investigation

## 1. Inspecting the Network Capture

The first step was to inspect the traffic and identify transferred files and unusual communications.

One interesting HTTP transfer contained an apparently ordinary image:

```text
brand_kit.png
```

At first glance it was a valid PNG, but its size was suspicious.

Checking the PNG structure showed that the legitimate image terminated at the normal PNG `IEND` chunk, while a large amount of data remained afterward.

Approximately **207 KB of additional data** had been appended to the PNG.

This indicated that the image was being used as a **polyglot/container**.

---

## 2. Inspecting the PNG Metadata

Before extracting the appended content, the PNG metadata revealed an important value:

```text
RC4Key = encore-k3y-26
```

At this point its purpose was unknown, so it was saved for later.

This turned out to be exactly what the challenge hint meant:

> Something you find early will matter again at the very end.

---

## 3. Extracting the Hidden ZIP

Everything after the PNG's `IEND` marker was carved into a separate file.

The appended data was identified as an encrypted ZIP archive.

Inside the archive was:

```text
usb.img
```

However, the ZIP was protected with AES encryption and required a password.

---

## 4. Recovering the ZIP Password from DNS

Returning to the network capture revealed a series of suspicious DNS requests.

Several queries used the domain:

```text
upd.encore-cdn.net
```

The subdomains contained indexed fragments.

The relevant fragments were:

```text
00-7f3a
01-91c0
02-4be2
03-d85a
04-16f9
05-c3d7
```

Sorting them numerically and joining the encoded portions resulted in:

```text
7f3a91c04be2d85a16f9c3d7
```

This was the password for the encrypted archive.

### ZIP Password

```text
7f3a91c04be2d85a16f9c3d7
```

Using it successfully decrypted the archive and extracted:

```text
usb.img
```

---

# USB Image Analysis

## 5. Identifying the Filesystem

The extracted disk image was approximately:

```text
128 MiB
```

It contained a FAT32 filesystem with the volume label:

```text
ENCORE
```

This immediately made the challenge description particularly relevant:

> deleting something is not the same as destroying it.

FAT filesystems often leave the contents of deleted files intact until their clusters are overwritten.

---

## 6. Recovering a Deleted DOCX

Analysis of the FAT32 directory entries revealed a deleted file corresponding to:

```text
meeting_notes.docx
```

Although the directory entry had been marked as deleted, its cluster chain had not yet been overwritten.

The file occupied approximately:

```text
Clusters 32–105
```

Carving those clusters reconstructed a valid DOCX file.

Recovered file:

```text
meeting_notes_deleted.docx
```

---

# DOCX Analysis

## 7. Inspecting the DOCX Internals

A `.docx` file is internally a ZIP archive containing XML documents.

After unpacking the recovered DOCX, the document properties were inspected.

A custom document property contained:

```text
BackupPhrase = Sp0tl1ght-Enc0re-Ghost!26
```

### Recovered Backup Phrase

```text
Sp0tl1ght-Enc0re-Ghost!26
```

This clearly appeared to be another decryption key.

---

# VAULT.BIN

## 8. Decrypting the Vault

Another artifact from the recovered filesystem was:

```text
VAULT.BIN
```

Using the recovered backup phrase, the vault could be decrypted.

The encryption scheme was based on:

```text
PBKDF2
AES-256-CBC
```

with the passphrase:

```text
Sp0tl1ght-Enc0re-Ghost!26
```

The decrypted output was identified as a SQLite database.

---

# SQLite Investigation

## 9. Examining the Message Database

Opening the recovered SQLite database revealed internal chat/message data.

The visible conversation contained references indicating that sensitive information had been sent accidentally.

One particularly suspicious point was a missing message immediately before a later message equivalent to:

```text
delete that, wrong channel
```

The missing entry corresponded to:

```text
message ID 18
```

This strongly suggested that the leaked content had been deleted from the database.

---

## 10. Recovering Deleted SQLite Content

Deleting a SQLite row does not necessarily immediately erase its bytes.

The database's free blocks and unallocated page space were therefore inspected.

One deleted string recovered from SQLite was:

```text
cyberweek{n0t_th3_r34l_0n3}
```

This looked like a flag.

However, it was deliberately misleading.

### Fake Flag

```text
cyberweek{n0t_th3_r34l_0n3}
```

Further analysis of the database's unallocated data revealed another deleted record:

```text
encore-export|WVLDVHB6GKAJINLOD2WRVFP2LA2XFH4FEQGLW4AA3SCWVEKDLH6CXQ37S4CZBT2YIRAWFEI5|eof
```

The structure suggested:

```text
encore-export | encoded data | eof
```

The middle portion was therefore extracted:

```text
WVLDVHB6GKAJINLOD2WRVFP2LA2XFH4FEQGLW4AA3SCWVEKDLH6CXQ37S4CZBT2YIRAWFEI5
```

---

# Final Decoding Stage

## 11. Base32 Decoding

The alphabet used by the encoded data matched Base32.

Decoding it produced a binary ciphertext.

At this point, the challenge hint became relevant again.

Earlier, the metadata of `brand_kit.png` had contained:

```text
RC4Key = encore-k3y-26
```

The recovered export therefore appeared to be encrypted with RC4.

---

## 12. RC4 Decryption

The Base32-decoded ciphertext was decrypted using:

```text
Key: encore-k3y-26
Cipher: RC4
```

The plaintext revealed the real flag:

```text
cyberweek{d3l3t3d_but_n3v3r_f0rg0773n_3nc0r3}
```

---

# Flag

```text
cyberweek{d3l3t3d_but_n3v3r_f0rg0773n_3nc0r3}
```

---

# Attack / Evidence Chain

The complete forensic chain was:

```text
encore_capture.pcapng
        |
        v
HTTP transfer
        |
        v
brand_kit.png
        |
        +--> PNG metadata
        |       |
        |       +--> RC4Key = encore-k3y-26
        |
        +--> Data appended after IEND
                |
                v
          AES-encrypted ZIP
                |
                | Password recovered through DNS:
                | 7f3a91c04be2d85a16f9c3d7
                v
             usb.img
                |
                v
        FAT32 deleted entries
                |
                +--> meeting_notes.docx
                |       |
                |       v
                | BackupPhrase =
                | Sp0tl1ght-Enc0re-Ghost!26
                |
                +--> VAULT.BIN
                        |
                        v
                 AES-256-CBC
                        |
                        v
                 SQLite database
                        |
                        v
              Deleted/free-space records
                        |
                        +--> Fake flag
                        |
                        +--> Base32 export
                                |
                                v
                          Base32 decode
                                |
                                v
                              RC4
                       key = encore-k3y-26
                                |
                                v
                            REAL FLAG
```

---

# Key Findings

| Stage | Finding |
|---|---|
| Network traffic | Suspicious HTTP file transfer |
| PNG | Additional content appended after `IEND` |
| PNG metadata | `RC4Key = encore-k3y-26` |
| DNS | ZIP password split into indexed DNS labels |
| ZIP password | `7f3a91c04be2d85a16f9c3d7` |
| ZIP | Contained `usb.img` |
| Disk image | FAT32 volume named `ENCORE` |
| Deleted FAT file | `meeting_notes.docx` |
| DOCX property | `Sp0tl1ght-Enc0re-Ghost!26` |
| Vault | AES-256-CBC encrypted SQLite database |
| SQLite deleted data | Fake flag + encrypted export |
| Export encoding | Base32 |
| Final cipher | RC4 |
| RC4 key | `encore-k3y-26` |
| Final flag | `cyberweek{d3l3t3d_but_n3v3r_f0rg0773n_3nc0r3}` |

---

# What Made the Challenge Interesting

The challenge used several different forensic concepts in a single chain:

- Network traffic reconstruction
- File carving
- PNG polyglots
- Metadata analysis
- DNS-based data transfer
- AES-encrypted archives
- FAT32 deleted-file recovery
- DOCX/XML metadata extraction
- Password-based cryptography
- SQLite database forensics
- Recovery of deleted SQLite records
- Base32 encoding
- RC4 decryption

The main theme of the challenge was persistence of supposedly deleted information.

A file deleted from FAT32 was still recoverable, and a deleted SQLite message also remained accessible in unused database space.

The challenge hint was therefore literal:

> **Deleting something is not the same as destroying it.**

The second hint also tied the entire investigation together: the RC4 key recovered from the very first PNG became necessary only at the final stage.

---

## Final Flag

```text
cyberweek{d3l3t3d_but_n3v3r_f0rg0773n_3nc0r3}
```