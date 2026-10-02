# `_EASYBROKEN`

**Category:** Crypto  
**Difficulty:** Easy  
**Points:** 100  
**Flag Format:** `hks{...}`

## Challenge Description

A damaged field radio was recovered near an abandoned forward operating base. The owner of the radio was listed as missing in action.

Among the debris was a note:

> "If command ever gets this, they'll know what to do with the numbers.  
> I just hope they still remember how I built it."

The provided challenge files contained a recovered binary stream fragment along with an encrypted message.

The goal was to reconstruct the intended decryption process and recover the hidden flag.

---

## Provided Files

The challenge archive contained files including:

```text
output.txt
ciphertext.txt
```

`output.txt` contained a recovered binary stream consisting of 192 bits, while `ciphertext.txt` contained the encrypted message in hexadecimal form.

---

## Initial Analysis

The recovered stream immediately looked interesting because it contained exactly:

```text
192 bits
```

Looking at the binary sequence as a possible keystream revealed that it had very low linear complexity.

Using linear recurrence analysis, the stream had a linear complexity of only:

```text
16
```

The recurrence involved offsets:

```text
7, 11, 14, 16
```

This strongly suggested that the original stream had been generated using a small **16-bit Linear Feedback Shift Register (LFSR)**.

---

## LFSR Observation

One particularly useful clue appeared when examining the first 16 recovered bits.

Reversing those bits produced:

```text
0xBEEF
```

This was almost certainly an intentional seed chosen by the challenge author.

The recurrence was consistent with a 16-bit right-shifting LFSR using tap positions corresponding to:

```text
0, 2, 5, 9
```

So the recovered transmission was clearly related to a deliberately weak pseudo-random generator.

However, reconstructing more LFSR output was not actually required to decrypt the final ciphertext.

---

## Finding the Actual Key Derivation

The important realization was that the recovered stream itself was being used as key material.

Rather than directly XORing the ciphertext with the LFSR stream, the contents of `output.txt` were hashed using SHA-256.

Conceptually:

```text
key = SHA256(recovered_stream)
```

The resulting SHA-256 digest was then used as the XOR key for the encrypted message.

Since the ciphertext was shorter than the 32-byte SHA-256 digest, only the required number of key bytes were needed.

---

## Decryption

The complete solve script was:

```python
from hashlib import sha256
from pathlib import Path

stream = Path("output.txt").read_bytes()
ct = bytes.fromhex(
    Path("ciphertext.txt").read_text().strip()
)

key = sha256(stream).digest()

flag = bytes(
    c ^ k
    for c, k in zip(ct, key)
)

print(flag.decode())
```

Running the script produced:

```text
hks{6f2ad9b4e18c73a1}
```

---

## Why It Was Broken

The challenge name, **Easy Broken**, fits the construction well.

The pseudo-random component was based on a tiny 16-bit LFSR. LFSRs are deterministic and have strong linear properties, making them unsuitable for cryptographic keystream generation by themselves.

A sufficiently long section of LFSR output can be used to reconstruct its recurrence and predict subsequent output.

In this case, the recovered 192-bit stream exposed enough information to identify properties such as:

```text
Linear complexity: 16
Seed clue:          0xBEEF
LFSR taps:          0, 2, 5, 9
```

The final encryption layer was also simply:

```text
ciphertext = plaintext XOR SHA256(stream)
```

Once the key derivation method was recognized, recovering the plaintext was straightforward.

---

## Attack Flow

```text
easybroken.zip
      |
      v
Extract files
      |
      v
Inspect output.txt
      |
      +--> 192-bit binary stream
      |
      +--> Linear complexity = 16
      |
      +--> First 16 bits reversed = 0xBEEF
      |
      v
Treat recovered stream as key material
      |
      v
SHA256(output.txt)
      |
      v
XOR digest with ciphertext
      |
      v
Recover plaintext
      |
      v
hks{6f2ad9b4e18c73a1}
```

---

## Flag

```text
hks{6f2ad9b4e18c73a1}
```

---

## Key Takeaways

This challenge demonstrated several useful cryptography concepts:

- LFSRs produce deterministic linear sequences.
- Small LFSRs can be reconstructed from relatively little output.
- Recognizable seeds such as `0xBEEF` are often intentional CTF hints.
- Hashing predictable or publicly recoverable data does not automatically make it secret.
- XOR encryption is only secure when the key material itself is unpredictable and unknown to the attacker.

The main weakness was therefore not SHA-256 itself, but the fact that the data being hashed was completely recoverable from the challenge files.