# Hacker Holidays: The Byte Lotus Resort - Write-up

**Challenge**: The Byte Lotus Hotel  
**Event**: TryHackMe Hacker Holidays  
**Category**: OSINT  
**Difficulty**: Easy  
**Platform**: [TryHackMe](https://tryhackme.com/hackerholidays)  

---

## About This Challenge

This challenge is part of **TryHackMe's Hacker Holidays** event—a seasonal CTF featuring themed security challenges across multiple categories. Hacker Holidays combines festive storytelling with legitimate penetration testing and OSINT techniques, making it an ideal introduction to cybersecurity for beginners while offering depth for experienced players.

**Event Theme**: Holiday-themed challenges disguised as resort/travel scenarios  
**Room Link**: https://tryhackme.com/hackerholidays

---

## Challenge Summary

> *"A polished first impression can still leave a trail."*

The challenge presents a luxury resort brochure with a suspicious AI-generated hero image. Players must follow the digital breadcrumb trail to locate a hidden social media account and extract the flag from encoded posts.

**Objective**: Analyze the brochure, trace the OSINT clues, locate the hidden Instagram account, and submit the flag.

---

## Initial Reconnaissance

### The Brochure Analysis

The provided brochure (`thebrochure.png`) contains several deliberate clues:

1. **AI Fingerprint** - The resort building is algorithmically generated
   - Inconsistent architectural details
   - Perfectly symmetrical composition
   - Unrealistic lighting/reflection artifacts
   - This screams "reverse image search me"

2. **Text Clues**
   - `"A polished first impression can still leave a trail."` — meta hint about social media footprints
   - `"Some things aren't posted. Some clues are. Find us on Instagram or not."` — vague Instagram reference
   - **VERA the Concierge** — named contact point, likely a username
   - `"LUXURY. SIGNALS. SECRETS."` — keyword pattern for searches

3. **Date Anchor**
   - `MON JUL 27` — establishes a timeline for when content was posted

### Initial Hypothesis

The challenge description states the account "leads somewhere the hotel never intended you to look." This suggests:
- An official resort account exists (`@thebytelotusresort`)
- But the **real flag** is hidden in a secondary account (`@veratheconcierge`)
- The concierge account was created as an OPSEC failure by the hotel

---

## Reconnaissance Phase

### Step 1: Identify the Instagram Account

**Approach**: Social media enumeration based on challenge clues

**Search Queries Tested**:
- `bytelotus` + variations → Too generic
- `vera` + `resort` → Promising
- `veratheconcierge` → **BINGO**

**Result**: Located two Instagram accounts:
- `@thebytelotusresort` (official resort account)
- `@veratheconcierge` (Concierge VERA's personal account)

The official account is a decoy. VERA's account contains the actual payload.

---

## Exploitation

### Step 2: Extract Encoded Flag Segments

**Account Profile**: `@veratheconcierge`
- 2 posts
- 272 followers
- 1 following
- Bio: "The Byte Lotus Resort"

**Post Analysis**:

The challenge elegantly splits the flag across **three separate posts**, each containing a base64-encoded string:

| Post | URL | Payload | Decoded |
|------|-----|---------|---------|
| Part 1 | `/p/Da0r1YxkfCo/` | `VEhNe1YzckBzX2FD` | `THM{V3r@s_aC` |
| Part 2 | `/p/Da0rtcoEe8R/` | `QzB1bnRfaDRzX2Iz` | `C0unt_h4s_b3` |
| Part 3 | `/p/Da0rjiJkTjN/` | `M25fZjB1bmQhfQ==` | `3n_f0und!}` |

**Decoding Command**:
```bash
echo "VEhNe1YzckBzX2FD" | base64 -d
echo "QzB1bnRfaDRzX2Iz" | base64 -d
echo "M25fZjB1bmQhfQ==" | base64 -d
```

**Output**:
```
THM{V3r@s_aCc0unt_h4s_b33n_f0und!}
```

---

## Flag

```
THM{V3r@s_aCc0unt_h4s_b33n_f0und!}
```

---

## Key Techniques Used

### 1. **Image Analysis**
   - Identified AI-generated content by visual artifacts
   - Recognized asymmetrical perfection as ML fingerprint

### 2. **Social Media Enumeration**
   - Username derivation from challenge text (VERA → veratheconcierge)
   - Differentiation between official and secondary accounts
   - Post timeline analysis (three consecutive posts)

### 3. **Data Extraction & Decoding**
   - Base64 decoding (standard encoding for CTF challenges)
   - Fragment reassembly across multiple sources

### 4. **OPSEC Failure Recognition**
   - Employees leaving personal social accounts linked to company operations
   - Unencrypted/public credential storage in account bios/posts
   - Lack of access controls on account listings

---

## Challenge Design Notes

**Why This Challenge Works**:
- **Low barrier to entry**: Only requires Instagram access, no specialized tools
- **Clear breadcrumb trail**: Brochure → Instagram account → Three posts → Flag
- **Realistic scenario**: Employee social media is a genuine OSINT vector
- **Elegant obfuscation**: Flag split across posts (makes screenshot/scraping less obvious)

**Thematic Consistency**:
- The challenge tagline ("polished first impression can still leave a trail") perfectly captures digital footprints
- VERA as the weak link reflects real corporate OPSEC failures
- The luxury resort aesthetic masks hacker culture (meta-layer)

---

## Tools & Resources

- **Manual Reconnaissance**: Instagram.com (direct browser)
- **Decoding**: `base64` (Linux/macOS built-in)
- **Alternative Tools**:
  - `echo` + pipe for quick decoding
  - CyberChef for GUI-based base64 decoding
  - TinEye/Google Images for reverse image search (if needed)

---

## Lessons Learned

1. **Social Media is OSINT Gold**
   - Employee accounts often leak company information
   - Secondary/personal accounts lack security hardening of official channels
   - Post metadata (timestamps, location tags) can be forensically valuable

2. **Encoding ≠ Encryption**
   - Base64 is obfuscation for transport, not security
   - Easy to decode with built-in tools
   - Always suspect encoded strings in CTF contexts

3. **Brochure Analysis Matters**
   - Marketing materials often contain unintended clues
   - AI-generated content has consistent fingerprints worth reverse searching
   - Flavor text in challenges is rarely random

4. **Fragmentation Strategy**
   - Splitting data across multiple posts makes correlation harder
   - Requires assembling context from timeline browsing
   - Mirrors real-world intelligence gathering (piecing disparate sources)

---

## Timeline

- **Reconnaissance**: Brochure analysis → Account discovery (~2 min)
- **Exploitation**: Post extraction + base64 decoding (~1 min)
- **Flag submission**: Instant

**Total Time**: ~5 minutes (Easy difficulty confirmed)

---

## Conclusion

A masterfully simple OSINT challenge that weaponizes the combination of:
- AI image forensics (basic visual analysis)
- Social engineering psychology (employee account targeting)
- Data exfiltration (encoded posts)

The real vulnerability wasn't technical—it was human. VERA left the hotel's secrets in plain sight, one post at a time.

**Status**: ✅ **PWNED**

```
THM{V3r@s_aCc0unt_h4s_b33n_f0und!}
```

---

## TryHackMe Context

**Hacker Holidays** is TryHackMe's seasonal event featuring thematic OSINT and reconnaissance challenges. This challenge exemplifies the platform's approach to:

- **Accessible Security Education**: No specialized tools required (browser + base64 decoder)
- **Real-World Application**: Employee OPSEC failures are genuine attack vectors
- **Gamified Learning**: Thematic presentation (luxury resort) increases engagement
- **Progressive Difficulty**: Starts easy for onboarding, allows skill scaling within event

**Recommended Follow-ups**:
- Explore other Hacker Holidays challenges for similar OSINT patterns
- Study social media reconnaissance techniques in TryHackMe's OSINT room
- Practice AI image forensics on other brochure-style materials

**Community Note**: This challenge rewards careful observation and lateral thinking over technical complexity—core OSINT competencies for real-world investigations.

---

## Submitting on TryHackMe

1. Navigate to the challenge room on TryHackMe
2. Locate the answer submission box
3. Enter the flag exactly as shown: `THM{V3r@s_aCc0unt_h4s_b33n_f0und!}`
4. Click "Submit" to confirm

---

## What's Next?

The Byte Lotus Hotel is one challenge in the **Hacker Holidays** event series. Other challenges may include:
- Web exploitation (similar resort/travel themes)
- Cryptography challenges
- Steganography puzzles
- Network analysis

Each challenge follows a similar themed narrative while teaching different security concepts. This OSINT challenge emphasizes reconnaissance and social engineering—critical first steps in any penetration test.
