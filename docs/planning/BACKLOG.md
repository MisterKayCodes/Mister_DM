# BACKLOG
# Ideas go here. Nothing in this file gets built until MVP is complete.
# Writing it here means you won't forget it. That's the only purpose.

---

## Feature Ideas (Post-MVP)

- Global template library (reuse templates across campaigns)
- Account health scoring (track which accounts are at risk)
- Account rotation (auto-switch accounts mid-campaign)
- Daily send limits per account
- Analytics dashboard (charts, conversion rates, reply rates)
- AI conversation summarizer (paste export → get summary)
- Auto-reply suggestions (AI drafts, human sends)
- Lead scoring / prospect rating
- Scraping (find targets from Telegram groups)
- Target deduplication across campaigns
- Blacklist (never contact this username again)
- Scheduled campaigns (start at specific time/date)
- Campaign cloning
- Multi-user support
- Web dashboard (replace Telegram bot UI)

---

## Technical Debt (Post-MVP)

- Retry engine for failed targets (with backoff)
- Account session health check on startup
- Database migration system (Alembic)
- Unit tests

### Mister (kay) Tool Enhancements — Add to Mister's own backlog
These are features needed in the `kay` CLI tool itself, not in Mister DM:
- `kay organize` — takes a mapping config file and restructures project folders automatically, so the AI doesn't waste tokens running multiple shell Move-Item commands manually
- `kay audit` — reads `ROLES_AND_RULES.md` from a project and scans the codebase for architectural violations (e.g. a bot handler importing `AsyncSessionLocal` directly, a repository opening its own session, etc.)

---

## Challenges / Open Questions (Revisit Later)

- What happens if Telegram account gets banned mid-campaign?
- Should we eventually store the first reply for offline export?
- Rate limiting strategy at scale (100+ targets/day)?
