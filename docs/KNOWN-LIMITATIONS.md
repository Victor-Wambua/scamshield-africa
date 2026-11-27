# Known limitations

- Analysis engine is keyword/regex plus MinHash: novel wording, images and voice are missed; English/Swahili only; evaluation data is synthetic and author-written (see EVALUATION.md).
- No live email, SMS or WhatsApp; no real LLM; no national or telco data; all are outstanding external dependencies.
- PostgreSQL and Docker paths unexecuted. GitHub Actions unexecuted.
- No screen-reader or user testing; Swahili needs native review; legal review outstanding.
- Geographic analytics use the reporter-chosen county only; small counts suppressed.
- Org "campaigns" is a verified-indicator list by category, not automatic clustering.
- API: test keys only; no webhooks; no file upload via API.
- Public reports are anonymous-capable and rely on moderation; moderator capacity is the bottleneck.
- Messages as indicators are exact-after-normalisation; near-duplicates are suggested to moderators, not auto-merged.
- Design items not built: states-gallery screen, "Try a request" console (use /docs), org alert "new rule" dialog (simple form instead), roles matrix is read-only as designed.
