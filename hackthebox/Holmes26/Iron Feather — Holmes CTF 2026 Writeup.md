# Iron Feather — Holmes CTF 2026 Writeup

## Scenario 7 — Iron Feather

Iron Feather is a mixed reverse-engineering and drone-forensics challenge involving an encrypted PX4 datastore, a stripped PX4 binary, mission data, and flight telemetry.

The investigation required recovering the datastore encryption scheme, deriving the AES key, identifying the active mission, reconstructing the payload-release event, detecting an injected MAVLink command, and analyzing the resulting crash.

---

## Challenge Objectives

The challenge asked us to determine:

- the encrypted datastore file format
- the encryption algorithm
- the custom key-derivation implementation
- the final AES-256 key
- the active PX4 mission bank
- the number of mission items
- the payload-release mission item
- takeoff, release, landing, and crash coordinates
- the malicious MAVLink command
- distance traveled before sabotage
- the exact disarm time
- the road closest to the crash site

---

# Artifacts

The challenge package contained several important artifacts.

The most relevant were:

```text
px4
encrypted datastore image
encrypted ULog / flight data
scenario PDF
```

The supplied `px4` executable was especially important because the encryption and key-derivation logic had to be recovered from the binary itself.

---

# Tools Used

The investigation relied on a combination of reverse-engineering, cryptographic, and telemetry-analysis techniques.

Typical tools useful for this challenge include:

```text
file
xxd / hexdump
strings
readelf
objdump
Ghidra / IDA
gdb
Python
OpenSSL-compatible crypto libraries
PX4 ULog parsers
pyulog
custom Python scripts
geospatial distance calculations
mapping / reverse-geocoding tools
```

Not every answer came from a single tool. Several findings required correlating results from the PX4 binary, decrypted datastore, and telemetry.

---

# Methodology

The investigation was split into four main stages:

```text
Stage 1: Identify encrypted datastore format
        ↓
Stage 2: Reverse engineer encryption + KDF
        ↓
Stage 3: Decrypt and parse PX4 mission storage
        ↓
Stage 4: Analyze ULog telemetry and reconstruct crash
```

---

# 1. Initial Artifact Inspection

The encrypted datastore was examined first.

A simple hexadecimal/header inspection revealed the first eight bytes as:

```text
PX4DMENC
```

This was the custom file magic identifying the encrypted datastore format.

Therefore:

```text
Q1: PX4DMENC
```

---

# 2. Encryption Algorithm

Reverse engineering the encryption path in the supplied PX4 binary showed that the datastore was protected using authenticated encryption.

The implementation used:

```text
AES-256-GCM
```

AES-GCM provides:

- AES encryption for confidentiality
- an authentication tag for integrity
- authenticated decryption

The successful authentication of the decrypted datastore later confirmed that this identification was correct.

```text
Q2: AES-256-GCM
```

---

# 3. Custom Key-Derivation Routine

Because the PX4 executable was stripped, the relevant function had to be found by following cryptographic calls and data flow.

The custom key-derivation routine was located at:

```text
RVA 0x170af0
```

Therefore:

```text
Q3: 0x170af0
```

---

# 4. Custom 32-bit Mixing Loop

Inside the key-derivation routine was a custom integer-mixing phase.

The loop counter showed:

```text
384 iterations
```

Therefore:

```text
Q4: 384
```

This custom routine transformed key material before it entered the standard password-based derivation stage.

---

# 5. Standard KDF

The standard KDF called later in the function was identified as:

```text
PBKDF2-HMAC-SHA256
```

The implementation used SHA-256 as the PBKDF2 PRF.

The iteration count was:

```text
8192
```

Therefore:

```text
Q5: PBKDF2-HMAC-SHA256
```

---

# 6. Recovering the AES-256 Key

Reimplementing every custom transformation manually was possible, but the supplied PX4 executable could also be instrumented directly.

The key was recovered from the live decryption process after the custom derivation and PBKDF2 stage.

The resulting 256-bit key was:

```text
a40ba87b8a0e21d4ead98b917c4bf0f60cc65b25c614b93f107e5ed1e483d6ce
```

This is exactly:

```text
32 bytes
64 hexadecimal characters
256 bits
```

The key successfully authenticated and decrypted the supplied encrypted artifacts.

```text
Q6:
a40ba87b8a0e21d4ead98b917c4bf0f60cc65b25c614b93f107e5ed1e483d6ce
```

---

# 7. Active PX4 Mission Bank

PX4 uses separate mission storage banks.

Inspection of the decrypted mission metadata showed:

```text
Active bank: 0
```

Therefore:

```text
Q7: 0
```

---

# 8. Mission Item Count

The mission metadata indicated that the active mission contained:

```text
24 mission items
```

Therefore:

```text
Q8: 24
```

---

# 9. Identifying the Payload Release

The mission items were decoded one by one.

Mission item 10 contained:

```text
MAV_CMD_DO_SET_ACTUATOR
Command ID: 187
Actuator value: 1
```

The surrounding sequence was:

```text
Item 10 -> actuator = 1
Item 11 -> delay ≈ 2 seconds
Item 12 -> actuator = 0
```

This sequence behaves exactly like a servo or release mechanism:

```text
Enable actuator
      ↓
Hold
      ↓
Disable actuator
```

That strongly identifies mission item 10 as the payload-release trigger.

```text
Q9: 10
```

---

# 10. Intended Landing Position

The final navigation item contained:

```text
MAV_CMD_NAV_LAND
```

with coordinates:

```text
51.49970,-0.16080
```

Therefore:

```text
Q10: 51.49970,-0.16080
```

---

# 11. Drone Takeoff Location

The decrypted flight telemetry contained global-position messages.

The takeoff point was reconstructed from the first reliable flight-position samples:

```text
Latitude:  51.4996987
Longitude: -0.1607999
```

Therefore:

```text
Q11: 51.4996987,-0.1607999
```

---

# 12. Payload-Release Position

The mission event corresponding to item 10 occurred at approximately:

```text
446.656 seconds after boot
```

Correlating that timestamp with global-position telemetry gave:

```text
Latitude:  51.5035602
Longitude: -0.1608417
```

Therefore:

```text
Q12: 51.5035602,-0.1608417
```

---

# 13. Malicious MAVLink Command

Later in the flight, a suspicious MAVLink command appeared with command ID:

```text
420
```

Command 420 corresponds to:

```text
MAV_CMD_INJECT_FAILURE
```

This command is intended to inject a simulated failure into a vehicle subsystem.

In the context of this scenario, its unexpected appearance during the mission indicates sabotage.

The command was observed at approximately:

```text
520.764 seconds after boot
```

Therefore:

```text
Q13: MAV_CMD_INJECT_FAILURE
```

---

# 14. Distance Traveled After Payload Release

This question required careful interpretation.

The wording asks:

```text
How far did the drone travel?
```

Initially, measuring a direct line between the payload-release position and the injection position produced approximately:

```text
224 m
```

However, this is only displacement.

The actual flight path was curved.

To calculate the true distance traveled, the horizontal distance between every pair of consecutive GPS samples from:

```text
446.656 s
```

to:

```text
520.764 s
```

was calculated and summed.

Conceptually:

```text
distance =
d(P1,P2)
+ d(P2,P3)
+ d(P3,P4)
+ ...
+ d(Pn-1,Pn)
```

The total was approximately:

```text
276.71 metres
```

Rounded to the nearest whole metre:

```text
277
```

Therefore:

```text
Q14: 277
```

---

# 15. Identifying the Actual Crash Point

The end-of-log GPS location cannot automatically be treated as the crash site because PX4 may continue outputting estimated positions even after physical impact.

Instead, the vehicle acceleration data was inspected.

A very large acceleration spike occurred at approximately:

```text
525.860 seconds after boot
```

with magnitude around:

```text
562 m/s²
```

This spike is consistent with a hard impact.

The position around this timestamp was reconstructed from nearby global-position samples.

The resulting crash location was:

```text
51.5016938,-0.1620929
```

Therefore:

```text
Q15: 51.5016938,-0.1620929
```

This was an important correction.

The earlier value represented the later resting/end-of-log position rather than the actual impact point.

---

# 16. Drone Disarm Time

Arming-state telemetry was inspected after the crash.

The drone eventually changed to the disarmed state at:

```text
576.968 seconds after boot
```

Therefore:

```text
Q16: 576.968
```

---

# 17. Closest Road to the Crash Site

Using the corrected crash location:

```text
51.5016938,-0.1620929
```

the closest named road was identified as:

```text
Knightsbridge
```

Therefore:

```text
Q17: Knightsbridge
```

---

# Timeline Reconstruction

The full incident can be reconstructed from the mission and telemetry.

| Time after boot | Event |
|---:|---|
| Flight start | Drone departs from `51.4996987,-0.1607999` |
| `446.656 s` | Payload-release mission item activates |
| `446.656 s` | Drone is at `51.5035602,-0.1608417` |
| `446.656–520.764 s` | Drone travels approximately `276.71 m` |
| `520.764 s` | `MAV_CMD_INJECT_FAILURE` appears |
| ~`520.772 s` | Vehicle/motor failure effects begin |
| `525.860 s` | Major acceleration spike indicates impact |
| `525.860 s` | Crash location ≈ `51.5016938,-0.1620929` |
| `576.968 s` | Vehicle becomes disarmed |

---

# Mission Sequence

The most interesting part of the mission can be represented as:

```text
Mission Item 10
    |
    +-- MAV_CMD_DO_SET_ACTUATOR
    +-- actuator = 1
    |
    v

Mission Item 11
    |
    +-- delay ≈ 2 seconds
    |
    v

Mission Item 12
    |
    +-- actuator = 0
```

This is consistent with a payload-release sequence.

The mission eventually intended to terminate with:

```text
MAV_CMD_NAV_LAND
51.49970,-0.16080
```

---

# Flight Reconstruction

A simplified reconstruction of the route is:

```text
Takeoff
51.4996987,-0.1607999
        |
        v
Normal mission execution
        |
        v
Payload release
51.5035602,-0.1608417
        |
        | 277 m traveled
        v
MAV_CMD_INJECT_FAILURE
        |
        v
Flight instability / failure
        |
        v
Impact
51.5016938,-0.1620929
        |
        v
Knightsbridge
```

The intended mission endpoint was:

```text
51.49970,-0.16080
```

but the drone never completed the planned landing normally.

---

# Useful Analysis Techniques

## Header Inspection

A basic first step for encrypted or unknown files:

```bash
xxd -l 64 <filename>
```

or:

```bash
hexdump -C <filename> | head
```

This exposed the custom:

```text
PX4DMENC
```

header.

---

## Binary Analysis

Useful ELF inspection commands include:

```bash
file px4
readelf -h px4
readelf -S px4
readelf -s px4
strings -a px4
```

Disassembly can be inspected using:

```bash
objdump -d px4
```

For a stripped executable, following calls into recognizable crypto APIs is often more productive than searching for function names.

---

## Runtime Analysis

Dynamic analysis can be used when a binary contains a complicated custom derivation routine.

Typical workflow:

```text
find crypto/KDF call
        ↓
set breakpoint
        ↓
run supplied encrypted artifact
        ↓
inspect KDF input/output buffers
        ↓
recover final key material
```

This is useful when manually reimplementing a custom mixing routine would take significantly longer.

---

## ULog Analysis

Once the encrypted ULog was recovered, useful PX4 telemetry topics included:

```text
vehicle_global_position
vehicle_local_position
vehicle_acceleration
vehicle_status
vehicle_command
mission_result
```

These allowed the mission execution and crash to be correlated precisely.

---

## Path-Distance Calculation

The correct solution for Q14 required cumulative trajectory length rather than a single endpoint-to-endpoint calculation.

A typical Python approach is:

```python
total = 0

for current, nxt in consecutive_positions:
    total += horizontal_distance(current, nxt)
```

The result was:

```text
276.71 m
```

and therefore:

```text
277 m
```

---

# Important Investigation Pitfalls

## 1. Straight-line distance vs traveled distance

The first calculation gave approximately:

```text
224 m
```

but this represented only the direct separation between the release and injection coordinates.

The actual drone trajectory totaled:

```text
276.71 m
```

This distinction changed the final answer to:

```text
277
```

---

## 2. Final GPS location vs crash location

Using the last available GPS coordinate initially produced the wrong crash point.

The correct approach was to locate the impact from telemetry.

The acceleration spike at:

```text
525.860 s
```

identified the physical impact event.

The position at that timestamp produced:

```text
51.5016938,-0.1620929
```

---

## 3. Mission command context matters

A single actuator command might be ambiguous.

However, the sequence:

```text
actuator ON
delay
actuator OFF
```

strongly indicates an intentional payload-release operation.

---

# Key Findings

The core findings from Iron Feather were:

### Encryption

```text
Magic:
PX4DMENC

Encryption:
AES-256-GCM

Custom KDF RVA:
0x170af0

Mixing rounds:
384

Standard KDF:
PBKDF2-HMAC-SHA256
```

### AES Key

```text
a40ba87b8a0e21d4ead98b917c4bf0f60cc65b25c614b93f107e5ed1e483d6ce
```

### Mission

```text
Active bank: 0
Mission count: 24
Payload-release item: 10
```

### Flight

```text
Takeoff:
51.4996987,-0.1607999

Payload release:
51.5035602,-0.1608417

Intended landing:
51.49970,-0.16080
```

### Sabotage

```text
Injected command:
MAV_CMD_INJECT_FAILURE

Injection time:
520.764 s
```

### Crash

```text
Distance traveled after release:
277 m

Impact time:
525.860 s

Crash:
51.5016938,-0.1620929

Disarmed:
576.968 s

Closest road:
Knightsbridge
```

---

# Final Answers

```text
1. PX4DMENC

2. AES-256-GCM

3. 0x170af0

4. 384

5. PBKDF2-HMAC-SHA256

6. a40ba87b8a0e21d4ead98b917c4bf0f60cc65b25c614b93f107e5ed1e483d6ce

7. 0

8. 24

9. 10

10. 51.49970,-0.16080

11. 51.4996987,-0.1607999

12. 51.5035602,-0.1608417

13. MAV_CMD_INJECT_FAILURE

14. 277

15. 51.5016938,-0.1620929

16. 576.968

17. Knightsbridge
```

---

# Lessons Learned

Iron Feather demonstrates how different forensic disciplines often overlap.

Some of the main lessons from the challenge were:

- File headers can reveal useful information even when the payload is encrypted.
- Stripped binaries can still be reverse engineered by tracing library calls and data flow.
- Dynamic analysis can be significantly faster than fully reproducing a custom KDF.
- Authenticated encryption provides a useful correctness check because an incorrect key will fail authentication.
- PX4 mission data becomes much easier to interpret once MAVLink command IDs are decoded.
- Mission context is just as important as individual command values.
- A flight's actual traveled distance must be calculated from its complete path rather than endpoint displacement.
- The final telemetry coordinate is not necessarily the physical crash location.
- Acceleration data is extremely valuable for identifying impact timestamps.
- Correlating several telemetry topics gives much stronger conclusions than relying on one source alone.

---

# Conclusion

Iron Feather begins as a cryptographic reverse-engineering challenge but gradually turns into a complete drone-forensics investigation.

The encrypted datastore was identified through its `PX4DMENC` signature and found to use `AES-256-GCM`. Reverse engineering exposed a custom 384-round mixing routine followed by `PBKDF2-HMAC-SHA256`, ultimately allowing recovery of the AES key.

Once decrypted, the mission data showed a 24-item mission stored in bank 0. Mission item 10 activated an actuator, waited approximately two seconds, and then disabled it, identifying the payload-release mechanism.

The flight telemetry then revealed a later `MAV_CMD_INJECT_FAILURE` event. From the payload release to this command, the drone traveled approximately 277 metres.

A large acceleration spike approximately five seconds later identified the actual physical impact. Correlating this event with global-position telemetry placed the crash at:

```text
51.5016938,-0.1620929
```

near Knightsbridge.

The resulting sequence of events was therefore:

```text
Encrypted mission recovered
        ↓
Mission executed
        ↓
Payload released
        ↓
MAV_CMD_INJECT_FAILURE received
        ↓
Vehicle loses controlled flight
        ↓
Impact
        ↓
Drone eventually disarms
```

This combination of reverse engineering, cryptography, PX4 internals, MAVLink analysis, and telemetry reconstruction made Iron Feather one of the more technically varied challenges in the scenario set.