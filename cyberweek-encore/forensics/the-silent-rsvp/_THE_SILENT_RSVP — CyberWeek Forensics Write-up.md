# `_THE_SILENT_RSVP`

**Category:** Forensics  
**Difficulty:** Hard  
**Points:** 200  
**Flag Format:** `cyberweek{...}`

---

## Challenge Description

> An outbox log recovered from Encore Events Ltd.'s mail server contains one email that doesn't quite belong — an ordinary vendor invoice thread, dressed up to slip past a casual read.
>
> Everything you need was sent in plain sight. Not everything sent in plain sight was meant to be seen.

We were provided with:

```text
outbox_recovered.eml
```

The objective was to inspect the email and its attachments, follow the hidden data across several layers, and recover the final flag.

---

## Initial Email Analysis

The `.eml` file appeared to contain a normal vendor invoice conversation.

Important headers included:

```text
From: D. Okafor <d.okafor@encore-events.example>
To: billing@northlyne-supplies.example
Cc: m.reyes@encore-events.example
Subject: Re: Vendor Invoice #EE-2291 -- Encore flyer proof attached
```

Two unusual custom headers immediately stood out:

```text
X-Debug-Salt: 00c0ffee1337beef
X-Vault-Salt: a91fbe20c477012d
```

The email contained three attachments:

```text
encore_flyer.png
logo.jpg
vendor_invoice.pdf
```

The message itself claimed these were simply a flyer proof, company logo, and signed invoice.

That made the attachments the obvious next place to investigate.

---

# 1. Extracting the Email Attachments

The attachments can be extracted using a mail parser, Python's `email` module, or tools such as `munpack`.

For example:

```bash
mkdir extracted
munpack -C extracted outbox_recovered.eml
```

After extraction:

```text
encore_flyer.png
logo.jpg
vendor_invoice.pdf
```

---

# 2. Investigating `encore_flyer.png`

Basic metadata inspection did not immediately reveal the secret, so the image channels were examined for steganography.

The important data was hidden using the **least significant bits of the blue channel**.

Extracting the blue-channel LSB stream revealed:

```text
9f2c-storeroom###END###
```

Therefore the first key component was:

```text
9f2c-storeroom
```

The `###END###` marker indicated that the meaningful hidden message ended there.

---

## Blue-Channel LSB Concept

For every pixel, the least significant bit of the blue value can be collected:

```python
bit = blue & 1
```

The bits are then grouped into bytes and interpreted as ASCII.

The resulting plaintext was:

```text
9f2c-storeroom###END###
```

---

# 3. Investigating `vendor_invoice.pdf`

The invoice looked legitimate when opened normally.

However, PDF metadata contained an interesting value:

```text
Keywords: Rehearsal!42
```

This provided a second password component:

```text
Rehearsal!42
```

Inspecting the internal PDF structure revealed something even more important:

```text
backup.7z
```

The file had been embedded inside the invoice.

This fit the challenge description perfectly: the data was sent in plain sight, but was not intended to be noticed.

---

# 4. Extracting `backup.7z`

The embedded file was extracted from the PDF.

Tools such as `pdfdetach`, `binwalk`, or PDF object extraction can be used depending on how the attachment is embedded.

For example:

```bash
pdfdetach -list vendor_invoice.pdf
```

followed by:

```bash
pdfdetach -saveall vendor_invoice.pdf
```

This recovered:

```text
backup.7z
```

Despite its `.7z` filename, investigation showed that the archive was actually using an **AES-encrypted ZIP-style format**.

---

# 5. Recovering the Archive Password

At this point we had two suspicious strings:

From the flyer:

```text
9f2c-storeroom
```

From the PDF metadata:

```text
Rehearsal!42
```

The correct combination was:

```text
9f2c-storeroom|Rehearsal!42
```

The pipe character was used as the separator.

The final archive password was therefore:

```text
9f2c-storeroom|Rehearsal!42
```

The password was confirmed by successfully authenticating and decrypting the archive rather than relying only on a password-verification field.

---

# 6. Contents of the Archive

After successful decryption, the archive contained:

```text
readme.txt
vault.db
```

The interesting file was:

```text
vault.db
```

This was a SQLite database.

---

# 7. Inspecting `vault.db`

Opening the database normally showed apparently harmless records.

For example:

```bash
sqlite3 vault.db
```

The available rows had IDs:

```text
1
2
3
4
5
7
9
```

This was suspicious because:

```text
6
8
```

were missing.

That strongly suggested that two rows had been deleted.

Simply running SQL queries would therefore not be enough.

---

# 8. Recovering Deleted SQLite Records

SQLite does not always immediately erase deleted data from database pages.

Deleted records may remain inside:

```text
freeblocks
```

or other unused space in database pages until SQLite overwrites them.

Carving the database's unused regions recovered data belonging to the deleted rows.

Two important labels appeared:

```text
backup-export
archive-export
```

These corresponded to the missing database entries.

The deleted `archive-export` row contained a Base64-encoded encrypted blob.

This was the key piece of deleted evidence.

---

# 9. Recovering the Encryption Parameters

The email contained another important custom header:

```text
X-Vault-Salt: a91fbe20c477012d
```

This turned out to be the salt needed for the database ciphertext.

The previously recovered archive password was reused:

```text
9f2c-storeroom|Rehearsal!42
```

The cryptographic parameters were:

```text
KDF      : PBKDF2-HMAC-SHA256
Iterations: 100000
Key Size : 256 bits

Cipher   : AES-256-CBC
IV       : First 16 bytes of the Base64-decoded ciphertext
Salt     : a91fbe20c477012d
```

The key derivation process was therefore conceptually:

```python
key = PBKDF2_HMAC_SHA256(
    password=b"9f2c-storeroom|Rehearsal!42",
    salt=bytes.fromhex("a91fbe20c477012d"),
    iterations=100000,
    length=32
)
```

The first 16 decoded bytes were then used as the AES IV:

```python
iv = ciphertext[:16]
encrypted_data = ciphertext[16:]
```

After decrypting with AES-256-CBC and removing padding, the plaintext contained the flag.

---

# 10. Final Flag

```text
cyberweek{st3g0_pdf_4nd_th3_d3l3t3d_r0w}
```

---

# Attack / Investigation Chain

The complete solve path was:

```text
outbox_recovered.eml
        |
        +--> X-Vault-Salt
        |      |
        |      +--> a91fbe20c477012d
        |
        +--> encore_flyer.png
        |      |
        |      +--> Blue-channel LSB
        |             |
        |             +--> 9f2c-storeroom
        |
        +--> vendor_invoice.pdf
               |
               +--> PDF metadata
               |      |
               |      +--> Rehearsal!42
               |
               +--> Embedded backup.7z
                       |
                       +--> Password:
                       |    9f2c-storeroom|Rehearsal!42
                       |
                       +--> vault.db
                              |
                              +--> Deleted SQLite rows
                                     |
                                     +--> archive-export
                                            |
                                            +--> Base64 ciphertext
                                                   |
                                                   +--> PBKDF2-SHA256
                                                   +--> AES-256-CBC
                                                          |
                                                          +--> FLAG
```

---

# Key Takeaways

This challenge combined several forensic techniques rather than relying on one obvious trick:

- MIME email analysis
- Suspicious/custom email-header inspection
- Image LSB steganography
- PDF metadata inspection
- Embedded PDF file extraction
- Archive format/password analysis
- SQLite deleted-record recovery
- Freeblock carving
- Base64 decoding
- PBKDF2 key derivation
- AES-CBC decryption

The main lesson was that the visible email content was deliberately mundane. Important evidence existed across several different parts of the message, and information recovered early in the investigation was reused later.

In particular:

```text
9f2c-storeroom
```

and:

```text
Rehearsal!42
```

first unlocked the embedded archive and then became relevant again during the final database decryption stage.

---

## Flag

```text
cyberweek{st3g0_pdf_4nd_th3_d3l3t3d_r0w}
```