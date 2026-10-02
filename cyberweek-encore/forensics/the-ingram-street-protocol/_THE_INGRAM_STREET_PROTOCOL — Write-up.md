# `_THE_INGRAM_STREET_PROTOCOL`

**Category:** Forensics  
**Difficulty:** Easy  
**Points:** 100  
**Flag Format:** `hks{...}`

---

## Challenge Description

> They pulled the phone out of a storm drain two blocks from the fight. Screen spider-webbed with cracks — no pun intended — but the storage chip survived. NYPD digital forensics pulled two files off it before the battery finally died for good: one photo, and one contact card synced from an old backup.
>
> Everyone on the team is staring at the photo. Nobody's opened the contact card. That's the mistake Mysterio would want you to make — stare at the thing that's obviously hiding something, and ignore the thing that looks like nothing at all.
>
> Somewhere in that photo is a message Peter needed someone to be able to read, even if he never made it home to explain it himself. He wouldn't have locked it behind something only he'd remember. He'd have locked it behind something the people he trusted would remember too.
>
> Two files. One case. Find what connects them.

---

## Provided Files

Extracting the challenge archive gives two files:

```text
phone_recovery.png
may_parker.vcf
```

The challenge description heavily hints that the contact card should not be ignored, so I started there.

---

## 1. Inspecting the Contact Card

A `.vcf` file is a standard vCard contact file and can simply be opened as text:

```bash
cat may_parker.vcf
```

The important contents were:

```text
FN:May Parker

ADR;TYPE=HOME:;;20 Ingram Street;Forest Hills;NY;11375;USA

BDAY:1962-03-11

NOTE:Peter\, if you're reading this off my old contact backup instead of calling me like a normal nephew\, you're probably locked out of something again. Same as always -- the alarm code Ben set the week we moved in and never once changed in thirty years. Street name\, no spaces\, capital letters where they belong\, then the year on the deed. That's it. That's always been it.

X-KEYPAD-CODE:IngramSt1962
```

The key clue is the custom field:

```text
X-KEYPAD-CODE:IngramSt1962
```

The note also explains how the value was constructed:

```text
Street name + year
```

So our likely key is:

```text
IngramSt1962
```

---

## 2. Investigating the PNG

The second artifact is:

```text
phone_recovery.png
```

Basic metadata and file inspection did not immediately reveal the hidden message.

The story suggests that something is hidden **inside the image**, so I checked the image's pixel data for Least Significant Bit steganography.

The idea behind LSB steganography is simple: each RGB color channel is represented by a byte.

For example:

```text
10110110
```

Changing only the final bit has almost no visible effect on the image:

```text
10110111
```

Those least-significant bits can therefore be combined to store another data stream.

---

## 3. Extracting the RGB LSB Stream

I extracted the least-significant bit of every RGB channel and grouped every eight bits into one byte.

A small Python script can do this:

```python
from PIL import Image

img = Image.open("phone_recovery.png").convert("RGB")

bits = []

for pixel in img.getdata():
    for channel in pixel:
        bits.append(channel & 1)

data = bytearray()

for i in range(0, len(bits) - 7, 8):
    value = 0

    for bit in bits[i:i + 8]:
        value = (value << 1) | bit

    data.append(value)

print(data[:64])
```

The beginning of the extracted stream was:

```text
SPDR\x00\x19...
```

This is a strong indication that we found the intended hidden data.

---

## 4. Understanding the Hidden Structure

The first four bytes are:

```text
SPDR
```

which act as a custom magic/header value.

Immediately following them are:

```text
00 19
```

Interpreting these two bytes as a big-endian integer:

```text
0x0019 = 25
```

So the custom structure appears to be:

```text
+----------------------+------------------+
| SPDR                 | 4-byte magic     |
+----------------------+------------------+
| 00 19                | payload length   |
+----------------------+------------------+
| encrypted data       | 25 bytes         |
+----------------------+------------------+
```

The 25-byte encrypted payload was:

```text
21 05 14 09 50 0f 3b 16 02 7d 5a 73 27
0a 50 46 23 34 66 25 5b 58 47 51 34
```

or:

```text
21051409500f3b16027d5a73270a5046233466255b58475134
```

---

## 5. Connecting the Two Files

At this point we had:

### From the contact card

```text
IngramSt1962
```

### From the image

A 25-byte encrypted payload.

The challenge specifically says:

> Two files. One case. Find what connects them.

The vCard therefore appears to provide the key needed to decode the data hidden inside the photograph.

I tried repeating `IngramSt1962` over the payload and XORing the two byte streams.

---

## 6. XOR Decryption

The following Python code reproduces the complete extraction and decryption:

```python
from PIL import Image

IMAGE = "phone_recovery.png"
KEY = b"IngramSt1962"

img = Image.open(IMAGE).convert("RGB")

# Extract RGB least-significant bits
bits = []

for pixel in img.getdata():
    for channel in pixel:
        bits.append(channel & 1)

# Convert bit stream to bytes
raw = bytearray()

for i in range(0, len(bits) - 7, 8):
    byte = 0

    for bit in bits[i:i + 8]:
        byte = (byte << 1) | bit

    raw.append(byte)

# Validate custom header
magic = raw[:4]

if magic != b"SPDR":
    raise ValueError("SPDR header not found")

# Two-byte big-endian payload size
length = int.from_bytes(raw[4:6], "big")

print(f"[+] Magic: {magic.decode()}")
print(f"[+] Payload length: {length}")

# Extract encrypted payload
encrypted = bytes(raw[6:6 + length])

print(f"[+] Encrypted payload: {encrypted.hex()}")

# Repeating-key XOR
plaintext = bytes(
    byte ^ KEY[i % len(KEY)]
    for i, byte in enumerate(encrypted)
)

print(f"[+] Decrypted: {plaintext.decode()}")
```

Running it gives:

```text
[+] Magic: SPDR
[+] Payload length: 25
[+] Encrypted payload: 21051409500f3b16027d5a73270a5046233466255b58475134
[+] Decrypted: hks{1bhb3DlAnd74BY5Qjaqc}
```

---

## Flag

```text
hks{1bhb3DlAnd74BY5Qjaqc}
```

---

## Solution Summary

The challenge used both supplied artifacts rather than hiding everything in the obvious image.

1. Opened `may_parker.vcf`.
2. Found the custom keypad value:

   ```text
   IngramSt1962
   ```

3. Extracted RGB least-significant bits from `phone_recovery.png`.
4. Reconstructed the hidden byte stream.
5. Identified the custom `SPDR` header.
6. Read `0x0019` as a 25-byte payload length.
7. Extracted the encrypted 25-byte payload.
8. Used `IngramSt1962` as a repeating XOR key.
9. Recovered the flag:

```text
hks{1bhb3DlAnd74BY5Qjaqc}
```

The central trick was exactly what the challenge description hinted at: **the photograph contained the encrypted message, but the seemingly harmless contact card contained the information required to unlock it.**