# Challenge 1: Custom Encoder (Reverse the Logic)

## Description
A flag was run through a custom encoder and given to you as a hex string.

## Encoder
For each byte at index `i`, the encoder does the following:

1. XOR with `0x5A`
2. Add `i % 5`
3. Reverse the whole byte string
4. Hex-encode

## Given
```
28396f406c37056d353006692d2b6b2d692c242b3232
```

## Approach
Undo the steps in reverse order: unhex, reverse, subtract `i % 5`, XOR with `0x5A`.

The order matters. The `i % 5` offset was applied before the reversal, so you have to reverse the bytes first to get the indices lined up again.

## Solution
```python
#!/usr/bin/env python3
def custom_decode(h):
    key = 0x5A
    data = bytes.fromhex(h)[::-1]  # undo the reversal
    return bytes([(b - (i % 5)) ^ key for i, b in enumerate(data)]).decode()

if __name__ == "__main__":
    out = "28396f406c37056d353006692d2b6b2d692c242b3232"
    print(custom_decode(out))
```

## Flag
```
hks{r3v3rs3_th3_l0g1c}
```
The leetspeak reads "reverse the logic".
