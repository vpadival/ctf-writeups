# TryHackMe Hacker Holidays 2026 — Towel on the Sunbed

**Category:** Web
**Difficulty:** Medium
**Points:** 90
**Flag:** `THM{t0w3l_0n_th3_sunb3d_d0ubl3_sp3nt}`

## Challenge Brief

The Byte Lotus Hotel's wellness portal runs **Ponzi**, a poolside crypto rewards app. Guests can claim a daily staking reward, gated by a 24-hour cooldown. The goal: reach **150 PONZI** to unlock the Whale Vault and grab the flag, despite the app only allowing one claim per day.

The room description hinted directly at the bug class:

> *"Somewhere between his request and the server's clock, there's a gap wide enough to walk a whale through."*

That's a classic **race condition** — specifically a **time-of-check to time-of-use (TOCTOU)** flaw in the claim endpoint.

## Recon

Registering a guest account and exploring the dashboard revealed:

- `GET /dashboard/api/me` — returns account state:
  ```json
  {
    "id": 4,
    "username": "srikanth",
    "balance": 0,
    "tier": "Shrimp",
    "whaleThreshold": 150,
    "canClaim": true,
    "secondsUntilClaim": 0
  }
  ```
- `POST /claim` — claims the daily reward. First call for a fresh account:
  ```json
  {
    "message": "Staking reward claimed successfully.",
    "reward": 50,
    "newBalance": 50,
    "tier": "Shrimp",
    "priceSnapshot": 4.2
  }
  ```
- A second call immediately after returns `429`:
  ```json
  {
    "error": "Reward already claimed. Please wait before claiming again.",
    "secondsRemaining": 86400
  }
  ```

So each claim awards a flat 50 PONZI, and reaching 150 legitimately would take three real days. The cooldown is clearly enforced server-side — but *how* it's enforced is what makes it exploitable.

## Attempt 1: Concurrent Requests via `aiohttp`

The first approach fired 40–80 concurrent `POST /claim` requests using Python's `asyncio` + `aiohttp` against a single account, hoping several requests would pass the "already claimed?" check before any of them wrote the updated timestamp.

Result on a fresh, never-claimed account: **only 1 out of 80 requests succeeded.** The rest received `429`.

This showed the server does have *some* separation between the check and the write — but plain `aiohttp.gather()` wasn't tight enough to exploit it. Each request still pays for its own TCP connection setup and TLS/socket negotiation, which staggers arrival times at the server just enough for Node's event loop to process each check-then-write as an atomic unit before the next request lands.

## Attempt 2: Pre-Established Raw Sockets

To close that timing gap, the approach shifted to a custom Python script built directly on the `socket` module instead of a higher-level HTTP client:

1. Open **all** TCP connections to the target **first**, and let them sit idle, fully connected.
2. Only once every socket is ready, loop through and `send()` the raw HTTP request bytes to each one back-to-back, with no connection-setup latency in between.
3. Read all responses afterward.

The idea: since connection setup was the source of the timing jitter in Attempt 1, doing all of that setup work upfront — before sending a single byte of the actual request — means the only remaining variance is the tight `sendall()` loop itself.

```python
def open_sockets(n):
    socks = []
    for _ in range(n):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        socks.append(s)
    return socks

def fire_all(socks):
    for s in socks:
        s.sendall(REQUEST)
```

By pre-connecting before firing, the only remaining gap between requests is a handful of `sendall()` syscalls in a tight loop — microseconds apart rather than the tens-of-milliseconds of connection setup.

## Result

Running the raw-socket burst against a fresh account with 60 pre-established connections:

```
Total 200 OK responses: 60 / 60
```

Every single request landed as a successful claim. The account's balance shot from 0 to 3000 PONZI (60 × 50), and the `tier` field flipped to `"Whale"` in the response body — confirming the check-then-write race had been fully won.

Heading to the dashboard and clicking **Open Vault** unlocked the Whale Vault and revealed the flag:

```
THM{t0w3l_0n_th3_sunb3d_d0ubl3_sp3nt}
```

## Root Cause

The `/claim` endpoint almost certainly implements the cooldown check like this:

```js
// pseudocode of the vulnerable logic
if (user.lastClaimed + ONE_DAY < Date.now()) {
  user.balance += REWARD;
  user.lastClaimed = Date.now();
  await saveUser(user);   // <-- gap here if this is async
}
```

If the read of `user.lastClaimed`, the balance update, and the persisted write aren't wrapped in a single atomic operation (e.g., a database transaction with row-level locking, or an atomic conditional update), then multiple requests arriving close enough together can all read the "not yet claimed" state before any of them commits their write. Each one independently decides it's allowed to claim, and all of them succeed.

This is a **TOCTOU race condition**, a very common class of bug in reward systems, rate limiters, and financial logic where "check eligibility, then act" isn't performed as one atomic unit.

## Remediation

- Wrap the check-and-update in a **database transaction** with row-level locking (`SELECT ... FOR UPDATE`), so concurrent transactions serialize on the same row.
- Alternatively, use an **atomic conditional update** — e.g., `UPDATE users SET balance = balance + 50, last_claimed = NOW() WHERE id = ? AND last_claimed < NOW() - INTERVAL '24 hours'` — and check the affected-row count to determine success, rather than doing a separate read followed by a write.
- Rate-limit by unique claim attempts per user at the infrastructure level (e.g., a distributed lock via Redis `SETNX`) as defense in depth.

## Tools & Techniques Used

- Browser DevTools (Network tab) for endpoint discovery and session cookie capture
- Python `asyncio` + `aiohttp` for initial concurrent-request testing
- A custom Python script using the raw `socket` module to pre-establish connections and fire requests in a tight loop
- Manual account creation to reset the claim state between attempts

## Key Takeaway

Naive concurrent HTTP client libraries aren't always concurrent enough to win a tight race condition — connection setup overhead can serialize requests that were "fired at the same time" from the client's perspective. Pre-establishing raw TCP connections and sending the request bytes in a tight loop closes that gap and is often necessary to actually land a race on a narrow server-side window.
