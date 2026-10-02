# Challenge 2: Caesar Cipher

## Description
The flag is hidden behind a Caesar cipher. Only letters shift; digits and punctuation stay put.

## Given
```
uxf{p43f4e_fu1sg_frperg}
```

## Approach
There are only 26 possible shifts, so brute-force them all and look for the line starting with `hks{`. It appears at `k = 13` (ROT13). The other 25 shifts give gibberish.

## Solution
```python
ct = "uxf{p43f4e_fu1sg_frperg}"
for k in range(26):
    out = "".join(
        chr((ord(c) - 97 + k) % 26 + 97) if c.islower() else c
        for c in ct
    )
    print(k, out)
```

## Flag
```
hks{c43s4r_sh1ft_secret}
```
The leetspeak reads "caesar shift secret", and the `hks{` prefix matches the previous challenge's flag format.
