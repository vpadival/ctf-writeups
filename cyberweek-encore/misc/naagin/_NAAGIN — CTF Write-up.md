# _NAAGIN

**Category:** Misc  
**Difficulty:** Easy  
**Points:** 100  

## Challenge Description

> complete the python file and get the flag  
> dont try to bruteforce ⚠️🥷

The challenge provides a ZIP containing a partially completed Python script along with a list of candidate flags.

The objective is to identify the missing portions of the script and use the intended filtering logic to recover the correct flag without brute-forcing anything.

---

## Initial Analysis

After extracting the provided archive, the important Python logic looked roughly like this:

```python
import hashlib

with open("flags.txt") as f:
    for line in f:
        flag = line.strip()
        h = hashlib.sha256(flag._____()).hexdigest()
        if h.startswith("00__0"):
            print(flag, h)
```

There were two incomplete parts:

```python
flag._____()
```

and

```python
"00__0"
```

The challenge specifically warned us not to brute-force, suggesting that the correct flag already existed inside `flags.txt` and only needed to be selected using the proper hash condition.

---

## Completing the Python Code

### 1. Fixing the SHA-256 Input

Python's `hashlib.sha256()` expects bytes rather than a normal string.

Therefore:

```python
flag._____()
```

should be:

```python
flag.encode()
```

This produces:

```python
hashlib.sha256(flag.encode()).hexdigest()
```

---

### 2. Determining the Hash Prefix

The second incomplete value was:

```python
"00__0"
```

A SHA-256 hash represented with `hexdigest()` contains only hexadecimal characters:

```text
0-9
a-f
```

Therefore the underscore characters cannot literally appear in the resulting digest.

The intended completed prefix is:

```python
"00000"
```

So the final condition becomes:

```python
if h.startswith("00000"):
```

---

## Completed Solver

The reconstructed Python script is:

```python
import hashlib

with open("flags.txt") as f:
    for line in f:
        flag = line.strip()

        h = hashlib.sha256(flag.encode()).hexdigest()

        if h.startswith("00000"):
            print(flag, h)
```

---

## Running the Solver

Executing the completed script checks each supplied candidate flag and calculates its SHA-256 digest.

Only one candidate satisfies the required condition:

```text
flag{6cde58290407906d53328533859ac9cfa8000d52}
000008e9fae260644161592e0d23bd53066bf57f4af26608f2b52e25863ad58c
```

Notice that the hash begins with:

```text
00000
```

which matches the reconstructed condition.

---

## Flag

```text
flag{6cde58290407906d53328533859ac9cfa8000d52}
```

---

## Key Takeaways

This challenge was mainly about understanding the incomplete Python code rather than performing any cryptographic attack.

The important observations were:

- `hashlib.sha256()` requires byte input, so the flag must be converted using `encode()`.
- SHA-256 hexadecimal output can only contain characters `0-9` and `a-f`.
- The supplied underscores therefore represented missing characters rather than literal characters.
- Completing the prefix as `00000` uniquely identified the correct candidate.
- No brute-force attack was necessary because all possible flags were already provided in `flags.txt`.

## Tools Used

- Python
- `hashlib`
- SHA-256
- Basic source-code analysis