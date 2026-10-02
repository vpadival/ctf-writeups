# WAKANDA_INTERCEPT

**Category:** Misc
**Difficulty:** Easy
**Points:** 300
**Flag format:** `DOOM{}`

## Challenge Description

> we got an intercept but need to crack it before DOOM does

Provided file: `wakanda_intercept.pcap`

## TL;DR

The capture hides a DNS-tunneled exfil split across **two parallel streams**
disguised as `beacon` and `sync` traffic to `kimoyo-relay.net`. Each is a
red herring for the other: one decodes to a message telling you it's a decoy,
the other holds the real flag.

```
DOOM{k1m0y0_fr3qu3ncy_l34k}
```

## Recon

```bash
file wakanda_intercept.pcap
# wakanda_intercept.pcap: pcap capture file, microsecond ts (little-endian) - version 2.4 (Ethernet, capture length 65535)
```

80 packets total. Loaded with Scapy since `tshark`/`tcpdump` weren't available:

```python
from scapy.all import *
pkts = rdpcap('wakanda_intercept.pcap')
print(len(pkts))          # 80
for p in pkts[:20]:
    print(p.summary())
```

The traffic is almost entirely DNS query/answer pairs. Alongside normal-looking
noise domains (`status.shield-uplink.net`, `metrics.outpost-alpha.io`,
`cdn.assets-vibranium.io`, etc.), a cluster of queries stood out:

```
05bjNs.beacon.kimoyo-relay.net.
09ZH0.beacon.kimoyo-relay.net.
08NGt9.sync.kimoyo-relay.net.
07X2wz.sync.kimoyo-relay.net.
01TXtr.sync.kimoyo-relay.net.
...
```

## Spotting the Pattern

Every interesting label has the shape:

```
<2-digit index><base64-ish chunk>.<beacon|sync>.kimoyo-relay.net
```

- The leading 2 digits (`00`–`09`) are a **sequence number**.
- What follows is a chunk of **base64** data.
- Labels are split into two independent, interleaved streams by the
  `beacon` / `sync` subdomain — each stream has its own 0–9 index space.

This interleaving is the trick: read the queries in capture order and the
data looks scrambled/duplicated; split by stream label first and it falls
into two clean, ordered sequences.

## Extraction

```python
from scapy.all import *
import re

pkts = rdpcap('wakanda_intercept.pcap')
seen = set()
beacon, sync = {}, {}

for p in pkts:
    if p.haslayer(DNSQR):
        qname = p[DNSQR].qname.decode().rstrip('.')
        if qname in seen:
            continue          # dedupe query/answer pairs
        seen.add(qname)

        m = re.match(r'^(\d{2})(\w+)\.(beacon|sync)\.kimoyo-relay\.net$', qname)
        if m:
            idx, chunk, kind = m.groups()
            (beacon if kind == 'beacon' else sync)[int(idx)] = chunk

b_str = ''.join(beacon[i] for i in sorted(beacon))
s_str = ''.join(sync[i] for i in sorted(sync))
print('beacon:', b_str)
print('sync:  ', s_str)
```

Output:

```
beacon: RE9PTXtkM2MweV9jaDRubjNsX2Rpc3JlZzRyZH0
sync:   RE9PTXtrMW0weTBfZnIzcXUzbmN5X2wzNGt9
```

## Decoding

Both strings are valid base64:

```python
import base64
print(base64.b64decode(b_str))
print(base64.b64decode(s_str))
```

```
beacon -> b'DOOM{d3c0y_ch4nn3l_disreg4rd}'
sync   -> b'DOOM{k1m0y0_fr3qu3ncy_l34k}'
```

The `beacon` channel decodes to a flag-shaped string that plainly announces
itself as a decoy (`d3c0y_ch4nn3l_disreg4rd`). The `sync` channel holds the
real flag.

## Flag

```
DOOM{k1m0y0_fr3qu3ncy_l34k}
```

## Lessons / Notes

- Don't trust the first flag-shaped string you decode — this challenge
  specifically plants one that self-identifies as a decoy once decoded.
- DNS-tunneling challenges are often split across multiple subdomains/labels
  to obscure ordering; always check for a sequence-number prefix and group
  by any secondary label (here, `beacon` vs `sync`) before concatenating.
- Scapy's `rdpcap` + a quick regex was enough here; no need for `tshark`.
