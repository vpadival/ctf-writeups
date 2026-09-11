# Byte Lotus — Write-Up

**Challenge:** Concierge Briefing (Byte Lotus)  
**Category:** Web  
**Difficulty:** Very Easy  
**Points:** 30  
**Event:** TryHackMe — Hacker Holidays  
**Platform:** https://tryhackme.com/hackerholidays

---

## About This Challenge

This is a beginner-level web exploitation challenge from **TryHackMe's Hacker Holidays** event. It's designed as an introductory CTF that demonstrates the real-world risks of deploying staging/development environments with version control systems exposed.

---

## Challenge Overview

In this challenge, we're tasked with gaining access to the "Byte Lotus" guest experience platform—a hotel management system deployed hastily to a staging environment. The scenario is that a "night-shift developer shipped more than the website," suggesting that development artifacts have been accidentally exposed to production.

**Objectives:**
1. Dump the exposed source code
2. Find the flag

---

## Reconnaissance

### Initial Reconnaissance

Starting with basic HTTP enumeration:

```bash
curl http://10.114.162.138:8080/
```

The landing page is a sleek hospitality platform homepage with styling and marketing copy. However, the footer contains a critical hint:

```
guest experience platform · build staging
```

The mention of "build staging" immediately signals that this is a staging deployment, likely with development artifacts left exposed.

### Directory Enumeration

Given the briefing's hint about port 8080 being "wide open," the first place to check for common development exposures is the `.git/` directory:

```bash
curl http://10.114.162.138:8080/.git/
```

**Result:** Directory listing is exposed!

```
Index of /.git/

- COMMIT_EDITMSG
- HEAD
- branches/
- config
- description
- hooks/
- index
- info/
- logs/
- objects/
- refs/
```

This is a critical finding. The `.git` directory contains the entire version control history of the application and is rarely meant to be exposed publicly.

---

## Exploitation

### Extracting the Repository

While the `.git/` directory is browsable, it's not configured as a proper Git remote, so a standard `git clone` won't work:

```bash
git clone http://10.114.162.138:8080/.git/ byte-lotus
# fatal: repository not found
```

Instead, we use **git-dumper**, a specialized tool designed to extract Git repositories from exposed `.git/` directories:

```bash
pip install git-dumper
git-dumper http://10.114.162.138:8080/.git/ byte-lotus
```

This tool recursively downloads all Git objects and reconstructs the repository history locally.

### Analyzing the Extracted Files

Once extracted, we have access to three key files:

**1. `app.js` — Front-end stub**

```javascript
// Byte Lotus guest app — front-end stub
// concierge personalization is served from the profiling service.
const API = "/api/guest";
async function greet() {
  // TODO: wire to live endpoint before launch
  console.log("welcome back. your usual?");
}
greet();
```

This reveals:
- A front-end stub, not fully wired to backend
- An API endpoint at `/api/guest` for profiling
- A TODO comment indicating unfinished development (reinforces the "night-shift" narrative)

**2. `index.html` — Landing page**

The HTML source matches what we saw in the browser. No flag or secrets here, but confirms the structure.

**3. `README.md` — THE FLAG**

```markdown
# Byte Lotus — Guest Experience Platform

Internal staging repository for the guest app and concierge personalization
service. Do not deploy this folder to production.

Staging flag (remove before launch): THM{byt3_l0tus_n3v3r_f0rg3ts}
```

---

## Flag

```
THM{byt3_l0tus_n3v3r_f0rg3ts}
```

---

## Key Findings

### Vulnerability: Exposed `.git/` Directory

**Severity:** Critical  
**CWE:** CWE-215 (Information Exposure Through Debug Information)

The entire `.git/` directory is publicly accessible and browsable. This allows attackers to:
- Reconstruct the full source code history
- Identify development branches, commits, and contributors
- Extract credentials and API keys from commit history
- Understand the application architecture and potential vulnerabilities

### Root Cause

The application was deployed to production with:
1. The `.git/` directory included in the web root
2. Staging flags and sensitive comments left in source files
3. No `.gitignore` to prevent committing sensitive data
4. No deployment checklist enforced

### Secondary Finding: Staging Artifacts in Production

The `README.md` explicitly states:
```
Internal staging repository for the guest app and concierge personalization
service. Do not deploy this folder to production.

Staging flag (remove before launch):
```

This indicates the developer knew this was staging code but failed to strip it during deployment.

---

## Remediation

### Immediate Actions

1. **Remove `.git/` from production**
   - Ensure `.git/` is not included in deployment artifacts
   - Add `.git/` to `.gitignore` or deployment exclusion rules

2. **Rotate all exposed credentials**
   - Any API keys, secrets, or passwords in the repository should be considered compromised
   - Implement secrets management (e.g., HashiCorp Vault, AWS Secrets Manager)

3. **Audit commit history**
   - Review all commits for hardcoded credentials or sensitive data
   - Use tools like `truffleHog` or `git-secrets` to scan history

4. **Remove staging artifacts**
   - Strip staging-specific code, comments, and flags before deploying to production
   - Use environment-based configuration for such data

### Long-term Practices

1. **Deployment Pipeline**
   - Implement automated build/deployment checks
   - Use `.gitignore` to prevent committing secrets
   - Enforce a deployment checklist

2. **Secrets Management**
   - Never commit secrets to Git
   - Use environment variables or external secret stores
   - Rotate credentials regularly

3. **Security Scanning**
   - Integrate SAST (Static Application Security Testing) into CI/CD
   - Scan for exposed credentials before deployment
   - Regular security audits of deployed code

4. **Developer Training**
   - Educate developers on secure deployment practices
   - Code review processes to catch accidental exposures
   - Use pre-commit hooks to prevent committing secrets

---

## Lessons Learned

This challenge perfectly illustrates the danger of deploying staging environments to production without proper sanitization. Key takeaways:

1. **Version control hygiene matters:** A single exposed `.git/` directory gave us complete access to the application source and secrets.

2. **Staging flags are not security:** Comments like "remove before launch" are reminders, not barriers. Enforcement mechanisms are needed.

3. **Web server configuration:** The `.git/` directory should never be served by a web server. Use `.htaccess` (Apache) or other configuration to block it:
   ```apache
   <Directories .git>
       Order allow,deny
       Deny from all
   </Directories>
   ```
   Or in nginx:
   ```nginx
   location ~ /\.git {
       deny all;
   }
   ```

4. **Defense in depth:** Even if `.git/` were blocked, storing secrets in the repository is still problematic. Multiple layers of security are needed.

---

## Tools Used

- **curl** — HTTP client for reconnaissance
- **git-dumper** — Tool to extract Git repositories from exposed `.git/` directories
- **git** — Version control system

---

## Timeline

| Step | Action | Result |
|------|--------|--------|
| 1 | Fetch landing page | Identified staging deployment hint |
| 2 | Enumerate `.git/` | Confirmed directory is accessible and browsable |
| 3 | Extract repository | Used git-dumper to download all files |
| 4 | Analyze source | Reviewed `app.js`, `index.html`, `README.md` |
| 5 | Find flag | Discovered staging flag in `README.md` |

---

## Flag Submission

```
THM{byt3_l0tus_n3v3r_f0rg3ts}
```

**Challenge Status:** ✓ Complete
