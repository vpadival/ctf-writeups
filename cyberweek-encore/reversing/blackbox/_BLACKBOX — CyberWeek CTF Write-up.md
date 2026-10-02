# _BLACKBOX

**Category:** Reversing  
**Difficulty:** Easy  
**Points:** 200

## Challenge Description

> 01:47 UTC — unscheduled capture triggered on the wideband array. Duration: 9.6 seconds of modulated audio, bracketed by a burst of DNS-shaped traffic on the ground relay and a stray file drop that nobody on shift will admit to touching. Four files, then a fifth appeared in the capture directory that none of the on-call engineers can explain.

The challenge provided a ZIP archive containing five files:

```text
audio.wav
capture.pcap
image.png
firmware.bin
unknown.dat
```

The challenge description strongly suggested that the artifacts were connected and that the unexplained fifth file was the final stage of the chain.

---

## Initial Analysis

After extracting the archive, I checked the file types and sizes.

The artifacts consisted of:

- A 9.6-second WAV audio file
- A small packet capture
- A PNG image
- A firmware binary
- An unknown binary file

Instead of treating them independently, I followed the clues from one file into the next.

The overall chain turned out to be:

```text
capture.pcap
     ↓
Key Part 1
     ↓
audio.wav
     ↓
Key Part 2
     ↓
image.png
     ↓
Key Part 3 + firmware location
     ↓
firmware.bin
     ↓
Final XOR key
     ↓
unknown.dat
     ↓
FLAG
```

---

# Stage 1 — DNS Traffic

I started with:

```text
capture.pcap
```

Inspecting the DNS traffic revealed several suspicious query components containing hexadecimal data.

Examples included chunks such as:

```text
4b455950
41525431
3d37463b
```

These values appeared to be ordered fragments rather than normal DNS data.

After concatenating the hexadecimal chunks and decoding them as ASCII, the result was:

```text
KEYPART1=7F;NEXT=AUDIO;LISTEN=SPECTRUM
```

This provided both the first key byte and the next instruction.

```text
KEYPART1 = 0x7F
```

The phrase:

```text
LISTEN=SPECTRUM
```

suggested that the next artifact should be inspected visually using a spectrogram.

---

# Stage 2 — Audio Spectrogram

The next file was:

```text
audio.wav
```

Listening to the file directly did not reveal anything especially useful.

Since the DNS clue explicitly mentioned:

```text
LISTEN=SPECTRUM
```

I generated a spectrogram of the audio.

The audio contained visible text encoded into its frequency spectrum.

The spectrogram revealed:

```text
KEYPART2=3C
```

Therefore:

```text
KEYPART2 = 0x3C
```

At this stage the collected key bytes were:

```text
7F 3C
```

---

# Stage 3 — Image LSB Data

The next artifact was:

```text
image.png
```

Visual inspection of the image did not immediately reveal anything useful, so I checked for hidden pixel-level information.

Reading the least significant bits of the RGB channels from the first row of pixels revealed hidden byte data.

The extracted data ended with the marker:

```text
####END####
```

The bytes before this marker were not directly readable, indicating another layer of obfuscation.

Since the previous stage produced:

```text
KEYPART2 = 0x3C
```

I XORed the hidden image data with:

```text
0x3C
```

The decrypted result was:

```text
KEYPART3=A9;FIRMWARE_OFFSET=0x0200;FIRMWARE_LEN=48
```

This gave the third key byte:

```text
KEYPART3 = 0xA9
```

It also provided instructions for extracting data from the firmware:

```text
Offset: 0x0200
Length: 48 bytes
```

The complete three-byte key was now:

```text
7F 3C A9
```

---

# Stage 4 — Firmware Extraction

The next file was:

```text
firmware.bin
```

The binary contained a deliberate firmware-style header identifying it as a Blackbox relay firmware image.

Using the values recovered from the PNG:

```text
Offset = 0x0200
Length = 48
```

I extracted 48 bytes beginning at hexadecimal offset `0x200`.

For example:

```bash
dd if=firmware.bin of=firmware_chunk.bin bs=1 skip=$((0x200)) count=48
```

The extracted bytes were still encoded.

I then XORed the firmware chunk using the repeating three-byte key recovered from the previous stages:

```text
7F 3C A9
```

Conceptually:

```python
key = bytes([0x7F, 0x3C, 0xA9])

decoded = bytes(
    byte ^ key[i % len(key)]
    for i, byte in enumerate(data)
)
```

The result contained:

```text
GHOST-SIGNAL-ORBIT-7734
```

This clearly looked like the key required for the final artifact.

---

# Stage 5 — Decrypting `unknown.dat`

The mysterious fifth file was:

```text
unknown.dat
```

I used the recovered ASCII string:

```text
GHOST-SIGNAL-ORBIT-7734
```

as a repeating XOR key against the entire contents of `unknown.dat`.

Example Python logic:

```python
from pathlib import Path

data = Path("unknown.dat").read_bytes()

key = b"GHOST-SIGNAL-ORBIT-7734"

plaintext = bytes(
    byte ^ key[i % len(key)]
    for i, byte in enumerate(data)
)

print(plaintext.decode())
```

The resulting plaintext was:

```text
TRANSMISSION DECODED.
SOURCE: UNKNOWN. ORIGIN: NOT EARTH ORBIT.
REPEATING BEACON PATTERN CONFIRMED ACROSS ALL FOUR CAPTURE LAYERS.
YOU FOLLOWED THE SIGNAL ALL THE WAY DOWN. WELL DONE.

FLAG: cyberweek{s1gn4l_thr0ugh_th3_st4t1c_orb1t7734}
```

---

# Flag

```text
cyberweek{s1gn4l_thr0ugh_th3_st4t1c_orb1t7734}
```

---

# Solve Summary

The challenge used several different hiding and encoding techniques chained together:

```text
PCAP DNS Hex
    ↓
KEYPART1 = 7F

Audio Spectrogram
    ↓
KEYPART2 = 3C

PNG RGB LSB
    ↓ XOR 0x3C
KEYPART3 = A9
Firmware Offset = 0x200
Length = 48

Firmware Chunk
    ↓ XOR with 7F 3C A9
GHOST-SIGNAL-ORBIT-7734

unknown.dat
    ↓ repeating XOR
Final plaintext + flag
```

Each artifact contained either a key component or explicit instructions for processing the next stage, making the challenge a layered combination of packet analysis, audio steganography, image LSB extraction, firmware reversing, and XOR decryption.

## Final Flag

```text
cyberweek{s1gn4l_thr0ugh_th3_st4t1c_orb1t7734}
```