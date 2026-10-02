# _MUSK_GOT_HACKED

**Category:** Misc  
**Difficulty:** Easy  
**Points:** 100  
**Flag Format:** `cyberweek{number_of_breaches}`

---

## Challenge Description

The challenge provided the following email address:

```text
elonmusk@gmail.com
```

The objective was to determine how many known data breaches this email address had appeared in and submit that number in the required flag format.

---

## Approach

Since the challenge asks for the number of breaches associated with an email address, this is essentially an OSINT/data-breach lookup challenge.

I initially checked the address using **XposedOrNot**.

```bash
curl -s 'https://api.xposedornot.com/v1/check-email/elonmusk@gmail.com' | jq
```

The API returned a list of known breaches.

To count them automatically:

```bash
curl -s 'https://api.xposedornot.com/v1/check-email/elonmusk@gmail.com' \
| jq '.breaches[0] | length'
```

This returned:

```text
27
```

So the first attempted flag was:

```text
cyberweek{27}
```

However, this was rejected.

---

## Identifying the Correct Source

The differing result suggested that the challenge author was using a different breach database.

The email was then searched on **Have I Been Pwned (HIBP)**.

```text
https://haveibeenpwned.com/
```

Searching:

```text
elonmusk@gmail.com
```

showed that the address had appeared in:

```text
44 data breaches
```

This demonstrated an important point: different breach-monitoring services maintain different datasets, so their reported breach counts may not be identical.

---

## Result

The Have I Been Pwned result was:

```text
44
```

Using the required format:

```text
cyberweek{number_of_breaches}
```

the final flag became:

```text
cyberweek{44}
```

The flag was accepted.

---

## Flag

```text
cyberweek{44}
```

---

## Key Takeaway

This challenge was a simple OSINT task, but the main trick was identifying the **intended breach database**.

XposedOrNot reported:

```text
27 breaches
```

while Have I Been Pwned reported:

```text
44 breaches
```

Since the challenge expected the HIBP result, relying on a single breach-checking service could lead to an incorrect answer.

When solving similar challenges, if the supplied count is rejected, check multiple reputable breach databases and consider which service the challenge creator most likely used.