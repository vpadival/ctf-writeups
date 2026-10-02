# _CRYPTO_KA_BAAP

**Category:** Crypto  
**Difficulty:** Hard  
**Points:** 500  
**Flag:** `DOOM{the_impossible_was_only_unfactored}`

---

## Challenge Description

> “Even Doom leaves traces.”
>
> A strange transmission has surfaced from Latveria. The ciphertext appears to contain no obvious weakness, and the key is nowhere to be found.
>
> But Doom made one mistake: he left part of the message behind.
>
> Half of the message is hidden somewhere outside this challenge. Search HackoSquad’s social media and the social accounts of its team members. Find the missing fragment, connect the clues, and break the cipher.

The supplied file contained an RSA public key and an encrypted value labelled as the key:

```text
D O O M
Latveria // 暗号 // 暗号文

公開値 / Public

n = 18092658332901526341964181422006016852172881445348015540250275883059076861162948590483070147014086472020482948182505539710637416104974413045000248484331159548296569378415195970830700583699869201602854124982762426099784346688016951134632888021397737808991428793252833994859634619882438980608435679771233176224327386406964962798126296723688444396463627121703887629428202552725590676275174564422458376892767218388600713511675128177901438336949994644576271700485698512607222660290887274050911369253629476265434215300941628442619053834527028022901927378228805296607301507255690462153068616706702629687776702528929966465977

e = 65537
```

The encrypted key was:

```text
2952743583722822297557175885429154936940614744045464269516178317355081421119176808771848831740490396072620085181087868753097659566063512886727871425412658627747303476845489174017560001329308343160283931632297853282783354856937245785951503348718065468678906121812725331049805523300064772664543426196971830522461961625628369417751416598842280497760608902429433165779255796665836891092612033445991575929084408387827930747414532978660765435513817138238072078340708132665154992258515174820515046955175716013949716806442986246826272097649058072835757865606828645264216103827874284338314938109450887567065320425610902923225
```

The final line also stated:

```text
there is a missing part
```

This suggested that the RSA ciphertext was only the first stage of the challenge.

---

## 1. Inspecting the RSA Modulus

We are given the usual RSA parameters:

```text
n
e = 65537
c
```

Normally, attacking a properly generated 2048-bit RSA modulus directly would be infeasible.

However, the challenge description says:

> Even Doom leaves traces.

That suggested checking whether the RSA primes had been generated poorly.

One useful attack when RSA primes are extremely close together is **Fermat factorization**.

RSA uses:

```text
n = p × q
```

If `p` and `q` are close, then:

```text
n = a² - b²
```

which can be rewritten as:

```text
n = (a - b)(a + b)
```

Therefore:

```text
p = a - b
q = a + b
```

where:

```text
a = ceil(sqrt(n))
b = sqrt(a² - n)
```

---

## 2. Fermat Factorization

A simple implementation is enough:

```python
from math import isqrt

n = 18092658332901526341964181422006016852172881445348015540250275883059076861162948590483070147014086472020482948182505539710637416104974413045000248484331159548296569378415195970830700583699869201602854124982762426099784346688016951134632888021397737808991428793252833994859634619882438980608435679771233176224327386406964962798126296723688444396463627121703887629428202552725590676275174564422458376892767218388600713511675128177901438336949994644576271700485698512607222660290887274050911369253629476265434215300941628442619053834527028022901927378228805296607301507255690462153068616706702629687776702528929966465977

a = isqrt(n)

if a * a < n:
    a += 1

while True:
    b2 = a * a - n
    b = isqrt(b2)

    if b * b == b2:
        p = a - b
        q = a + b
        break

    a += 1

print("p =", p)
print("q =", q)
print("difference =", q - p)
```

The modulus factors almost immediately.

The difference between the primes is only:

```text
591024
```

This is catastrophically small for RSA.

The recovered factors were:

```text
p =
134508952612461919883423737160321717356815339426543759510078491662564943137901590116316579127263680396929664598730365528229045725047740869437465241405065363550091965641119840791410796784121006769752956640298045162097147204573470245378368473850631107847004458280927772761220990783900538814887074849215435968499
```

```text
q =
134508952612461919883423737160321717356815339426543759510078491662564943137901590116316579127263680396929664598730365528229045725047740869437465241405065363550091965641119840791410796784121006769752956640298045162097147204573470245378368473850631107847004458280927772761220990783900538814887074849215436559523
```

---

## 3. Recovering the RSA Private Key

With `p` and `q`, Euler's totient can be calculated:

```python
phi = (p - 1) * (q - 1)
```

The RSA private exponent is:

```python
d = pow(e, -1, phi)
```

We can then decrypt the encrypted key:

```python
m = pow(c, d, n)
```

Converting the result into bytes:

```python
key = m.to_bytes((m.bit_length() + 7) // 8, "big")

print(key.hex())
```

produced:

```text
eaffdaa03223e362170c2a2026f9a2fa02fd092a3d4006d241a722be48df8afe
```

This is exactly **32 bytes / 256 bits**, strongly suggesting that it is an AES-256 key.

So the first layer had been solved.

---

## 4. Finding the Missing Fragment

The challenge explicitly instructed us to search:

> HackoSquad’s social media and the social accounts of its team members.

Searching through the HackoSquad team led to the profile of **Shaikh Minhaz**.

His About section contained a suspicious block:

```text
第二層 / 第二層
nonce / ノンス
f00316bb14d1f1e841a35ac8

暗号文
a2682e5b8bcddd7a9800701455caca02482f15d9783aebaadb0bc1f0872932dc7da724adbd6aec6c

認証
fba5b8ecd95b84f205a1b4c16dd5b876

終了 / 終了
```

The Japanese labels translate roughly to:

```text
第二層   -> Second layer
nonce   -> Nonce
暗号文   -> Ciphertext
認証     -> Authentication
終了     -> End
```

We therefore had:

```text
Key:
eaffdaa03223e362170c2a2026f9a2fa02fd092a3d4006d241a722be48df8afe

Nonce:
f00316bb14d1f1e841a35ac8

Ciphertext:
a2682e5b8bcddd7a9800701455caca02482f15d9783aebaadb0bc1f0872932dc7da724adbd6aec6c

Authentication Tag:
fba5b8ecd95b84f205a1b4c16dd5b876
```

---

## 5. Identifying the Second Cipher

There were several strong indicators of **AES-GCM**:

- The recovered key is 32 bytes → AES-256
- The nonce is 12 bytes → standard GCM nonce size
- The authentication value is 16 bytes → standard GCM tag size
- We have separate ciphertext and authentication tag fields

Therefore the second layer was **AES-256-GCM**.

---

## 6. AES-GCM Decryption

Using PyCryptodome:

```python
from Crypto.Cipher import AES

key = bytes.fromhex(
    "eaffdaa03223e362170c2a2026f9a2fa"
    "02fd092a3d4006d241a722be48df8afe"
)

nonce = bytes.fromhex(
    "f00316bb14d1f1e841a35ac8"
)

ciphertext = bytes.fromhex(
    "a2682e5b8bcddd7a9800701455caca02"
    "482f15d9783aebaadb0bc1f0872932dc"
    "7da724adbd6aec6c"
)

tag = bytes.fromhex(
    "fba5b8ecd95b84f205a1b4c16dd5b876"
)

cipher = AES.new(
    key,
    AES.MODE_GCM,
    nonce=nonce
)

plaintext = cipher.decrypt_and_verify(
    ciphertext,
    tag
)

print(plaintext.decode())
```

Output:

```text
DOOM{the_impossible_was_only_unfactored}
```

The authentication check succeeds, confirming that both the recovered AES key and the OSINT fragment are correct.

---

## Complete Solver

The RSA portion can be automated as follows:

```python
from math import isqrt
from Crypto.Cipher import AES

n = 18092658332901526341964181422006016852172881445348015540250275883059076861162948590483070147014086472020482948182505539710637416104974413045000248484331159548296569378415195970830700583699869201602854124982762426099784346688016951134632888021397737808991428793252833994859634619882438980608435679771233176224327386406964962798126296723688444396463627121703887629428202552725590676275174564422458376892767218388600713511675128177901438336949994644576271700485698512607222660290887274050911369253629476265434215300941628442619053834527028022901927378228805296607301507255690462153068616706702629687776702528929966465977

e = 65537

c = 2952743583722822297557175885429154936940614744045464269516178317355081421119176808771848831740490396072620085181087868753097659566063512886727871425412658627747303476845489174017560001329308343160283931632297853282783354856937245785951503348718065468678906121812725331049805523300064772664543426196971830522461961625628369417751416598842280497760608902429433165779255796665836891092612033445991575929084408387827930747414532978660765435513817138238072078340708132665154992258515174820515046955175716013949716806442986246826272097649058072835757865606828645264216103827874284338314938109450887567065320425610902923225

# Fermat factorization
a = isqrt(n)

if a * a < n:
    a += 1

while True:
    b2 = a * a - n
    b = isqrt(b2)

    if b * b == b2:
        p = a - b
        q = a + b
        break

    a += 1

assert p * q == n

print(f"[+] p = {p}")
print(f"[+] q = {q}")
print(f"[+] Prime difference = {q - p}")

# RSA private key
phi = (p - 1) * (q - 1)
d = pow(e, -1, phi)

m = pow(c, d, n)

key = m.to_bytes(
    (m.bit_length() + 7) // 8,
    "big"
)

print(f"[+] AES key = {key.hex()}")

# OSINT fragment
nonce = bytes.fromhex(
    "f00316bb14d1f1e841a35ac8"
)

ciphertext = bytes.fromhex(
    "a2682e5b8bcddd7a9800701455caca02"
    "482f15d9783aebaadb0bc1f0872932dc"
    "7da724adbd6aec6c"
)

tag = bytes.fromhex(
    "fba5b8ecd95b84f205a1b4c16dd5b876"
)

# AES-256-GCM
aes = AES.new(
    key,
    AES.MODE_GCM,
    nonce=nonce
)

plaintext = aes.decrypt_and_verify(
    ciphertext,
    tag
)

print(f"[+] Flag: {plaintext.decode()}")
```

Running it produces:

```text
[+] Prime difference = 591024
[+] AES key = eaffdaa03223e362170c2a2026f9a2fa02fd092a3d4006d241a722be48df8afe
[+] Flag: DOOM{the_impossible_was_only_unfactored}
```

---

## Attack Chain

```text
Challenge RSA values
        |
        v
Notice p and q are extremely close
        |
        v
Fermat Factorization
        |
        v
Recover p and q
        |
        v
Calculate phi(n) and private exponent d
        |
        v
RSA decrypt encrypted key
        |
        v
Recover 256-bit AES key
        |
        v
OSINT on HackoSquad/team members
        |
        v
Find nonce + ciphertext + authentication tag
        |
        v
Identify AES-256-GCM
        |
        v
Authenticated decryption
        |
        v
DOOM{the_impossible_was_only_unfactored}
```

---

## Why the RSA Was Broken

The critical cryptographic mistake was generating RSA primes that were far too close together.

For secure RSA:

```text
p and q
```

must be independently generated sufficiently large random primes.

Here:

```text
q - p = 591024
```

which is tiny compared with ~1024-bit prime values.

That makes:

```text
sqrt(n)
```

almost exactly equal to:

```text
(p + q) / 2
```

allowing Fermat factorization to recover both primes essentially instantly.

The flag itself references this mistake:

```text
the_impossible_was_only_unfactored
```

What initially appears to be an impossible 2048-bit RSA problem becomes trivial once the weakness in the modulus is identified.

---

## Key Takeaways

1. Always inspect RSA parameters before assuming brute-force factorization is necessary.
2. Fermat factorization is highly effective when `p` and `q` are unusually close.
3. A decrypted RSA plaintext may be a key for another cryptographic layer rather than the final flag.
4. A 32-byte secret together with a 12-byte nonce and 16-byte tag strongly suggests AES-256-GCM.
5. CTF crypto challenges may combine cryptanalysis with OSINT instead of keeping all required data inside the downloadable challenge.
6. The authentication tag provides a useful correctness check: `decrypt_and_verify()` only succeeds when the correct key, nonce, ciphertext and tag are supplied.

---

## Flag

```text
DOOM{the_impossible_was_only_unfactored}
```