# ROADMAP
# One phase at a time. Define done before you start. Commit when done.

---

## Current Phase

**Phase 1 — Accounts**

---

## Phases

### Phase 1 — Accounts
**Done when:**
- [ ] Add account (name, session_path, delay_min, delay_max)
- [ ] List all accounts
- [ ] Delete account
- [ ] Saved and retrieved from SQLite
- [ ] Tested manually end-to-end

```bash
git commit -m "phase 1: accounts complete"
```

---

### Phase 2 — Campaigns
**Done when:**
- [ ] Create campaign (name, select account)
- [ ] List campaigns with status
- [ ] Delete campaign (draft only)
- [ ] Tested manually end-to-end

```bash
git commit -m "phase 2: campaigns complete"
```

---

### Phase 3 — Templates
**Done when:**
- [ ] Add template to a campaign
- [ ] List templates per campaign
- [ ] Delete template
- [ ] Tested manually end-to-end

```bash
git commit -m "phase 3: templates complete"
```

---

### Phase 4 — Import Targets
**Done when:**
- [ ] Paste usernames directly into bot
- [ ] Upload TXT file
- [ ] Targets stored as `pending` in DB
- [ ] Duplicate check (same username + campaign = skip)
- [ ] Tested manually end-to-end

```bash
git commit -m "phase 4: target import complete"
```

---

### Phase 5 — Scheduler (Campaign Engine)
**Done when:**
- [ ] Start campaign → picks pending targets one by one
- [ ] Randomly picks template
- [ ] Sends message via Telethon (DRY RUN mode first)
- [ ] Marks target as `sent` on success
- [ ] Marks target as `failed` on error (FloodWait, UserNotFound, Privacy, etc.)
- [ ] Generates random delay between sends (delay_min to delay_max)
- [ ] Pause / Resume / Stop controls work
- [ ] Campaign auto-marks `completed` when all targets processed
- [ ] Tested with dry_run=True first, then 2-3 real accounts

```bash
git commit -m "phase 5: scheduler complete"
```

---

### Phase 6 — Reply Tracking
**Done when:**
- [ ] Telethon detects incoming replies from sent targets
- [ ] Target status updated to `replied`
- [ ] Bot notifies you: "@username replied"
- [ ] Tested manually (send from Account B → Account A replies)

```bash
git commit -m "phase 6: reply tracking complete"
```

---

### Phase 7 — Pain Tags
**Done when:**
- [ ] Create new pain tag (global)
- [ ] List all pain tags with count
- [ ] Assign tag(s) to a target
- [ ] View which targets share a tag
- [ ] Add/edit note on a target
- [ ] Tested manually end-to-end

```bash
git commit -m "phase 7: pain tags complete"
```

---

### Phase 8 — Export Conversations
**Done when:**
- [ ] Select campaign or individual target
- [ ] Telethon pulls conversation history live
- [ ] Formatted as readable text file
- [ ] File sent to you via bot
- [ ] Tested manually end-to-end

```bash
git commit -m "phase 8: export complete"
```

---

## MVP Complete Criteria

```
✓ 100 outreach messages sent
✓ 20+ conversations happened
✓ Pain tags assigned
✓ Top 3 pains identified
✓ Conversations exportable
```

**If this works: MVP is successful.**

---

## Rules

1. Never work on Phase N+1 while Phase N is incomplete
2. Bugs in current phase → fix immediately
3. New ideas → BACKLOG.md, not here
4. When a phase is done → commit → move on. No tweaking.
