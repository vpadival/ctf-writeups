# _THE_WEB_OF_SHADOWS

**Category:** Forensics  
**Difficulty:** Medium  
**Points:** 294  
**Flag Format:** `hks{...}`

---

## Challenge Description

Three weeks ago, something changed inside Oscorp Tower.

Norman Osborn vanished from the executive floor, but his terminal continued logging in at unusual hours from an IP address that did not exist on the corporate VLAN.

Peter Parker later captured a short burst of suspicious outbound traffic originating from a decommissioned server in Sub-Basement 4. The traffic was distributed across several different protocols:

- DNS
- ICMP
- TCP
- HTTP

The challenge description hinted that the protocols were not independent. Instead, each layer contained a clue explaining how to extract information from the next one.

The objective was to analyze `web_of_shadows.pcap` and recover the secret being exfiltrated from Oscorp.

---

## Initial Analysis

The first step was to inspect the PCAP and identify unusual communication patterns.

Several suspicious groups of packets stood out:

- DNS requests involving `nibble-web.darkweb`
- ICMP echo traffic
- TCP SYN packets targeting port `31337`
- HTTP requests using an unusual user-agent
- Traffic containing what appeared to already be an `hks{...}` flag

Because the challenge specifically mentioned **multiple protocols and multiple layers**, the immediately visible flag was suspicious and was not assumed to be genuine.

---

# Stage 1 — DNS

The first meaningful clue was hidden in DNS queries originating from:

```text
10.66.6.66
```

The queries contained labels under:

```text
nibble-web.darkweb
```

There were six indexed fragments, numbered approximately:

```text
00
01
02
03
04
05
```

Each fragment contained hexadecimal-looking data.

At first glance, directly converting the hexadecimal bytes did not produce readable text.

The domain name itself provided a hint:

```text
nibble-web
```

A **nibble** is four bits, meaning half of a byte.

For each byte:

```text
AB
```

we swapped its upper and lower hexadecimal nibbles:

```text
AB -> BA
```

After concatenating the six DNS fragments in the correct order and nibble-swapping every byte, the following instruction appeared:

```text
icmp_4762_byte_at_seq_mod_len
```

This clearly described how the next protocol layer should be processed.

---

# Stage 2 — ICMP

The decoded DNS clue was:

```text
icmp_4762_byte_at_seq_mod_len
```

This was interpreted as:

- Find ICMP packets using identifier `0x4762`
- For each packet, use the ICMP sequence number
- Calculate:

```text
sequence % payload_length
```

- Extract the byte at that position from the ICMP payload

Conceptually:

```python
index = sequence_number % len(payload)
character = payload[index]
```

Processing the relevant ICMP echo packets in sequence reconstructed another instruction:

```text
syn_31337_key_is_window_xor_urgptr
```

This pointed directly to TCP SYN packets targeting port `31337`.

---

# Stage 3 — TCP SYN Packets

The second clue was:

```text
syn_31337_key_is_window_xor_urgptr
```

The PCAP contained six specially crafted TCP SYN packets targeting:

```text
Destination Port: 31337
```

They originated from source ports:

```text
47000
47001
47002
47003
47004
47005
```

The clue instructed us to XOR two TCP header fields:

```text
TCP Window XOR TCP Urgent Pointer
```

For each packet, the low byte of the XOR result was extracted.

The resulting hexadecimal bytes were:

```text
53 50 31 44 33 52
```

Converting them to ASCII:

```text
53 -> S
50 -> P
31 -> 1
44 -> D
33 -> 3
52 -> R
```

produced:

```text
SP1D3R
```

This was clearly intended to be the encryption key for the next stage.

---

# Stage 4 — HTTP

Next, the suspicious HTTP traffic was inspected.

The important HTTP requests used the custom user-agent:

```text
GoblinGlider/6.6.6
```

These requests contained headers named:

```text
X-Goblin-Fragment
```

There were six fragments in total.

The fragment values were Base64 encoded.

After extracting the fragments in their correct order, each one was Base64-decoded and combined into a single byte stream.

The TCP stage had already provided the key:

```text
SP1D3R
```

The reconstructed HTTP payload was therefore XOR-decoded using a repeating `SP1D3R` key.

Conceptually:

```python
key = b"SP1D3R"

plaintext = bytes(
    byte ^ key[i % len(key)]
    for i, byte in enumerate(ciphertext)
)
```

However, the result was still reversed.

Reversing the decoded byte sequence finally revealed the real flag.

---

# Decoy Flag

During analysis, another HTTP stream associated with:

```text
10.13.13.13
```

contained the following value:

```text
hks{n1c3_try_but_th1s_1s_th3_wr0ng_w3b}
```

This translates roughly to:

```text
nice try but this is the wrong web
```

It was intentionally placed as a decoy.

The challenge structure confirmed this: the real solution required following the complete DNS → ICMP → TCP → HTTP chain rather than stopping at the first flag-shaped string.

---

# Full Extraction Chain

The complete chain was:

```text
DNS
 |
 | nibble swap
 v
icmp_4762_byte_at_seq_mod_len
 |
 | ICMP ID = 0x4762
 | payload[sequence % payload_length]
 v
syn_31337_key_is_window_xor_urgptr
 |
 | TCP SYN -> port 31337
 | Window XOR Urgent Pointer
 v
SP1D3R
 |
 | HTTP GoblinGlider/6.6.6
 | Base64 decode fragments
 | repeating-key XOR
 | reverse result
 v
FLAG
```

---

## Flag

```text
hks{w1th_gr34t_p4ck3ts_c0m3s_gr34t_r3sp0ns1b1l1ty}
```

---

## Interpretation

The flag decodes to the Spider-Man-inspired phrase:

```text
with great packets comes great responsibility
```

which fits perfectly with both the Spider-Man/Oscorp theme and the packet-forensics nature of the challenge.

---

## Key Takeaways

This challenge demonstrated several useful network-forensics concepts:

- Inspect unusual DNS query labels for covert data
- Treat protocol names and domain names as possible hints
- Look beyond packet payloads and inspect header fields
- ICMP identifiers and sequence numbers can be used as covert channels
- TCP fields such as Window Size and Urgent Pointer may carry hidden data
- Custom HTTP headers and user-agents are useful indicators during traffic analysis
- Base64 is often only an encoding layer rather than the final solution
- Repeating-key XOR can be hidden across several independently transmitted fragments
- Flag-shaped strings should not automatically be trusted
- In layered CTF challenges, each recovered string may be an instruction rather than the final answer

---

## Tools

Useful tools for solving this challenge include:

```text
Wireshark
tshark
Python
CyberChef
xxd
base64
```

---

## Final Flag

```text
hks{w1th_gr34t_p4ck3ts_c0m3s_gr34t_r3sp0ns1b1l1ty}
```