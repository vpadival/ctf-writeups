# _SIGNAL_FROM_THE_MOTHER_SHIP

**Category:** Forensics  
**Difficulty:** Medium  
**Points:** 200  

---

## Challenge Description

> McNair, McNair & Associates weren't the only ones watching Peter Parker that night. Someone else intercepted a transmission and buried it inside this very comic before it ever reached print. The Bugle never printed a retraction — because nobody at the Bugle ever found it.
>
> Everything you need is inside this one PDF file. Nothing external is required except your own tools and patience. There is more than one thing that looks like an answer. Only one of them is real.

We are provided with a single PDF:

```text
spiderman_ctf_challenge.pdf
```

The challenge strongly suggests that the PDF contains multiple hidden artifacts and that at least one apparent flag is fake.

---

# Investigation

## 1. Initial PDF Inspection

The first step was to inspect the document normally and look at its text, metadata, and embedded objects.

During extraction, a suspicious flag-like string immediately appeared:

```text
hks{not_the_real_flag_keep_looking}
```

The message itself tells us that this is only a decoy.

So instead of submitting it, we continued investigating the structure of the PDF.

Useful commands for inspecting the file include:

```bash
pdfinfo spiderman_ctf_challenge.pdf
```

and:

```bash
exiftool spiderman_ctf_challenge.pdf
```

The PDF metadata contained something unusual in the **Keywords** field.

---

## 2. Inspecting the Metadata

The `Keywords` metadata was not ordinary descriptive text.

It was Base64-encoded.

Extracting the field can be done with:

```bash
exiftool -Keywords spiderman_ctf_challenge.pdf
```

After Base64-decoding the metadata, we obtained a hint directing us toward an **embedded attachment**.

The decoded instructions indicated that we should:

1. Find the attachment inside the PDF.
2. Examine its lowest bits.
3. Treat the first four recovered bytes as the payload length.
4. Extract the following payload.
5. XOR the result using the villain's name.

This was the main roadmap for the challenge.

---

## 3. Finding the Embedded Attachment

PDF files can contain arbitrary embedded attachments, so we checked the document for them.

Using `pdfdetach`:

```bash
pdfdetach -list spiderman_ctf_challenge.pdf
```

revealed an embedded file:

```text
signal.png
```

We extracted it using:

```bash
pdfdetach -save signal.png spiderman_ctf_challenge.pdf
```

Now the challenge had shifted from PDF forensics to image steganography.

---

# 4. Analyzing `signal.png`

The metadata hint specifically referred to the **lowest bits**, suggesting an LSB steganography technique.

Testing the RGB channels showed that useful data was stored in the:

```text
Red channel
```

The bits needed to be read:

```text
MSB-first
```

from the sequence of recovered LSBs.

Conceptually, for each pixel:

```python
bit = red_value & 1
```

These bits are concatenated into bytes.

---

## 5. Recovering the Hidden Length

The first four decoded bytes were:

```text
00 00 00 24
```

Interpreting this as a big-endian 32-bit integer:

```text
0x00000024 = 36
```

Therefore, the next:

```text
36 bytes
```

contained the actual hidden payload.

---

# 6. Extracting the Payload

Reading the following 36 bytes produced:

```text
PDIjPjwqNCwnKiQkM3cyNCVvKTc3MHchKQ==
```

The trailing `==` strongly suggested another Base64 layer.

Decoding it:

```bash
echo 'PDIjPjwqNCwnKiQkM3cyNCVvKTc3MHchKQ==' | base64 -d
```

gave:

```text
<2#><*4,'*$$3w24%o)770w!)
```

This still wasn't the flag.

The metadata hint told us that one final XOR operation was required.

---

# 7. Determining the XOR Key

The hint referred to using the **villain's name**.

The villain appearing in the comic is:

```text
TYPEFACE
```

Therefore, the repeating XOR key is:

```text
TYPEFACE
```

The ciphertext:

```text
<2#><*4,'*$$3w24%o)770w!)
```

was XORed against the repeating key:

```text
TYPEFACETYPEFACETYPEFACETYPEFACE...
```

---

## 8. XOR Decryption

A simple Python script can perform the operation:

```python
ciphertext = b"<2#><*4,'*$$3w24%o)770w!)"
key = b"TYPEFACE"

plaintext = bytes(
    byte ^ key[i % len(key)]
    for i, byte in enumerate(ciphertext)
)

print(plaintext.decode())
```

Output:

```text
hks{zkwisstau6qqq6yrqq4d}
```

---

# Full Extraction Script

The important steganography stage can also be automated directly from the extracted PNG.

```python
from PIL import Image
import base64

img = Image.open("signal.png").convert("RGB")

bits = []

for pixel in img.getdata():
    r, g, b = pixel

    # Hidden data is stored in the LSB of the red channel
    bits.append(r & 1)

data = bytearray()

# Convert collected bits to bytes, MSB-first
for i in range(0, len(bits), 8):
    chunk = bits[i:i + 8]

    if len(chunk) < 8:
        break

    value = 0

    for bit in chunk:
        value = (value << 1) | bit

    data.append(value)

# First four bytes contain the big-endian payload length
length = int.from_bytes(data[:4], "big")

print(f"[+] Payload length: {length}")

encoded_payload = bytes(data[4:4 + length])

print(f"[+] Encoded payload: {encoded_payload.decode()}")

ciphertext = base64.b64decode(encoded_payload)

print(f"[+] Base64 decoded: {ciphertext!r}")

key = b"TYPEFACE"

plaintext = bytes(
    byte ^ key[i % len(key)]
    for i, byte in enumerate(ciphertext)
)

print(f"[+] Flag: {plaintext.decode()}")
```

Expected output:

```text
[+] Payload length: 36
[+] Encoded payload: PDIjPjwqNCwnKiQkM3cyNCVvKTc3MHchKQ==
[+] Base64 decoded: b"<2#><*4,'*$$3w24%o)770w!)"
[+] Flag: hks{zkwisstau6qqq6yrqq4d}
```

---

# Extraction Chain

```text
spiderman_ctf_challenge.pdf
        │
        ├── Visible decoy
        │      │
        │      └── hks{not_the_real_flag_keep_looking}
        │
        ├── PDF metadata
        │      │
        │      └── Base64 encoded hint
        │
        └── Embedded attachment
               │
               └── signal.png
                       │
                       └── Red-channel LSBs
                               │
                               ├── First 4 bytes
                               │      └── 0x00000024
                               │             └── 36 byte payload
                               │
                               └── PDIjPjwqNCwnKiQkM3cyNCVvKTc3MHchKQ==
                                      │
                                      └── Base64 decode
                                             │
                                             └── <2#><*4,'*$$3w24%o)770w!)
                                                    │
                                                    └── Repeating-key XOR
                                                           │
                                                           └── TYPEFACE
                                                                  │
                                                                  ▼
                                                    hks{zkwisstau6qqq6yrqq4d}
```

---

# Flag

```text
hks{zkwisstau6qqq6yrqq4d}
```

---

## Conclusion

This challenge combined several forensic techniques instead of relying on a single hiding mechanism.

The main stages were:

- PDF text inspection
- Identification of a fake flag
- PDF metadata analysis
- Base64 decoding
- Extraction of an embedded PDF attachment
- PNG LSB steganography
- Big-endian length parsing
- Another Base64 decoding layer
- Repeating-key XOR decryption

The most important clue was recognizing that the obvious flag was intentionally planted as a decoy and continuing to inspect the PDF's internal structure.

**Final Flag:**

```text
hks{zkwisstau6qqq6yrqq4d}
```
