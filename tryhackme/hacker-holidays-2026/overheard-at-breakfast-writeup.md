# Overheard at Breakfast — TryHackMe Writeup

**Category:** OSINT
**Difficulty:** Easy
**Points:** 60
**Room:** [Overheard at Breakfast](https://tryhackme.com/room/hh-overheardatbreakfast-6f01793c)

## Briefing

> The breakfast terrace is loud this morning — clinking cutlery, espresso machines, the usual chatter. One guest couldn't help but linger at a nearby table, seeing more of a conversation than they were meant to. When the table's occupant stepped away for a refill, they seized the moment and grabbed a screenshot before it could disappear. Somewhere in that conversation is enough to track down an account nobody was supposed to find.

The task: analyze a leaked Discord conversation, extract the identifying details, and use them to locate a hidden account.

## The Evidence

The provided task file was a zipped screenshot (`conversation.png`) of a Discord exchange between two users, `Ponzi – Influencer [L3AK]` and `Lambo!`:

```
Ponzi – Influencer [L3AK] (10:53 PM)
Hey @Lambo!

Lambo! (10:53 PM)
Hi Ponzi! How are things going on your end? :)

Ponzi – Influencer [L3AK] (10:54 PM)
doing well thanks for asking, enjoying the resort so far?

Lambo! (10:55 PM)
Absolutely, Byte Lotus is treating me nice, love the food, weather and overall vibes.
Will probably come back next year too.

Ponzi – Influencer [L3AK] (10:57 PM)
love to hear it!!! so i've been posting so much on social media and helping
customers around. i never ended up getting your handle, so that i could
possibly tag you next time.

Lambo! (11:00 PM)
Great to hear, I've been seeing those awesome posts. Yeah nowadays I don't
really use much social media...

Though I'm still out there, I used to use this free tool that let me upload
my profile and link other media accounts, was neat, until I wiped everything.
Started with a G if I remember correctly.

But if anything this is my best way of communication:
lambobytelotushotel@gmail.com

Ponzi – Influencer [L3AK] (11:03 PM)
woah woah, seems very secretive! maybe for the better that you don't use
social media, heard some strange things have been happening in Byte Lotus.
thanks regardless I will be in touch with you.
btw one more thing, going out to breakfast tomorrow morning?

Lambo! (11:03 PM)
Yeah sounds dope, will be there you know me😎!
```

Two things stood out immediately:

1. A **free tool starting with "G"** that lets users upload a profile picture and link other social/media accounts.
2. A **specific email address** — `lambobytelotushotel@gmail.com` — offered up as Lambo's "best way of communication."

## Identifying the Tool

The description — a free service for a unified profile picture that also links out to other accounts — is a strong match for **Gravatar** ("Globally Recognized Avatar"), a service by Automattic. Gravatar doesn't tie a profile to a username; it ties a profile to a **hash of an email address**. Once you know the email, you effectively know the profile URL.

## Resolving the Profile

Gravatar profile/avatar URLs are built from a hash of the (trimmed, lowercased) email address:

- **Legacy avatar endpoint:** MD5 of the email
- **Current profile API:** SHA-256 of the email

```bash
echo -n "lambobytelotushotel@gmail.com" | md5sum
# d4a5fc5d3128890778667e24617d7cc0

echo -n "lambobytelotushotel@gmail.com" | sha256sum
# d43faafe9d7f056793bd037b8d6e321acad985c222d83775b10d6539e301e931
```

Rather than guessing at the exact endpoint format, I used Gravatar's own email-lookup flow with the address from the chat, which resolved directly to Lambo's public profile:

```
https://gravatar.com/cheerfullysongf28e3c3716
```

## The Flag

Lambo's Gravatar bio contained a taunting note and a base64-encoded string:

> "Funny thing about email hashes, they follow you places you didn't expect. Glad you found the right corner of the internet! Here is your prize: `VEhNe1MzY3JlVF9QcjBmaWwzX0g0c19iMzNuX0lkZW50MWZpM2R9`"

Decoding it:

```bash
echo "VEhNe1MzY3JlVF9QcjBmaWwzX0g0c19iMzNuX0lkZW50MWZpM2R9" | base64 -d
```

```
THM{S3creT_Pr0fil3_H4s_b33n_Ident1fi3d}
```

## Flag

```
THM{S3creT_Pr0fil3_H4s_b33n_Ident1fi3d}
```

## Takeaways

- **Email-derived identifiers are not anonymous.** Any hash-based lookup service (Gravatar being the classic example) turns "just an email address" into a direct pointer at a public profile — same input, same hash, every time.
- **Casual chat leaks matter.** Lambo thought sharing an email was more discreet than a social handle, but the email itself was the real de-anonymizing artifact.
- **Read secondary clues carefully.** The "started with a G" hint wasn't filler — it was the key that turned a random email address into an actionable lead.
