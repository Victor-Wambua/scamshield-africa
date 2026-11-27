# ScamShield Africa: product brief

Status: design phase. Everything in this package is a design deliverable. No backend exists. All demo data is synthetic demonstration data.

## 1. Product in one paragraph
An independent fraud-intelligence network, starting in Kenya. People check a phone number, link, email, payment reference or wallet before they pay; report what they saw; and institutions use the same intelligence to investigate campaigns. It records **reports about indicators**, not accusations about people. Every record shows how many independent people reported it, what evidence exists, and whether a moderator verified it.

## 2. Target users
| Group | Context | What they need |
|---|---|---|
| Ordinary consumers, mobile-money users | Android phone, mobile data, low data allowance, often Kiswahili/English mix, little patience for jargon | Fast answer to "is this safe?", plain words, a report flow that takes under 3 minutes |
| Small businesses | Impersonated by fake sellers, fake invoices | Check suppliers; ask for a correction when their name is misused |
| Banks, fintechs, telcos | Fraud desks, customer care | Campaign view, CSV export, API, case notes, alerts |
| NGOs, researchers, security professionals | Trend study, awareness | Aggregates with privacy thresholds, threat categories |
| Moderators | Review queue all day | Evidence, duplicate signals, one-click compliant decisions |
| Platform admins | Governance | Users, roles, audit |

Roles: Visitor, Registered reporter, Verified contributor, Moderator, Organization analyst, Organization administrator, Platform administrator.

## 3. Problems
1. People cannot quickly tell whether a number or link has been reported, and "no result" is misread as "safe".
2. Reporting is scattered (carrier short codes, social media, police) and gives no feedback.
3. Public blacklists risk defamation and wrongful labelling; mistakes are hard to correct.
4. One noisy reporter can inflate a record; institutions cannot see which reports are independent.
5. Institutions lack a shared, privacy-respecting view of campaigns.

## 4. UX objectives
- Check in under 10 seconds from opening the app; report in under 3 minutes on a 3G-class connection.
- "Not reported does not mean safe" on every empty result.
- Every status, count and confidence has a "why". AI output is never presented as proof.
- Wording rule: indicators are "reported", "unverified", "verified with evidence". Never "criminal" or "scammer" about a named person.
- A correction path on every record. Audit trail on every moderation action.
- Mobile-first public side; staff tools usable on tablet; WCAG 2.2 AA target; English with Kiswahili-ready copy keys.

## 5. Evidence base and verification (honest outcome)
I attempted to read both primary pages. **Neither could be read directly.**

| Source | Result of fetching | What I can and cannot say |
|---|---|---|
| Communications Authority of Kenya, "CA resolves 82 per cent ICT consumer complaints..." (ca.go.ke) | WebFetch and a plain HTTP request both returned a bot-verification challenge page, not the article. I did not bypass it. A second URL, the CA's own "Consumer Complaints Statistics for Q4 FY 2025-2026" document, returned the same challenge. | **Primary page not verified.** Search-engine summaries of CA's disclosures (secondary: TechCabal, Nation, as relayed by a search tool, pages not opened by me) report: 670 escalated complaints April-June 2026 (up from 563 the previous quarter), 548 resolved (82%), 110 digital financial services / mobile money, 75 cybercrime (43 of them social media), telecommunications 239. These agree with the brief's 670 / 110 / 75. |
| INTERPOL, "African Cyberthreat Assessment 2026" news item | HTTP 403 from WebFetch; plain request returned an access-denied page. | **Primary page not verified.** A trade-press article I did open (Help Net Security, 2026-08-05) reports $484 million reported losses in 2025 (up from $192 million), victims 35,000 to 87,000, and does not itself state an AI share. Search summaries of INTERPOL coverage give "about 55%" AI-linked. The brief only said "more than half", which is consistent, but I could not confirm the percentage from INTERPOL. |

**Mismatch / ambiguity notes**
- CA "86" fraud-and-scams figure: secondary sources disagree on whether it is inside the 110 DFS category (TechCabal) or a separate category (Nation). The design does not use it.
- Survey size in the INTERPOL report: coverage says 36 member countries in most outlets and 26 in one. Not used in the design.
- No figure from this section appears as a stat in the UI. All dashboard numbers are labelled synthetic.

## 6. Competitor and adjacent-service scan
Pages I actually opened (this session): ScamAdviser home, Google Safe Browsing home. Items marked "snippet" come only from search-result summaries and were not opened; Truecaller's site refused the fetch.

| Service | Evidence | Strength | Gap ScamShield addresses |
|---|---|---|---|
| ScamAdviser (opened) | Free URL checker; community "Trust Guardians" reports with comments; screenshot "Lens" tool; no phone lookup on the home page | Familiar URL check | The page I read did not describe how reports are verified or labelled; focuses on websites, not Kenyan numbers or payment references |
| Google Safe Browsing (opened) | Warns users in Chrome, Search, Gmail, Android; public Site Status lookup; free API; report malware/phishing | Huge reach for URLs | Not designed for phone numbers, till numbers or messages; no independent-report counts or case tools for local institutions |
| Truecaller (snippet, via Techweez 2015/2017 reports) | Kenyan users reportedly flag many spam calls daily; most flagged calls from individuals (2017 figure) | Caller ID at scale | Not opened. Closed app; labels can follow a number without evidence or correction path |
| ScamWarners and similar volunteer lookup sites (snippet) | Per-number pages built from member reports | Community knowledge | Evidence quality and correction rights unclear |
| Carrier reporting (snippet): Safaricom 333 and 456; Airtel Kenya dial *100# then Report Fraud | Existing in-network reporting channels | Direct to the operator | No public feedback, no shared intelligence across operators, no status tracking |

Not verified and therefore not claimed: ScamAdviser phone coverage, Scamwatch, PhishTank, any Kenyan-government reporting portal.

## 7. Differentiation
1. **Independent-report counting**: repeat submissions by one person are linked and counted once; visible in the UI.
2. **Evidence-graded status** (reported / unverified / verified with evidence), never a binary "scam" flag.
3. **Correction and challenge on every record** with a different moderator, plus legal removal.
4. **Explainable analysis** with confidence level and reasons; never proof.
5. **Institution tools on the same data**: campaigns, cases, CSV, API, alerts, with small-number suppression.
6. **Designed for Android on mobile data**: small payloads, saved drafts, plain language, Kiswahili-ready.

## 8. Legal and risk considerations (design inputs, not legal advice or a compliance claim)
I could not read the Kenya Office of the Data Protection Commissioner site (bot challenge) or the Act text, so the following are design assumptions for counsel to confirm.
- **Kenya Data Protection Act 2019**: assume phone numbers, emails and reports can be personal data. Design responds with data minimisation (publish indicator + status, never reporter identity), explicit consent and notice at submission, purpose limitation, retention rules, access/correction/deletion paths, restricted evidence access, audit logs, and a data-protection impact assessment before launch. Registration as a data controller/processor and cross-border transfer rules need counsel.
- **Defamation and accuracy**: a number may belong to an innocent person (SIM recycling, spoofing, impersonation). Mitigations: neutral wording, status ladder, no names, visible "not proof" language, fast correction, takedown for inaccurate or unlawful data, documented moderation policy, moderator reasons logged.
- **Evidence handling**: screenshots may contain third-party personal data; redaction prompt, access limited to moderators/approved partners, retention limits.
- **Abuse**: false reports as harassment or competitor attacks; independent-count rule, reporter trust signals, restriction workflow.
- **Partner data sharing**: only approved organisations, agreements, tenant isolation.
- **AI**: explanation and confidence required; no decisions about individuals from AI alone.

## 9. Data availability (what the real product could use)
| Data | Source | Status |
|---|---|---|
| User reports, evidence | The product itself | Available from day one; cold-start problem |
| Partner telco/bank indicators | Agreements | Not available; needs partnerships |
| URL reputation | Public lists or APIs (for example Safe Browsing API terms) | Needs terms review; not integrated in design |
| Blockchain public data | Public explorers | Possible later; wallet checks simulated in the prototype |
| Official statistics (CA, INTERPOL) | Publishers | Primary pages blocked for me; cite only after a human confirms |
| Geographic data | County level from reports | Subject to suppression below 5 |
