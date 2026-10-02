# Challenge 3: Base64 (Welcome)

## Description
A short encoded string that decodes straight to a flag.

## Given
```
aGtze3czbGMwbTNfdDBfY3RmfQ==
```

## Approach
The trailing `==` padding and the character set point to base64. Decode it directly:

```bash
echo 'aGtze3czbGMwbTNfdDBfY3RmfQ==' | base64 -d
```

## Flag
```
hks{w3lc0m3_t0_ctf}
```
The leetspeak reads "welcome to ctf". If the platform rejects it, check whether it expects a different prefix, since `hks{...}` is what the string decodes to as-is.
