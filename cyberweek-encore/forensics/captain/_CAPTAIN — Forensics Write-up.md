# _CAPTAIN

**Category:** Forensics  
**Difficulty:** Easy  
**Bounty:** 50 pts  

---

## Challenge Description

> **CLASSIFIED — RECOVERED S.H.I.E.L.D. ARCHIVE**
>
> Everyone remembers the photo. Smoke over the Leipzig/Halle tarmac. Six figures who used to be a team, running toward each other as enemies.
>
> What nobody's ever seen is what Steve Rogers buried inside that photo forty minutes before it was taken — a personal log he couldn't risk transmitting, encoded the old way, hidden somewhere Ross's surveillance net would never think to check.
>
> The file above is that photo. Untouched on the surface. But somewhere in its bytes, Steve's real briefing is still sitting there, waiting for someone patient enough to dig it out.

The challenge provided what appeared to be a normal image:

```text
civil_war_dossier.jpg
```

The objective was to investigate the file and recover the hidden briefing.

---

## Initial Analysis

The first step was to inspect the provided image rather than trusting its `.jpg` extension.

Although the file was named:

```text
civil_war_dossier.jpg
```

inspection revealed that the underlying image format was actually **WebP**, which uses a **RIFF container**.

A WebP file typically begins with a structure similar to:

```text
RIFF....WEBP
```

This immediately indicated that the filename extension was misleading.

---

## Investigating the RIFF Container

RIFF files store the expected container size inside their header.

By comparing the size declared in the RIFF structure with the actual file size, an inconsistency became apparent.

The legitimate WebP/RIFF image ended at approximately:

```text
81436 bytes
```

However, the complete file size was:

```text
83191 bytes
```

This meant additional data existed after the legitimate image container.

The amount of trailing data was:

```text
83191 - 81436 = 1755 bytes
```

Therefore, approximately **1755 bytes** had been appended to the image.

---

## Inspecting the Appended Data

Examining the bytes immediately after the legitimate RIFF container revealed:

```text
50 4B 03 04
```

Which corresponds to:

```text
PK\x03\x04
```

This is the standard signature for a **ZIP archive**.

The challenge was therefore using simple file concatenation:

```text
[Valid WebP Image][Hidden ZIP Archive]
```

The image remained perfectly valid and could still be opened normally, while the hidden archive was stored after the logical end of the image data.

---

## Extracting the Hidden Archive

Since the hidden ZIP archive began at byte offset `81436`, it could be carved directly from the original file.

Using `dd`:

```bash
dd if=civil_war_dossier.jpg of=hidden.zip bs=1 skip=81436
```

The extracted file could then be verified using:

```bash
file hidden.zip
```

The resulting data was correctly identified as a ZIP archive.

---

## Extracting the ZIP Archive

The archive was extracted using:

```bash
unzip hidden.zip
```

It contained:

```text
mission_briefing.txt
```

Reading the recovered file:

```bash
cat mission_briefing.txt
```

revealed Steve Rogers' hidden briefing, with the flag located at the end.

---

## Flag

```text
hks{m4jxoiglrnw4uc21237t}
```

---

## Investigation Flow

```text
civil_war_dossier.jpg
        │
        ▼
Inspect actual file structure
        │
        ▼
Identify WebP / RIFF container
        │
        ▼
Compare RIFF size with physical file size
        │
        ▼
Discover 1755 trailing bytes
        │
        ▼
Find PK\x03\x04 ZIP signature
        │
        ▼
Carve data from offset 81436
        │
        ▼
hidden.zip
        │
        ▼
mission_briefing.txt
        │
        ▼
hks{m4jxoiglrnw4uc21237t}
```

---

## Key Takeaways

This challenge demonstrates an important digital forensics principle:

> **Never trust a file extension or what a file appears to contain.**

The visible image itself was valid, but additional information had simply been appended after the end of its legitimate RIFF container.

Useful forensic commands for similar challenges include:

```bash
file <filename>
xxd <filename> | less
strings <filename>
binwalk <filename>
```

It is also useful to compare:

- The file's actual physical size
- The size declared by its internal structure
- Known file signatures or magic bytes
- Any data existing after the logical end of the file

Common embedded-file signatures include:

```text
ZIP      50 4B 03 04
PNG      89 50 4E 47
JPEG     FF D8 FF
PDF      25 50 44 46
ELF      7F 45 4C 46
```

In this challenge, identifying the ZIP signature immediately after the WebP container was enough to locate and recover the hidden evidence.

---

## Conclusion

`_CAPTAIN` was a straightforward **file-carving forensics challenge** disguised as image steganography.

Rather than modifying pixels or hiding information using techniques such as LSB steganography, the challenge simply appended a ZIP archive after a legitimate WebP image.

Once the true image boundary was identified, the hidden archive could be carved and extracted to recover:

```text
mission_briefing.txt
```

which ultimately revealed the flag:

```text
hks{m4jxoiglrnw4uc21237t}
```