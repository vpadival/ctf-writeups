# _STONES

**Category:** Misc  
**Difficulty:** Medium  
**Points:** 300  

## Challenge Description

> Something powerful is hidden inside an Infinity Stone—but it won't reveal itself that easily.

The challenge provided the following archive:

```text
The_Hidden_Infinity_Stone_PARTICIPANT.zip
```

After extracting the archive, the main artifact was:

```text
infinity_stone.png
```

The challenge hinted that something was hidden *inside* the Infinity Stone, suggesting image steganography.

---

## Initial Analysis

I first inspected the image for obvious embedded information, including:

- Metadata
- Appended files/data
- Visible strings
- Steganographic patterns
- Individual RGB bit planes

The visible image itself did not immediately reveal the flag.

Since PNG images preserve pixel values losslessly, examining the individual bits of each RGB channel was a logical next step.

---

## Bit-Plane Analysis

The RGB channels were separated and their individual bit planes inspected.

The **least significant bit of the red channel** contained readable text.

Extracting those bits revealed the following message:

```text
DOOM'S NOTE: The green storm carries the Stone. Ignore the obvious noise.
Begin at pixel 17, then take every 13th pixel.
Read the SECOND bit from the green channel.
The first two bytes give the payload length.
Extract exactly that many bytes, reverse them,
XOR with LATVERIA, then decode Base32.
```

This provided the complete extraction algorithm.

---

## Stage 1 — Extract the Hidden Bitstream

According to Doom's note:

- Use the **green channel**
- Start at pixel index `17`
- Select every `13th` pixel
- Read the **second bit**, i.e. bit position `1`
- Reassemble the bits into bytes

Conceptually:

```python
bit = (green_value >> 1) & 1
```

The extracted byte stream began with two bytes representing the length of the hidden payload.

Those bytes were:

```text
00 24
```

Interpreted as a big-endian integer:

```text
0x0024 = 36
```

Therefore, exactly **36 bytes** had to be extracted after the two-byte length field.

---

## Stage 2 — Reverse the Payload

The extracted 36-byte payload was stored backwards.

The next step was therefore:

```python
payload = payload[::-1]
```

---

## Stage 3 — XOR with `LATVERIA`

The reversed data was encrypted using a repeating XOR key:

```text
LATVERIA
```

The operation can be reproduced with:

```python
key = b"LATVERIA"

decoded = bytes(
    byte ^ key[i % len(key)]
    for i, byte in enumerate(payload)
)
```

After the XOR operation, the following string was recovered:

```text
IRHU6TL3MVWWK4TBNRSF643UN5ZG2XZRG56Q
```

The character set strongly suggested **Base32**.

---

## Stage 4 — Base32 Decode

Decoding the recovered string:

```python
import base64

data = b"IRHU6TL3MVWWK4TBNRSF643UN5ZG2XZRG56Q"

print(base64.b32decode(data).decode())
```

produced:

```text
DOOM{emerald_storm_17}
```

---

## Complete Extraction Script

A simplified script reproducing the important extraction steps is shown below:

```python
from PIL import Image
import base64

IMAGE = "infinity_stone.png"

img = Image.open(IMAGE).convert("RGB")
pixels = list(img.getdata())

# Hidden payload settings recovered from the red-channel LSB message.
start = 17
step = 13

bits = []

for i in range(start, len(pixels), step):
    r, g, b = pixels[i]

    # SECOND bit of the green channel
    bit = (g >> 1) & 1
    bits.append(bit)

# Convert bitstream to bytes.
raw = bytearray()

for i in range(0, len(bits) - 7, 8):
    value = 0

    for bit in bits[i:i + 8]:
        value = (value << 1) | bit

    raw.append(value)

# First two bytes contain the payload length.
payload_length = int.from_bytes(raw[:2], "big")

print(f"[+] Payload length: {payload_length}")

payload = bytes(raw[2:2 + payload_length])

# Reverse stored payload.
payload = payload[::-1]

# Repeating XOR key.
key = b"LATVERIA"

base32_data = bytes(
    value ^ key[i % len(key)]
    for i, value in enumerate(payload)
)

print(f"[+] Base32: {base32_data.decode()}")

flag = base64.b32decode(base32_data).decode()

print(f"[+] Flag: {flag}")
```

Expected output:

```text
[+] Payload length: 36
[+] Base32: IRHU6TL3MVWWK4TBNRSF643UN5ZG2XZRG56Q
[+] Flag: DOOM{emerald_storm_17}
```

---

## Extraction Flow

```text
infinity_stone.png
        │
        ▼
Red Channel LSB
        │
        ▼
Doom's Hidden Instructions
        │
        ▼
Green Channel — Bit 1
        │
Start Pixel: 17
Every 13th Pixel
        │
        ▼
First 2 Bytes
0x0024 → 36-byte payload
        │
        ▼
Reverse Payload
        │
        ▼
Repeating XOR
Key: LATVERIA
        │
        ▼
Base32 String
        │
        ▼
Base32 Decode
        │
        ▼
DOOM{emerald_storm_17}
```

---

## Flag

```text
DOOM{emerald_storm_17}
```

---

## Conclusion

`_STONES` used multiple steganographic and encoding layers rather than hiding the flag directly in the image.

The key observation was examining the image's **bit planes**. The red-channel LSB contained instructions rather than the final secret. Those instructions then directed us toward a second covert channel inside the green pixel values.

The complete chain was:

```text
PNG bit-plane analysis
→ Red-channel LSB message
→ Green-channel bit extraction
→ Length-prefixed payload
→ Reverse bytes
→ XOR with LATVERIA
→ Base32 decode
→ Flag
```

The challenge was a nice example of layered image steganography where one hidden channel acts as a guide to extracting another.